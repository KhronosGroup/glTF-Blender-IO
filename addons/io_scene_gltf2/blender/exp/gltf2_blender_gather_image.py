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
import typing
import os

from . import gltf2_blender_export_keys
from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.blender.exp import gltf2_blender_search_node_tree
from io_scene_gltf2.io.exp import gltf2_io_binary_data
from io_scene_gltf2.io.exp import gltf2_io_image_data
from io_scene_gltf2.io.com import gltf2_io_debug
from io_scene_gltf2.blender.exp.gltf2_blender_image import Channel, ExportImage, FillImage
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

    mime_type = __gather_mime_type(blender_shader_sockets_or_texture_slots, image_data, export_settings)
    name = __gather_name(image_data, export_settings)

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


def __gather_mime_type(sockets_or_slots, export_image, export_settings):
    # force png if Alpha contained so we can export alpha
    for socket in sockets_or_slots:
        if socket.name == "Alpha":
            return "image/png"

    if export_settings["gltf_image_format"] == "AUTO":
        image = export_image.blender_image()
        if image is not None and __is_blender_image_a_jpeg(image):
            return "image/jpeg"
        return "image/png"

    elif export_settings["gltf_image_format"] == "JPEG":
        return "image/jpeg"


def __gather_name(export_image, export_settings):
    # Find all Blender images used in the ExportImage
    imgs = []
    for fill in export_image.fills.values():
        if isinstance(fill, FillImage):
            img = fill.image
            if img not in imgs:
                imgs.append(img)

    # If all the images have the same path, use the common filename
    filepaths = set(img.filepath for img in imgs)
    if len(filepaths) == 1:
        filename = os.path.basename(list(filepaths)[0])
        name, extension = os.path.splitext(filename)
        if extension.lower() in ['.png', '.jpg', '.jpeg']:
            if name:
                return name

    # Combine the image names: img1-img2-img3
    names = []
    for img in imgs:
        name, extension = os.path.splitext(img.name)
        names.append(name)
    name = '-'.join(names)
    return name or 'Image'



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
                if elem.from_socket.name == 'Alpha':
                    src_chan = Channel.A

            dst_chan = None

            # some sockets need channel rewriting (gltf pbr defines fixed channels for some attributes)
            if socket.name == 'Metallic':
                dst_chan = Channel.B
            elif socket.name == 'Roughness':
                dst_chan = Channel.G
            elif socket.name == 'Occlusion':
                dst_chan = Channel.R
            elif socket.name == 'Alpha' and len(sockets_or_slots) > 1 and sockets_or_slots[1] is not None:
                dst_chan = Channel.A
            elif socket.name == 'Clearcoat':
                dst_chan = Channel.R
            elif socket.name == 'Clearcoat Roughness':
                dst_chan = Channel.G

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


def __is_blender_image_a_jpeg(image: bpy.types.Image) -> bool:
    if image.source != 'FILE':
        return False
    path = image.filepath_raw.lower()
    return path.endswith('.jpg') or path.endswith('.jpeg') or path.endswith('.jpe')
