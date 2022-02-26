# Copyright 2018-2021 The glTF-Blender-IO authors.
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
        blender_shader_sockets: typing.Tuple[bpy.types.NodeSocket],
        export_settings):
    if not __filter_image(blender_shader_sockets, export_settings):
        return None

    image_data = __get_image_data(blender_shader_sockets, export_settings)
    if image_data.empty():
        # The export image has no data
        return None

    mime_type = __gather_mime_type(blender_shader_sockets, image_data, export_settings)
    name = __gather_name(image_data, export_settings)

    if image_data.original is None:
        uri = __gather_uri(image_data, mime_type, name, export_settings)
    else:
        # Retrieve URI relative to exported glTF files
        uri = __gather_original_uri(image_data.original.filepath, export_settings)

    buffer_view = __gather_buffer_view(image_data, mime_type, name, export_settings)

    image = __make_image(
        buffer_view,
        __gather_extensions(blender_shader_sockets, export_settings),
        __gather_extras(blender_shader_sockets, export_settings),
        mime_type,
        name,
        uri,
        export_settings
    )

    export_user_extensions('gather_image_hook', export_settings, image, blender_shader_sockets)

    return image

def __gather_original_uri(original_uri, export_settings):

    def _path_to_uri(path):
        import urllib
        path = os.path.normpath(path)
        path = path.replace(os.sep, '/')
        return urllib.parse.quote(path)

    path_to_image = bpy.path.abspath(original_uri)
    if not os.path.exists(path_to_image): return None
    try:
        rel_path = os.path.relpath(
            path_to_image,
            start=export_settings[gltf2_blender_export_keys.FILE_DIRECTORY],
        )
    except ValueError:
        # eg. because no relative path between C:\ and D:\ on Windows
        return None
    return _path_to_uri(rel_path)


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


def __filter_image(sockets, export_settings):
    if not sockets:
        return False
    return True


@cached
def __gather_buffer_view(image_data, mime_type, name, export_settings):
    if export_settings[gltf2_blender_export_keys.FORMAT] != 'GLTF_SEPARATE':
        return gltf2_io_binary_data.BinaryData(data=image_data.encode(mime_type))
    return None


def __gather_extensions(sockets, export_settings):
    return None


def __gather_extras(sockets, export_settings):
    return None


def __gather_mime_type(sockets, export_image, export_settings):
    # force png if Alpha contained so we can export alpha
    for socket in sockets:
        if socket.name == "Alpha":
            return "image/png"

    if export_settings["gltf_image_format"] == "AUTO":
        if export_image.original is None: # We are going to create a new image
            image = export_image.blender_image()
        else:
            # Using original image
            image = export_image.original

        if image is not None and __is_blender_image_a_jpeg(image):
            return "image/jpeg"
        return "image/png"

    elif export_settings["gltf_image_format"] == "JPEG":
        return "image/jpeg"


def __gather_name(export_image, export_settings):
    if export_image.original is None:
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
    else:
        return export_image.original.name


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


def __get_image_data(sockets, export_settings) -> ExportImage:
    # For shared resources, such as images, we just store the portion of data that is needed in the glTF property
    # in a helper class. During generation of the glTF in the exporter these will then be combined to actual binary
    # resources.
    results = [__get_tex_from_socket(socket, export_settings) for socket in sockets]
    composed_image = ExportImage()
    for result, socket in zip(results, sockets):
        if result.shader_node.image.channels == 0:
            gltf2_io_debug.print_console("WARNING",
                                         "Image '{}' has no color channels and cannot be exported.".format(
                                             result.shader_node.image))
            continue

        # Assume that user know what he does, and that channels/images are already combined correctly for pbr
        # If not, we are going to keep only the first texture found
        # Example : If user set up 2 or 3 different textures for Metallic / Roughness / Occlusion
        # Only 1 will be used at export
        # This Warning is displayed in UI of this option
        if export_settings['gltf_keep_original_textures']:
            composed_image = ExportImage.from_original(result.shader_node.image)

        else:
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
            elif socket.name == 'Alpha':
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


@cached
def __get_tex_from_socket(blender_shader_socket: bpy.types.NodeSocket, export_settings):
    result = gltf2_blender_search_node_tree.from_socket(
        blender_shader_socket,
        gltf2_blender_search_node_tree.FilterByType(bpy.types.ShaderNodeTexImage))
    if not result:
        return None
    return result[0]


def __is_blender_image_a_jpeg(image: bpy.types.Image) -> bool:
    if image.source != 'FILE':
        return False
    if image.filepath_raw == '' and image.packed_file:
        return image.packed_file.data[:3] == b'\xff\xd8\xff'
    else:
        path = image.filepath_raw.lower()
        return path.endswith('.jpg') or path.endswith('.jpeg') or path.endswith('.jpe')
