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

#
# Imports
#

import struct
import zlib


class Image:
    """
    Image object class to represent a 4-channel RGBA image.

    Pixel values are expected to be floating point in the range of [0.0 to 1.0]
    """

    def __init__(self, width, height, pixels):
        self.width = width
        self.height = height
        self.channels = 4
        self.pixels = pixels
        self.name = ""
        self.file_format = "PNG"

    def to_png_data(self):
        buf = bytearray([int(channel * 255.0) for channel in self.pixels])

        #
        # Taken from 'blender-thumbnailer.py' in Blender.
        #

        # reverse the vertical line order and add null bytes at the start
        width_byte_4 = self.width * 4
        raw_data = b"".join(
            b'\x00' + buf[span:span + width_byte_4] for span in range(
                (self.height - 1) * self.width * 4, -1, - width_byte_4))

        def png_pack(png_tag, data):
            chunk_head = png_tag + data
            return struct.pack("!I", len(data)) + chunk_head + struct.pack("!I", 0xFFFFFFFF & zlib.crc32(chunk_head))

        return b"".join([
            b'\x89PNG\r\n\x1a\n',
            png_pack(b'IHDR', struct.pack("!2I5B", self.width, self.height, 8, 6, 0, 0, 0)),
            png_pack(b'IDAT', zlib.compress(raw_data, 9)),
            png_pack(b'IEND', b'')])

    def to_image_data(self, mime_type):
        if mime_type == 'image/png':
            return self.to_png_data()
        raise ValueError("Unsupported image file type {}".format(mime_type))

    def save_png(self, dst_path):
        data = self.to_png_data()
        with open(dst_path, 'wb') as f:
            f.write(data)


def create_img(width, height, r=0.0, g=0.0, b=0.0, a=1.0):
    """
    Create a new image object with 4 channels and initialize it with the given default values.

    (if no arguments are given, these default to R=0, G=0, B=0, A=1.0)
    Return the created image object.
    """
    return Image(width, height, [r, g, b, a] * (width * height))


def create_img_from_pixels(width, height, pixels):
    """
    Create a new image object with 4 channels and initialize it using the given array of pixel data.

    Return the created image object.
    """
    if pixels is None or len(pixels) != width * height * 4:
        return None

    return Image(width, height, pixels)


def copy_img_channel(dst_image, dst_channel, src_image, src_channel):
    """
    Copy a single channel (identified by src_channel) from src_image to dst_image (overwriting dst_channel).

    src_image and dst_image are expected to be image objects created using create_img.
    Return True on success, False otherwise.
    """
    if dst_image is None or src_image is None:
        return False

    if dst_channel < 0 or dst_channel >= dst_image.channels or src_channel < 0 or src_channel >= src_image.channels:
        return False

    if src_image.width != dst_image.width or \
            src_image.height != dst_image.height or \
            src_image.channels != dst_image.channels:
        return False

    for i in range(0, len(dst_image.pixels), dst_image.channels):
        dst_image.pixels[i + dst_channel] = src_image.pixels[i + src_channel]

    return True


def test_save_img(image, path):
    """
    Save the given image to a PNG file (specified by path).

    Return True on success, False otherwise.
    """
    if image is None or image.channels != 4:
        return False

    width = image.width
    height = image.height

    buf = bytearray([int(channel * 255.0) for channel in image.pixels])

    #
    # Taken from 'blender-thumbnailer.py' in Blender.
    #

    # reverse the vertical line order and add null bytes at the start
    width_byte_4 = width * 4
    raw_data = b"".join(
        b'\x00' + buf[span:span + width_byte_4] for span in range((height - 1) * width * 4, -1, - width_byte_4))

    def png_pack(png_tag, data):
        chunk_head = png_tag + data
        return struct.pack("!I", len(data)) + chunk_head + struct.pack("!I", 0xFFFFFFFF & zlib.crc32(chunk_head))

    data = b"".join([
        b'\x89PNG\r\n\x1a\n',
        png_pack(b'IHDR', struct.pack("!2I5B", width, height, 8, 6, 0, 0, 0)),
        png_pack(b'IDAT', zlib.compress(raw_data, 9)),
        png_pack(b'IEND', b'')])

    with open(path, 'wb') as f:
        f.write(data)
        return True
