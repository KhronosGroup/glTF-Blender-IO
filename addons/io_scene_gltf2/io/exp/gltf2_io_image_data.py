# Copyright 2018 The glTF-Blender-IO authors.
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

import typing
import struct
import zlib

class ImageData:
    """
    contains channels of an image with raw pixel data.
    """
    def __init__(self, name: str, width: int, height: int, channels: typing.List[typing.List[float]] = None):
        if width <= 0 or height <=0:
            raise ValueError("Image data can not have zero width or height")
        self.name = name
        self.channels = channels
        self.width = width
        self.height = height

    def add_to_image(self, image_data):
        if self.width != image_data.width or self.height != image_data.height:
            raise ValueError("Image dimensions do not match")
        if len(self.channels) + len(image_data.channels) > 4:
            raise ValueError("Can't append image: channels full")
        self.name += image_data.name
        self.channels += image_data.channels

    @property
    def r(self):
        if len(self.channels) <= 0:
            return None
        return self.channels[0]

    @property
    def g(self):
        if len(self.channels) <= 1:
            return None
        return self.channels[1]

    @property
    def b(self):
        if len(self.channels) <= 2:
            return None
        return self.channels[2]

    @property
    def a(self):
        if len(self.channels) <= 3:
            return None
        return self.channels[3]

    def to_image_data(self, mime_type: str) -> bytes:
        if mime_type == 'image/png':
            return self.to_png_data()
        raise ValueError("Unsupported image file type {}".format(mime_type))

    def to_png_data(self) -> bytes:
        buf = bytearray([int(channel * 255.0) for channel in self.channels])

        #
        # Taken from 'blender-thumbnailer.py' in Blender.
        #

        # reverse the vertical line order and add null bytes at the start
        width_byte_4 = self.width * 4
        raw_data = b"".join(
            b'\x00' + buf[span:span + width_byte_4] for span in range((self.height - 1) * self.width * 4, -1, - width_byte_4))

        def png_pack(png_tag, data):
            chunk_head = png_tag + data
            return struct.pack("!I", len(data)) + chunk_head + struct.pack("!I", 0xFFFFFFFF & zlib.crc32(chunk_head))

        return b"".join([
            b'\x89PNG\r\n\x1a\n',
            png_pack(b'IHDR', struct.pack("!2I5B", self.width, self.height, 8, 6, 0, 0, 0)),
            png_pack(b'IDAT', zlib.compress(raw_data, 9)),
            png_pack(b'IEND', b'')])
