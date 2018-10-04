# Copyright (c) 2018 The Khronos Group Inc.
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
import base64
from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.blender.exp.gltf2_blender_gather import cached
from io_scene_gltf2.blender.com import gltf2_blender_image
from io_scene_gltf2.io.exp import gltf2_io_binary_data

@cached
def gather_image(blender_image, export_settings):
    if not __filter_image(blender_image, export_settings):
        return None
    return gltf2_io.Image(
        buffer_view=__gather_buffer_view(blender_image, export_settings),
        extensions=__gather_extensions(blender_image, export_settings),
        extras=__gather_extras(blender_image, export_settings),
        mime_type=__gather_mime_type(blender_image, export_settings),
        name=__gather_name(blender_image, export_settings),
        uri=__gather_uri(blender_image, export_settings)
    )


def __filter_image(blender_image, export_settings):
    return True


def __gather_buffer_view(blender_image, export_settings):
    if export_settings['gltf_format'] == 'ASCII':
        return None

    image = gltf2_blender_image.create_img_from_blender_image(blender_image)
    return gltf2_io_binary_data.BinaryData(data=image.to_image_data(__gather_mime_type(blender_image, export_settings)))

def __gather_extensions(blender_image, export_settings):
    return None


def __gather_extras(blender_image, export_settings):
    return None


def __gather_mime_type(blender_image, export_settings):
    if export_settings['filtered_images_use_alpha'].get(blender_image.name):
        return 'image/png'
    return 'image/png'
    #return 'image/jpeg'


def __gather_name(blender_image, export_settings):
    return blender_image.name


def __gather_uri(blender_image, export_settings):
    if export_settings['gltf_format'] != 'ASCII':
        return None

    # as usual we just store the data in place instead of already resolving the references
    return gltf2_blender_image.create_img_from_blender_image(blender_image)