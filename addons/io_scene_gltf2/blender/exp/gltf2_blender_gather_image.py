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
from io_scene_gltf2.blender.exp.gltf2_blender_image import Channel, ExportImage
from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached
from io_scene_gltf2.io.exp.gltf2_io_user_extensions import export_user_extensions


@cached
def gather_image(
        blender_shader_sockets_or_texture_slots: typing.Union[typing.Tuple[bpy.types.NodeSocket],
                                                              typing.Tuple[bpy.types.Texture]],
        export_settings):
    if not __filter_image(blender_shader_sockets_or_texture_slots, export_settings):
        return None

    image_data = __get_image_data(blender_shader_sockets_or_texture_slots, export_settings)
    if image_data.empty():
        # The export image has no data
        return None

    mime_type = __gather_mime_type(blender_shader_sockets_or_texture_slots, export_settings)
    name = __gather_name(blender_shader_sockets_or_texture_slots, export_settings)

    uri = __gather_uri(image_data, mime_type, name, export_settings)
    buffer_view = __gather_buffer_view(image_data, mime_type, name, export_settings)

    image = __make_image(
        buffer_view,
        __gather_extensions(blender_shader_sockets_or_texture_slots, export_settings),
        __gather_extras(blender_shader_sockets_or_texture_slots, export_settings),
        mime_type,
        name,
        uri,
        export_settings
    )

    export_user_extensions('gather_image_hook', export_settings, image, blender_shader_sockets_or_texture_slots)

    return image

@cached
def __make_image(buffer_view, extensions, extras, mime_type, name, uri, export_settings):
    return gltf2_io.Image(
        buffer_view=buffer_view,
        extensions=extensions,
        extras=extras,
        mime_type=mime_type,
        name=name,
        uri=uri
    )


def __filter_image(sockets_or_slots, export_settings):
    if not sockets_or_slots:
        return False
    return True


@cached
def __gather_buffer_view(image_data, mime_type, name, export_settings):
    if export_settings[gltf2_blender_export_keys.FORMAT] != 'GLTF_SEPARATE':
        return gltf2_io_binary_data.BinaryData(data=image_data.encode(mime_type))
    return None


def __gather_extensions(sockets_or_slots, export_settings):
    return None


def __gather_extras(sockets_or_slots, export_settings):
    return None


def __gather_mime_type(sockets_or_slots, export_settings):
    # force png if Alpha contained so we can export alpha
    for socket in sockets_or_slots:
        if socket.name == "Alpha":
            return "image/png"

    if export_settings["gltf_image_format"] == "NAME":
        extension = __get_extension_from_slot(sockets_or_slots, export_settings)
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
    return image_name


@cached
def __gather_uri(image_data, mime_type, name, export_settings):
    if export_settings[gltf2_blender_export_keys.FORMAT] == 'GLTF_SEPARATE':
        # as usual we just store the data in place instead of already resolving the references
        return gltf2_io_image_data.ImageData(
            data=image_data.encode(mime_type=mime_type),
            mime_type=mime_type,
            name=name
        )

    return None


def __is_socket(sockets_or_slots):
    return isinstance(sockets_or_slots[0], bpy.types.NodeSocket)


def __is_slot(sockets_or_slots):
    return isinstance(sockets_or_slots[0], bpy.types.MaterialTextureSlot)


def __get_image_data(sockets_or_slots, export_settings) -> ExportImage:
    # For shared resources, such as images, we just store the portion of data that is needed in the glTF property
    # in a helper class. During generation of the glTF in the exporter these will then be combined to actual binary
    # resources.
    if __is_socket(sockets_or_slots):
        results = [__get_tex_from_socket(socket, export_settings) for socket in sockets_or_slots]
        composed_image = ExportImage()
        for result, socket in zip(results, sockets_or_slots):
            if result.shader_node.image.channels == 0:
                gltf2_io_debug.print_console("WARNING",
                                             "Image '{}' has no color channels and cannot be exported.".format(
                                                 result.shader_node.image))
                continue

            # rudimentarily try follow the node tree to find the correct image data.
            src_chan = Channel.R
            for elem in result.path:
                if isinstance(elem.from_node, bpy.types.ShaderNodeSeparateRGB):
                   src_chan = {
                        'R': Channel.R,
                        'G': Channel.G,
                        'B': Channel.B,
                    }[elem.from_socket.name]

            dst_chan = None

            # some sockets need channel rewriting (gltf pbr defines fixed channels for some attributes)
            if socket.name == 'Metallic':
                dst_chan = Channel.B
            elif socket.name == 'Roughness':
                dst_chan = Channel.G
            elif socket.name == 'Occlusion' and len(sockets_or_slots) > 1 and sockets_or_slots[1] is not None:
                dst_chan = Channel.R
            elif socket.name == 'Alpha' and len(sockets_or_slots) > 1 and sockets_or_slots[1] is not None:
                dst_chan = Channel.A

            if dst_chan is not None:
                composed_image.fill_image(result.shader_node.image, dst_chan, src_chan)

                # Since metal/roughness are always used together, make sure
                # the other channel is filled.
                if socket.name == 'Metallic' and not composed_image.is_filled(Channel.G):
                    composed_image.fill_white(Channel.G)
                elif socket.name == 'Roughness' and not composed_image.is_filled(Channel.B):
                    composed_image.fill_white(Channel.B)
            else:
                # copy full image...eventually following sockets might overwrite things
                composed_image = ExportImage.from_blender_image(result.shader_node.image)

        return composed_image

    elif __is_slot(sockets_or_slots):
        texture = __get_tex_from_slot(sockets_or_slots[0])
        image = ExportImage.from_blender_image(texture.image)
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
        combined_name = None
        foundNames = []
        # If multiple images are being combined, combine the names as well.
        for socket in sockets_or_slots:
            node = __get_tex_from_socket(socket, export_settings)
            if node is not None:
                image_name = node.shader_node.image.name
                if image_name not in foundNames:
                    foundNames.append(image_name)
                    name, extension = os.path.splitext(image_name)
                    if combined_name is None:
                        combined_name = name
                    else:
                        combined_name += '-' + name

        # If only one image was used, and that image has a real filepath, use the real filepath instead.
        if len(foundNames) == 1:
            filename = os.path.basename(bpy.data.images[foundNames[0]].filepath)
            name, extension = os.path.splitext(filename)
            if extension.lower() in ['.png', '.jpg', '.jpeg']:
                return name

        return combined_name

    elif isinstance(sockets_or_slots[0], bpy.types.MaterialTextureSlot):
        return sockets_or_slots[0].texture.image.name


@cached
def __get_extension_from_slot(sockets_or_slots, export_settings):
    if __is_socket(sockets_or_slots):
        for socket in sockets_or_slots:
            node = __get_tex_from_socket(socket, export_settings)
            if node is not None:
                image_name = node.shader_node.image.name
                filepath = bpy.data.images[image_name].filepath
                name, extension = os.path.splitext(filepath)
                if extension:
                    return extension
        return '.png'

    elif isinstance(sockets_or_slots[0], bpy.types.MaterialTextureSlot):
        image_name = sockets_or_slots[0].texture.image.name
        filepath = bpy.data.images[image_name].filepath
        name, extension = os.path.splitext(filepath)
        return extension
