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
from io_scene_gltf2.io.com import gltf2_io_debug
from io_scene_gltf2.blender.exp import gltf2_blender_image
from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached


@cached
def gather_image(
        blender_shader_sockets_or_texture_slots: typing.Union[typing.Tuple[bpy.types.NodeSocket],
                                                              typing.Tuple[bpy.types.Texture]],
        export_settings):
    if not __filter_image(blender_shader_sockets_or_texture_slots, export_settings):
        return None

    uri = __gather_uri(blender_shader_sockets_or_texture_slots, export_settings)
    buffer_view = __gather_buffer_view(blender_shader_sockets_or_texture_slots, export_settings)
    if not (uri is not None or buffer_view is not None):
        # The blender image has no data
        return None

    image = gltf2_io.Image(
        buffer_view=buffer_view,
        extensions=__gather_extensions(blender_shader_sockets_or_texture_slots, export_settings),
        extras=__gather_extras(blender_shader_sockets_or_texture_slots, export_settings),
        mime_type=__gather_mime_type(blender_shader_sockets_or_texture_slots, export_settings),
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
        if image is None:
            return None
        return gltf2_io_binary_data.BinaryData(
            data=image.encode(__gather_mime_type(sockets_or_slots, export_settings)))
    return None


def __gather_extensions(sockets_or_slots, export_settings):
    return None


def __gather_extras(sockets_or_slots, export_settings):
    return None


def __gather_mime_type(sockets_or_slots, export_settings):
    if export_settings["gltf_image_format"] == "NAME":
        image_name = __get_texname_from_slot(sockets_or_slots, export_settings)
        _, extension = os.path.splitext(bpy.data.images[image_name].filepath)
        extension = extension.lower()
        if extension in [".jpeg", ".jpg", ".png"]:
            return {
                ".jpeg": "image/jpeg",
                ".jpg": "image/jpeg",
                ".png": "image/png",
            }[extension]
        return "image/png"

    elif export_settings["gltf_image_format"] == "JPEG":
        return "image/jpeg"
    else:
        return "image/png"


def __gather_name(sockets_or_slots, export_settings):
    image_name = __get_texname_from_slot(sockets_or_slots, export_settings)

    name, extension = os.path.splitext(image_name)
    extension = extension.lower()
    if extension in [".jpeg", ".jpg", ".png"]:
        return name
    return image_name


def __gather_uri(sockets_or_slots, export_settings):
    if export_settings[gltf2_blender_export_keys.FORMAT] == 'GLTF_SEPARATE':
        # as usual we just store the data in place instead of already resolving the references
        mime_type = __gather_mime_type(sockets_or_slots, export_settings)
        return gltf2_io_image_data.ImageData(
            data=__get_image_data(sockets_or_slots, export_settings).encode(mime_type=mime_type),
            mime_type=mime_type,
            name=__gather_name(sockets_or_slots, export_settings)
        )

    return None


def __is_socket(sockets_or_slots):
    return isinstance(sockets_or_slots[0], bpy.types.NodeSocket)


def __is_slot(sockets_or_slots):
    return isinstance(sockets_or_slots[0], bpy.types.MaterialTextureSlot)


def __get_image_data(sockets_or_slots, export_settings) -> gltf2_blender_image.ExportImage:
    # For shared ressources, such as images, we just store the portion of data that is needed in the glTF property
    # in a helper class. During generation of the glTF in the exporter these will then be combined to actual binary
    # ressources.
    def split_pixels_by_channels(image: bpy.types.Image, export_settings) -> typing.Optional[typing.List[typing.List[float]]]:
        channelcache = export_settings['gltf_channelcache']
        if image.name in channelcache:
            return channelcache[image.name]

        pixels = np.array(image.pixels)
        pixels = pixels.reshape((pixels.shape[0] // image.channels, image.channels))
        channels = np.split(pixels, pixels.shape[1], axis=1)

        channelcache[image.name] = channels

        return channels

    if __is_socket(sockets_or_slots):
        results = [__get_tex_from_socket(socket, export_settings) for socket in sockets_or_slots]
        composed_image = None
        for result, socket in zip(results, sockets_or_slots):
            if result.shader_node.image.channels == 0:
                gltf2_io_debug.print_console("WARNING",
                                             "Image '{}' has no color channels and cannot be exported.".format(
                                                 result.shader_node.image))
                continue

            # rudimentarily try follow the node tree to find the correct image data.
            source_channel = 0
            for elem in result.path:
                if isinstance(elem.from_node, bpy.types.ShaderNodeSeparateRGB):
                    source_channel = {
                        'R': 0,
                        'G': 1,
                        'B': 2
                    }[elem.from_socket.name]

            image = gltf2_blender_image.ExportImage.from_blender_image(result.shader_node.image)

            if composed_image is None:
                composed_image = gltf2_blender_image.ExportImage.white_image(image.width, image.height)

            # Change target channel for metallic and roughness.
            if socket.name == 'Metallic':
                composed_image[2] = image[source_channel]
            elif socket.name == 'Roughness':
                composed_image[1] = image[source_channel]
            elif socket.name == 'Occlusion' and len(sockets_or_slots) > 2:
                composed_image[0] = image[source_channel]
            else:
                composed_image.update(image)

        return composed_image

    elif __is_slot(sockets_or_slots):
        texture = __get_tex_from_slot(sockets_or_slots[0])
        image = gltf2_blender_image.ExportImage.from_blender_image(texture.image)
        return image
    else:
        raise NotImplementedError()

@cached
def __get_tex_from_socket(blender_shader_socket: bpy.types.NodeSocket, export_settings):
    result = gltf2_blender_search_node_tree.from_socket(
        blender_shader_socket,
        gltf2_blender_search_node_tree.FilterByType(bpy.types.ShaderNodeTexImage))
    if not result:
        return None
    return result[0]


def __get_tex_from_slot(blender_texture_slot):
    return blender_texture_slot.texture


@cached
def __get_texname_from_slot(sockets_or_slots, export_settings):
    if __is_socket(sockets_or_slots):
        node = __get_tex_from_socket(sockets_or_slots[0], export_settings)
        if node is None:
            return None
        return node.shader_node.image.name

    elif isinstance(sockets_or_slots[0], bpy.types.MaterialTextureSlot):
        return sockets_or_slots[0].texture.image.name
