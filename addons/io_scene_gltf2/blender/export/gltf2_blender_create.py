# Copyright (c) 2017 The Khronos Group Inc.
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

import json
import os
import shutil
import struct
import zlib

import bpy

from ...io.common.gltf2_io_debug import *

from .gltf2_blender_get import *

#
# Globals
#

#
# Functions
#

class BlenderEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, bpy.types.ID):
            return dict(
                name=obj.name,
                type=obj.__class__.__name__
            )

        return super(BlenderEncoder, self).default(obj)

def is_json(data):
    """
    Test, if a data set can be expressed as JSON.
    """
    try:
        json.dumps(data, cls=BlenderEncoder)
        return True
    except:
        import logging
        logging.exception("failed to json.dump custom properties.")
        return False

def create_image_file(context, blender_image, dst_path, file_format):
    """
    Creates JPEG or PNG file from a given Blender image.
    """

    if file_format == blender_image.file_format:
        # Copy source image to destination, keeping original format.

        src_path = bpy.path.abspath(blender_image.filepath, library=blender_image.library)

        if dst_path != src_path:
            shutil.copyfile(src_path, dst_path)

    else:
        # Render a new image to destination, converting to target format.

        # TODO: Reusing the existing scene means settings like exposure are applied on export,
        # which we don't want, but I'm not sure how to create a new Scene object through the
        # Python API. See: https://github.com/KhronosGroup/glTF-Blender-Exporter/issues/184.

        context.scene.render.image_settings.file_format = file_format
        context.scene.render.image_settings.color_depth = '8'
        blender_image.save_render(dst_path, context.scene)


def create_image_data(context, export_settings, blender_image, file_format):
    """
    Creates JPEG or PNG byte array from a given Blender image.
    """
    if blender_image is None:
        return None

    if file_format == 'PNG':
        return _create_png_data(context, export_settings, blender_image)
    else:
        return _create_jpg_data(context, export_settings, blender_image)


def _create_jpg_data(context, export_settings, blender_image):
    """
    Creates a JPEG byte array from a given Blender image.
    """

    uri = get_image_uri(export_settings, blender_image)
    path = export_settings['gltf_filedirectory'] + uri

    create_image_file(context, blender_image, path, 'JPEG')

    jpg_data = open(path, 'rb').read()
    os.remove(path)
    return jpg_data

def _create_png_data(context, export_settings, blender_image):
    """
    Creates a PNG byte array from a given Blender image.
    """

    width = blender_image.size[0]
    height = blender_image.size[1]

    buf = bytearray([int(channel * 255.0) for channel in blender_image.pixels])

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

    return b"".join([
        b'\x89PNG\r\n\x1a\n',
        png_pack(b'IHDR', struct.pack("!2I5B", width, height, 8, 6, 0, 0, 0)),
        png_pack(b'IDAT', zlib.compress(raw_data, 9)),
        png_pack(b'IEND', b'')])


def create_custom_property(blender_element):
    """
    Filters and creates a custom property, which is stored in the glTF extra field.
    """
    if not blender_element:
        return None

    extras = {}

    # Custom properties, which are in most cases present and should not be exported.
    black_list = ['cycles', 'cycles_visibility', 'cycles_curves', '_RNA_UI']

    count = 0
    for custom_property in blender_element.keys():
        if custom_property in black_list:
            continue

        value = blender_element[custom_property]

        add_value = False

        if isinstance(value, bpy.types.ID):
            add_value = True

        if isinstance(value, str):
            add_value = True

        if isinstance(value, (int, float)):
            add_value = True

        if hasattr(value, "to_list"):
            value = value.to_list()
            add_value = True

        if hasattr(value, "to_dict"):
            value = value.to_dict()
            add_value = is_json(value)

        if add_value:
            extras[custom_property] = value
            count += 1

    if count == 0:
        return None

    return extras
