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
        self.file_format = {
            "image/jpeg": "JPEG",
            "image/png": "PNG"
        }.get(mime_type, "PNG")

        # Happy path = we can just use an existing Blender image
        if self.__on_happy_path():
            return self.__encode_happy()

        # Unhappy path = we need to create the image self.fills describes.
        return self.__encode_unhappy()

    def __encode_happy(self) -> bytes:
        for fill in self.fills.values():
            return self.__encode_from_image(fill.image)

    def __encode_unhappy(self) -> bytes:
        result = self.__encode_unhappy_with_compositor()
        if result is not None:
            return result
        return self.__encode_unhappy_with_numpy()

    def __encode_unhappy_with_compositor(self) -> bytes:
        # Builds a Compositor graph that will build the correct image
        # from the description in self.fills.
        #
        #     [ Image ]->[ Sep RGBA ]    [ Comb RGBA ]
        #                [  src_chan]--->[dst_chan   ]--->[ Output ]
        #
        # This is hacky, but is about 4x faster than using
        # __encode_unhappy_with_numpy. There are some caveats though:

        # First, we can't handle pre-multiplied alpha.
        if Channel.A in self.fills:
            return None

        # Second, in order to get the same results as using image.pixels
        # (which ignores the colorspace), we need to use the 'Non-Color'
        # colorspace for all images and set the output device to 'None'. But
        # setting the colorspace on dirty images discards their changes.
        # So we can't handle dirty images that aren't already 'Non-Color'.
        for fill in self.fills:
            if isinstance(fill, FillImage):
                if fill.image.is_dirty:
                    if fill.image.colorspace_settings.name != 'Non-Color':
                        return None

        tmp_scene = None
        orig_colorspaces = {}  # remembers original colorspaces
        try:
            tmp_scene = bpy.data.scenes.new('##gltf-export:tmp-scene##')
            tmp_scene.use_nodes = True
            node_tree = tmp_scene.node_tree
            for node in node_tree.nodes:
                node_tree.nodes.remove(node)

            out = node_tree.nodes.new('CompositorNodeComposite')
            comb_rgba = node_tree.nodes.new('CompositorNodeCombRGBA')
            for i in range(4):
                comb_rgba.inputs[i].default_value = 1.0
            node_tree.links.new(out.inputs['Image'], comb_rgba.outputs['Image'])

            img_size = None
            for dst_chan, fill in self.fills.items():
                if not isinstance(fill, FillImage):
                    continue

                img = node_tree.nodes.new('CompositorNodeImage')
                img.image = fill.image
                sep_rgba = node_tree.nodes.new('CompositorNodeSepRGBA')
                node_tree.links.new(sep_rgba.inputs['Image'], img.outputs['Image'])
                node_tree.links.new(comb_rgba.inputs[dst_chan], sep_rgba.outputs[fill.src_chan])

                if fill.image.colorspace_settings.name != 'Non-Color':
                    if fill.image.name not in orig_colorspaces:
                        orig_colorspaces[fill.image.name] = \
                            fill.image.colorspace_settings.name
                    fill.image.colorspace_settings.name = 'Non-Color'

                if img_size is None:
                    img_size = fill.image.size[:2]
                else:
                    # All images should be the same size (should be
                    # guaranteed by gather_texture_info)
                    assert img_size == fill.image.size[:2]

            width, height = img_size or (1, 1)
            return _render_temp_scene(
                tmp_scene=tmp_scene,
                width=width,
                height=height,
                file_format=self.file_format,
                color_mode='RGB',
                colorspace='None',
            )

        finally:
            for img_name, colorspace in orig_colorspaces.items():
                bpy.data.images[img_name].colorspace_settings.name = colorspace

            if tmp_scene is not None:
                bpy.data.scenes.remove(tmp_scene, do_unlink=True)


    def __encode_unhappy_with_numpy(self):
        # Read the pixels of each image with image.pixels, put them into a
        # numpy, and assemble the desired image that way. This is the slowest
        # method, and the conversion to Python data eats a lot of memory, so
        # it's only used as a last resort.
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

        if result is None:
            # No ImageFills; use a 1x1 white pixel
            result = np.array([1.0, 1.0, 1.0, 1.0])
            result = result.reshape((1, 1, 4))

        return self.__encode_from_numpy_array(result)

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

            return _encode_temp_image(tmp_image, self.file_format)

        finally:
            if tmp_image is not None:
                bpy.data.images.remove(tmp_image, do_unlink=True)

    def __encode_from_image(self, image: bpy.types.Image) -> bytes:
        # See if there is an existing file we can use.
        if self.file_format == image.file_format:
            src_path = bpy.path.abspath(image.filepath_raw)
            if os.path.isfile(src_path):
                with open(src_path, 'rb') as f:
                    return f.read()

        # Copy to a temp image and save.
        tmp_image = None
        try:
            tmp_image = image.copy()
            if image.is_dirty:
                tmp_image.pixels = image.pixels[:]

            return _encode_temp_image(tmp_image, self.file_format)
        finally:
            if tmp_image is not None:
                bpy.data.images.remove(tmp_image, do_unlink=True)


def _encode_temp_image(tmp_image: bpy.types.Image, file_format: str) -> bytes:
    with tempfile.TemporaryDirectory() as tmpdirname:
        tmpfilename = tmpdirname + '/img'
        tmp_image.filepath_raw = tmpfilename

        # NOT A TYPO!!! If you delete this line, the
        # assignment on the next line will not work.
        tmp_image.file_format
        tmp_image.file_format = file_format

        tmp_image.save()

        with open(tmpfilename, "rb") as f:
            return f.read()


def _render_temp_scene(
    tmp_scene: bpy.types.Scene,
    width: int,
    height: int,
    file_format: str,
    color_mode: str,
    colorspace: str,
) -> bytes:
    """Set render settings, render to a file, and read back."""
    tmp_scene.render.resolution_x = width
    tmp_scene.render.resolution_y = height
    tmp_scene.render.resolution_percentage = 100
    tmp_scene.display_settings.display_device = colorspace
    tmp_scene.render.image_settings.color_mode = color_mode
    tmp_scene.render.dither_intensity = 0.0

    # Turn off all metadata (stuff like use_stamp_date, etc.)
    for attr in dir(tmp_scene.render):
        if attr.startswith('use_stamp_'):
            setattr(tmp_scene.render, attr, False)

    with tempfile.TemporaryDirectory() as tmpdirname:
        tmpfilename = tmpdirname + "/img"
        tmp_scene.render.filepath = tmpfilename
        tmp_scene.render.use_file_extension = False
        tmp_scene.render.image_settings.file_format = file_format

        bpy.ops.render.render(scene=tmp_scene.name, write_still=True)

        with open(tmpfilename, "rb") as f:
            return f.read()
