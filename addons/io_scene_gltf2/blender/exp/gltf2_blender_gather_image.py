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
import re

import bpy
import typing
import os
import numpy as np

from . import gltf2_blender_export_keys
from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.blender.exp import gltf2_blender_search_node_tree
from io_scene_gltf2.io.exp import gltf2_io_binary_data
from io_scene_gltf2.io.exp import gltf2_io_image_data


def gather_image(
        blender_shader_sockets_or_texture_slots: typing.Union[typing.Tuple[bpy.types.NodeSocket],
                                                              typing.Tuple[bpy.types.Texture]],
        export_settings):
    if not __filter_image(blender_shader_sockets_or_texture_slots, export_settings):
        return None

    uri = __gather_uri(blender_shader_sockets_or_texture_slots, export_settings)
    mime_type = __gather_mime_type(uri.filepath if uri is not None else "")

    image = gltf2_io.Image(
        buffer_view=__gather_buffer_view(blender_shader_sockets_or_texture_slots, export_settings),
        extensions=__gather_extensions(blender_shader_sockets_or_texture_slots, export_settings),
        extras=__gather_extras(blender_shader_sockets_or_texture_slots, export_settings),
        mime_type=mime_type,
        name=__gather_name(blender_shader_sockets_or_texture_slots, export_settings),
        uri=uri
    )
    return image


def __filter_image(sockets_or_slots, export_settings):
    if not sockets_or_slots:
        return False
    return True


def __gather_buffer_view(sockets_or_slots, export_settings):
    if export_settings[gltf2_blender_export_keys.FORMAT] != 'GLTF_SEPARATE':
        image = __get_image_data(sockets_or_slots, export_settings)
        return gltf2_io_binary_data.BinaryData(
            data=image.to_image_data(__gather_mime_type()))
    return None


def __gather_extensions(sockets_or_slots, export_settings):
    return None


def __gather_extras(sockets_or_slots, export_settings):
    return None


def __gather_mime_type(filepath=""):
    extension_types = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg'}
    default_extension = extension_types['.png']

    matches = re.findall(r'\.\w+$', filepath)
    extension = matches[0] if len(matches) > 0 else default_extension
    return extension_types[extension] if extension.lower() in extension_types.keys() else default_extension


def __gather_name(sockets_or_slots, export_settings):
    if __is_socket(sockets_or_slots):
        node = __get_tex_from_socket(sockets_or_slots[0])
        if node is not None:
            return node.shader_node.image.name
    elif isinstance(sockets_or_slots[0], bpy.types.MaterialTextureSlot):
        return sockets_or_slots[0].name
    return None


def __gather_uri(sockets_or_slots, export_settings):
    if export_settings[gltf2_blender_export_keys.FORMAT] == 'GLTF_SEPARATE':
        # as usual we just store the data in place instead of already resolving the references
        return __get_image_data(sockets_or_slots, export_settings)
    return None


def __is_socket(sockets_or_slots):
    return isinstance(sockets_or_slots[0], bpy.types.NodeSocket)


def __is_slot(sockets_or_slots):
    return isinstance(sockets_or_slots[0], bpy.types.MaterialTextureSlot)


def __get_image_data(sockets_or_slots, export_settings):
    # For shared ressources, such as images, we just store the portion of data that is needed in the glTF property
    # in a helper class. During generation of the glTF in the exporter these will then be combined to actual binary
    # ressources.
    def split_pixels_by_channels(image: bpy.types.Image, export_settings) -> typing.List[typing.List[float]]:
        assert image.channels > 0, "Image '{}' has no color channels and cannot be exported.".format(image.name)

        channelcache = export_settings['gltf_channelcache']
        if image.name in channelcache:
            return channelcache[image.name]

        pixels = np.array(image.pixels)
        pixels = pixels.reshape((pixels.shape[0] // image.channels, image.channels))
        channels = np.split(pixels, pixels.shape[1], axis=1)

        channelcache[image.name] = channels

        return channels

    if __is_socket(sockets_or_slots):
        results = [__get_tex_from_socket(socket) for socket in sockets_or_slots]
        image = None
        for result, socket in zip(results, sockets_or_slots):
            # rudimentarily try follow the node tree to find the correct image data.
            source_channel = None
            target_channel = None
            source_channels_length = None
            for elem in result.path:
                if isinstance(elem.from_node, bpy.types.ShaderNodeSeparateRGB):
                    source_channel = {
                        'R': 0,
                        'G': 1,
                        'B': 2
                    }[elem.from_socket.name]

            if source_channel is not None:
                pixels = [split_pixels_by_channels(result.shader_node.image, export_settings)[source_channel]]
                target_channel = source_channel
                source_channel = 0
                source_channels_length = 1
            else:
                pixels = split_pixels_by_channels(result.shader_node.image, export_settings)
                target_channel = 0
                source_channel = 0
                source_channels_length = len(pixels)

            # Change target channel for metallic and roughness.
            if elem.to_socket.name == 'Metallic':
                target_channel = 2
                source_channels_length = 1
            elif elem.to_socket.name == 'Roughness':
                target_channel = 1
                source_channels_length = 1

            file_name = os.path.splitext(result.shader_node.image.name)[0]

            image_data = gltf2_io_image_data.ImageData(
                file_name,
                result.shader_node.image.filepath,
                result.shader_node.image.size[0],
                result.shader_node.image.size[1],
                source_channel,
                target_channel,
                source_channels_length,
                pixels)

            if image is None:
                image = image_data
            else:
                image.add_to_image(target_channel, image_data)

        return image
    elif __is_slot(sockets_or_slots):
        texture = __get_tex_from_slot(sockets_or_slots[0])
        pixels = split_pixels_by_channels(texture.image, export_settings)

        image_data = gltf2_io_image_data.ImageData(
            texture.name,
            texture.image.filepath,
            texture.image.size[0],
            texture.image.size[1],
            0,
            0,
            len(pixels),
            pixels)
        return image_data
    else:
        # Texture slots
        raise NotImplementedError()


def __get_tex_from_socket(blender_shader_socket: bpy.types.NodeSocket):
    result = gltf2_blender_search_node_tree.from_socket(
        blender_shader_socket,
        gltf2_blender_search_node_tree.FilterByType(bpy.types.ShaderNodeTexImage))
    if not result:
        return None
    return result[0]


def __get_tex_from_slot(blender_texture_slot):
    return blender_texture_slot.texture
