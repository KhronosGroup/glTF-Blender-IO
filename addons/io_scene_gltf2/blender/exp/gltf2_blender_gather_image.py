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
import typing
from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached
from io_scene_gltf2.blender.exp import gltf2_blender_search_node_tree
from io_scene_gltf2.io.exp import gltf2_io_binary_data
from io_scene_gltf2.io.exp import gltf2_io_image_data


@cached
def gather_image(blender_shader_sockets: typing.List[bpy.types.NodeSocket], export_settings):
    if not __filter_image(blender_shader_sockets, export_settings):
        return None
    return gltf2_io.Image(
        buffer_view=__gather_buffer_view(blender_shader_sockets, export_settings),
        extensions=__gather_extensions(blender_shader_sockets, export_settings),
        extras=__gather_extras(blender_shader_sockets, export_settings),
        mime_type=__gather_mime_type(blender_shader_sockets, export_settings),
        name=__gather_name(blender_shader_sockets, export_settings),
        uri=__gather_uri(blender_shader_sockets, export_settings)
    )


def __filter_image(blender_shader_sockets, export_settings):
    return True


def __gather_buffer_view(blender_shader_sockets, export_settings):
    if export_settings['gltf_format'] != 'ASCII':

        image = __get_image_data(blender_shader_sockets)
        return gltf2_io_binary_data.BinaryData(
            data=image.to_image_data(__gather_mime_type(blender_shader_sockets, export_settings)))
    return None


def __gather_extensions(blender_shader_sockets, export_settings):
    return None


def __gather_extras(blender_shader_sockets, export_settings):
    return None


def __gather_mime_type(blender_shader_sockets, export_settings):
    if export_settings['filtered_images_use_alpha'].get(__gather_name(blender_shader_sockets, export_settings)):
        return 'image/png'
    return 'image/png'
    #return 'image/jpeg'


def __gather_name(blender_shader_sockets, export_settings):
    node = __get_tex_from_socket(blender_shader_sockets[0])
    if node is not None:
        return node.shader_node.image.name
    return None


def __gather_uri(blender_shader_sockets, export_settings):
    if export_settings['gltf_format'] == 'ASCII':
        # as usual we just store the data in place instead of already resolving the references
        return __get_image_data(blender_shader_sockets)
    return None


def __get_image_data(blender_shader_sockets):
    # For shared ressources, such as images, we just store the portion of data that is needed in the glTF property
    # in a helper class. During generation of the glTF in the exporter these will then be combined to actual binary
    # ressources.

    results = [__get_tex_from_socket(socket) for socket in blender_shader_sockets]
    image = None
    for result, socket in zip(results, blender_shader_sockets):
        # rudimentarily try follow the node tree to find the correct image data.
        channel = None
        for elem in result.path:
            if isinstance(elem.to_node, bpy.ShaderNodeSeparateRGB):
                channel = {
                    'R': 0,
                    'G': 1,
                    'B': 2
                }[elem.to_socket.name]

        if channel is not None:
            pixels = [result.shader_node.image.pixels[channel]]
        else:
            pixels = result.shader_node.image.pixels

        image_data = gltf2_io_image_data.ImageData(
            socket.name,
            result.shader_node.image.width,
            result.shader_node.image.height,
            pixels)

        if image is None:
            image = image_data
        else:
            image.append(image_data)

    return image


def __get_tex_from_socket(blender_shader_socket):
    result = gltf2_blender_search_node_tree.from_socket(
        blender_shader_socket,
        gltf2_blender_search_node_tree.FilterByType(bpy.types.ShaderNodeTexImage))
    if not result:
        return None
    return result[0]
