# Copyright 2018-2019 The glTF-Blender-IO authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import bpy
import os
from typing import Optional
import numpy as np
import tempfile
import enum


class Channel(enum.IntEnum):
    R = 0
    G = 1
    B = 2
    A = 3

# These describe how an ExportImage's channels should be filled.

class FillImage:
    """Fills a channel with the channel src_chan from a Blender image."""
    def __init__(self, image: bpy.types.Image, src_chan: Channel):
        self.image = image
        self.src_chan = src_chan

class FillWhite:
    """Fills a channel with all ones (1.0)."""
    pass


class ExportImage:
    """Custom image class.

    An image is represented by giving a description of how to fill its red,
    green, blue, and alpha channels. For example:

        self.fills = {
            Channel.R: FillImage(image=bpy.data.images['Im1'], src_chan=Channel.B),
            Channel.G: FillWhite(),
        }

    This says that the ExportImage's R channel should be filled with the B
    channel of the Blender image 'Im1', and the ExportImage's G channel
    should be filled with all 1.0s. Undefined channels mean we don't care
    what values that channel has.

    This is flexible enough to handle the case where eg. the user used the R
    channel of one image as the metallic value and the G channel of another
    image as the roughness, and we need to synthesize an ExportImage that
    packs those into the B and G channels for glTF.

    Storing this description (instead of raw pixels) lets us make more
    intelligent decisions about how to encode the image.
    """

    def __init__(self):
        self.fills = {}

    @staticmethod
    def from_blender_image(image: bpy.types.Image):
        export_image = ExportImage()
        for chan in range(image.channels):
            export_image.fill_image(image, dst_chan=chan, src_chan=chan)
        return export_image

    def fill_image(self, image: bpy.types.Image, dst_chan: Channel, src_chan: Channel):
        self.fills[dst_chan] = FillImage(image, src_chan)

    def fill_white(self, dst_chan: Channel):
        self.fills[dst_chan] = FillWhite()

    def is_filled(self, chan: Channel) -> bool:
        return chan in self.fills

    def empty(self) -> bool:
        return not self.fills

    def __on_happy_path(self) -> bool:
        # Whether there is an existing Blender image we can use for this
        # ExportImage because all the channels come from the matching
        # channel of that image, eg.
        #
        #     self.fills = {
        #         Channel.R: FillImage(image=im, src_chan=Channel.R),
        #         Channel.G: FillImage(image=im, src_chan=Channel.G),
        #     }
        return (
            all(isinstance(fill, FillImage) for fill in self.fills.values()) and
            all(dst_chan == fill.src_chan for dst_chan, fill in self.fills.items()) and
            len(set(fill.image.name for fill in self.fills.values())) == 1
        )

    def encode(self, mime_type: Optional[str]) -> bytes:
        self.mime_type = mime_type

        # All channels are white or undefined
        # (I don't think this should happen...)
        if all(isinstance(fill, FillWhite) for fill in self.fills.values()):
            return self.__encode_blank()

        # Happy path = we can just use an existing Blender image
        if self.__on_happy_path():
            return self.__encode_happy()

        # Unhappy path = we need to create the image self.fills describes.
        return self.__encode_unhappy()

    def __encode_happy(self) -> bytes:
        for fill in self.fills.values():
            return self.__encode_from_image(fill.image)

    def __encode_unhappy(self) -> bytes:
        # This will be a numpy array we fill in with pixel data.
        result = None

        img_fills = {
            chan: fill
            for chan, fill in self.fills.items()
            if isinstance(fill, FillImage)
        }
        # Loop over images instead of dst_chans; ensures we only decode each
        # image once even if it's used in multiple channels.
        image_names = list(set(fill.image.name for fill in img_fills.values()))
        for image_name in image_names:
            image = bpy.data.images[image_name]

            if result is None:
                result = np.ones((image.size[0], image.size[1], 4), np.float32)
            # Images should all be the same size (should be guaranteed by
            # gather_texture_info).
            assert (image.size[0], image.size[1]) == result.shape[:2]

            # Slow and eats all your memory.
            pixels = np.array(image.pixels[:])

            pixels = pixels.reshape((image.size[0], image.size[1], image.channels))

            for dst_chan, img_fill in img_fills.items():
                if img_fill.image == image:
                    result[:, :, dst_chan] = pixels[:, :, img_fill.src_chan]

            pixels = None  # GC this please

        return self.__encode_from_numpy_array(result)

    def __encode_blank(self) -> bytes:
        # 1x1 white image
        pixels = np.array([1.0, 1.0, 1.0, 1.0])
        pixels = pixels.reshape((1, 1, 4))
        return self.__encode_from_numpy_array(pixels)

    def __encode_from_numpy_array(self, array: np.ndarray) -> bytes:
        tmp_image = None
        try:
            tmp_image = bpy.data.images.new(
                "##gltf-export:tmp-image##",
                width=array.shape[0],
                height=array.shape[1],
                alpha=Channel.A in self.fills,
            )
            assert tmp_image.channels == 4  # 4 regardless of the alpha argument above.

            # Also slow and eats all your memory.
            tmp_image.pixels = array.flatten().tolist()

            return self.__encode_from_image(tmp_image)

        finally:
            if tmp_image is not None:
                bpy.data.images.remove(tmp_image, do_unlink=True)

    def __encode_from_image(self, image: bpy.types.Image) -> bytes:
        file_format = {
            "image/jpeg": "JPEG",
            "image/png": "PNG"
        }.get(self.mime_type, "PNG")

        # For images already on disk, skip saving them and just read them back.
        # (What about if the image has changed on disk though?)
        if file_format == image.file_format and not image.is_dirty:
            src_path = bpy.path.abspath(image.filepath_raw)
            if os.path.isfile(src_path):
                with open(src_path, 'rb') as f:
                    return f.read()

        # Save to a tempfile and read back
        with tempfile.TemporaryDirectory() as tmpdirname:
            tmpfilename = tmpdirname + "/img"
            _save_copy_of_image(image, tmpfilename, file_format)
            with open(tmpfilename, "rb") as f:
                return f.read()

def _save_copy_of_image(image: bpy.types.Image, path: str, file_format: str):
    # Only way to save copy of an image seems to be to use image.save_render
    # which picks up render settings from a scene. Create a temp scene with
    # the settings we want to use.
    tmp_scene = None
    try:
        tmp_scene = bpy.data.scenes.new('##gltf-export:tmp-scene##')

        tmp_scene.render.image_settings.file_format = file_format
        tmp_scene.display_settings.display_device = 'None'
        tmp_scene.render.dither_intensity = 0.0

        image.save_render(path, scene=tmp_scene)

    finally:
        if tmp_scene is not None:
            bpy.data.scenes.remove(tmp_scene, do_unlink=True)
