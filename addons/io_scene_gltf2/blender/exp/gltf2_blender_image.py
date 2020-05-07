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
from typing import Optional, Tuple
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

    def blender_image(self) -> Optional[bpy.types.Image]:
        """If there's an existing Blender image we can use,
        returns it. Otherwise (if channels need packing),
        returns None.
        """
        if self.__on_happy_path():
            for fill in self.fills.values():
                return fill.image
        return None

    def __on_happy_path(self) -> bool:
        # All src_chans match their dst_chan and come from the same image
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
        return self.__encode_from_image(self.blender_image())

    def __encode_unhappy(self) -> bytes:
        # We need to assemble the image out of channels.
        # Do it with numpy and image.pixels.
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
                dim = (image.size[0], image.size[1])
                result = np.ones(dim[0] * dim[1] * 4, np.float32)
                tmp_buf = np.empty(dim[0] * dim[1] * 4, np.float32)
            # Images should all be the same size (should be guaranteed by
            # gather_texture_info).
            assert (image.size[0], image.size[1]) == dim

            image.pixels.foreach_get(tmp_buf)

            for dst_chan, img_fill in img_fills.items():
                if img_fill.image == image:
                    result[int(dst_chan)::4] = tmp_buf[int(img_fill.src_chan)::4]

        tmp_buf = None  # GC this

        if result is None:
            # No ImageFills; use a 1x1 white pixel
            dim = (1, 1)
            result = np.array([1.0, 1.0, 1.0, 1.0])

        return self.__encode_from_numpy_array(result, dim)

    def __encode_from_numpy_array(self, pixels: np.ndarray, dim: Tuple[int, int]) -> bytes:
        with TmpImageGuard() as guard:
            guard.image = bpy.data.images.new(
                "##gltf-export:tmp-image##",
                width=dim[0],
                height=dim[1],
                alpha=Channel.A in self.fills,
            )
            tmp_image = guard.image

            tmp_image.pixels.foreach_set(pixels)

            return _encode_temp_image(tmp_image, self.file_format)

    def __encode_from_image(self, image: bpy.types.Image) -> bytes:
        # See if there is an existing file we can use.
        data = None
        if image.source == 'FILE' and image.file_format == self.file_format and \
                not image.is_dirty:
            if image.packed_file is not None:
                data = image.packed_file.data
            else:
                src_path = bpy.path.abspath(image.filepath_raw)
                if os.path.isfile(src_path):
                    with open(src_path, 'rb') as f:
                        data = f.read()
        # Check magic number is right
        if data:
            if self.file_format == 'PNG':
                if data.startswith(b'\x89PNG'):
                    return data
            elif self.file_format == 'JPEG':
                if data.startswith(b'\xff\xd8\xff'):
                    return data

        # Copy to a temp image and save.
        with TmpImageGuard() as guard:
            _make_temp_image_copy(guard, src_image=image)
            tmp_image = guard.image
            return _encode_temp_image(tmp_image, self.file_format)


def _encode_temp_image(tmp_image: bpy.types.Image, file_format: str) -> bytes:
    with tempfile.TemporaryDirectory() as tmpdirname:
        tmpfilename = tmpdirname + '/img'
        tmp_image.filepath_raw = tmpfilename

        tmp_image.file_format = file_format

        tmp_image.save()

        with open(tmpfilename, "rb") as f:
            return f.read()


class TmpImageGuard:
    """Guard to automatically clean up temp images (use it with `with`)."""
    def __init__(self):
        self.image = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.image is not None:
            bpy.data.images.remove(self.image, do_unlink=True)


def _make_temp_image_copy(guard: TmpImageGuard, src_image: bpy.types.Image):
    """Makes a temporary copy of src_image. Will be cleaned up with guard."""
    guard.image = src_image.copy()
    tmp_image = guard.image

    tmp_image.update()

    if src_image.is_dirty:
        # Unsaved changes aren't copied by .copy(), so do them ourselves
        tmp_buf = np.empty(src_image.size[0] * src_image.size[1] * 4, np.float32)
        src_image.pixels.foreach_get(tmp_buf)
        tmp_image.pixels.foreach_set(tmp_buf)
