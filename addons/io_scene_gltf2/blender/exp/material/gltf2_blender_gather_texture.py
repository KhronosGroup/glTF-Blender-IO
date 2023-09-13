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

import typing
import bpy
from ....io.com import gltf2_io_debug
from ....io.exp.gltf2_io_user_extensions import export_user_extensions
from ....io.com.gltf2_io_extensions import Extension
from ....io.exp.gltf2_io_image_data import ImageData
from ....io.exp.gltf2_io_binary_data import BinaryData
from ....io.com import gltf2_io
from ..gltf2_blender_gather_cache import cached
from ..gltf2_blender_gather_sampler import gather_sampler
from ..gltf2_blender_get import get_tex_from_socket
from . import gltf2_blender_gather_image

@cached
def gather_texture(
        blender_shader_sockets: typing.Tuple[bpy.types.NodeSocket],
        default_sockets: typing.Tuple[bpy.types.NodeSocket],
        export_settings):
    """
    Gather texture sampling information and image channels from a blender shader texture attached to a shader socket.

    :param blender_shader_sockets: The sockets of the material which should contribute to the texture
    :param export_settings: configuration of the export
    :return: a glTF 2.0 texture with sampler and source embedded (will be converted to references by the exporter)
    """

    if not __filter_texture(blender_shader_sockets, export_settings):
        return None, None

    source, webp_image, image_data, factor = __gather_source(blender_shader_sockets, default_sockets, export_settings)

    exts, remove_source = __gather_extensions(blender_shader_sockets, source, webp_image, image_data, export_settings)

    texture = gltf2_io.Texture(
        extensions=exts,
        extras=__gather_extras(blender_shader_sockets, export_settings),
        name=__gather_name(blender_shader_sockets, export_settings),
        sampler=__gather_sampler(blender_shader_sockets, export_settings),
        source=source if remove_source is False else None
    )

    # although valid, most viewers can't handle missing source properties
    # This can have None source for "keep original", when original can't be found
    if texture.source is None and remove_source is False:
        return None, None

    export_user_extensions('gather_texture_hook', export_settings, texture, blender_shader_sockets)

    return texture, factor


def __filter_texture(blender_shader_sockets, export_settings):
    # User doesn't want to export textures
    if export_settings['gltf_image_format'] == "NONE":
        return None
    return True


def __gather_extensions(blender_shader_sockets, source, webp_image, image_data, export_settings):

    extensions = {}


    remove_source = False
    required = False

    ext_wepb = {}

    # If user want to keep original textures, and these textures are webp, we need to remove source from
    # gltf2_io.Texture, and populate extension
    if export_settings['gltf_keep_original_textures'] is True \
            and source is not None \
            and source.mime_type == "image/webp":
        ext_wepb["source"] = source
        remove_source = True
        required = True

# If user want to export in webp format (so without fallback in png/jpg)
    if export_settings['gltf_image_format'] == "WEBP":
        # We create all image without fallback
        ext_wepb["source"] = source
        remove_source = True
        required = True

# If user doesn't want to export in webp format, but want webp too. Texture is not webp
    if export_settings['gltf_image_format'] != "WEBP" \
            and export_settings['gltf_add_webp'] \
            and source is not None \
            and source.mime_type != "image/webp":
        # We need here to create some webp textures

        new_mime_type = "image/webp"
        new_data, _ = image_data.encode(new_mime_type, export_settings)

        if export_settings['gltf_format'] == 'GLTF_SEPARATE':

            uri = ImageData(
                data=new_data,
                mime_type=new_mime_type,
                name=source.uri.name
            )
            buffer_view = None
            name = source.uri.name

        else:
            buffer_view = BinaryData(data=new_data)
            uri = None
            name = source.name

        webp_image = __make_webp_image(buffer_view, None, None, new_mime_type, name, uri, export_settings)

        ext_wepb["source"] = webp_image


# If user doesn't want to export in webp format, but want webp too. Texture is webp
    if export_settings['gltf_image_format'] != "WEBP" \
            and source is not None \
            and source.mime_type == "image/webp":

        # User does not want fallback
        if export_settings['gltf_webp_fallback'] is False:
            ext_wepb["source"] = source
            remove_source = True
            required = True

# If user doesn't want to export in webp format, but want webp too as fallback. Texture is webp
    if export_settings['gltf_image_format'] != "WEBP" \
            and webp_image is not None \
            and export_settings['gltf_webp_fallback'] is True:
        # Already managed in __gather_source, we only have to assign
        ext_wepb["source"] = webp_image

        # Not needed in code, for for documentation:
        # remove_source = False
        # required = False

    if len(ext_wepb) > 0:
        extensions["EXT_texture_webp"] = Extension('EXT_texture_webp', ext_wepb, required)
        return extensions, remove_source
    else:
        return None, False

@cached
def __make_webp_image(buffer_view, extensions, extras, mime_type, name, uri, export_settings):
    return gltf2_io.Image(
        buffer_view=buffer_view,
        extensions=extensions,
        extras=extras,
        mime_type=mime_type,
        name=name,
        uri=uri
    )

def __gather_extras(blender_shader_sockets, export_settings):
    return None


def __gather_name(blender_shader_sockets, export_settings):
    return None


def __gather_sampler(blender_shader_sockets, export_settings):
    shader_nodes = [get_tex_from_socket(socket) for socket in blender_shader_sockets]
    if len(shader_nodes) > 1:
        gltf2_io_debug.print_console("WARNING",
                                     "More than one shader node tex image used for a texture. "
                                     "The resulting glTF sampler will behave like the first shader node tex image.")
    first_valid_shader_node = next(filter(lambda x: x is not None, shader_nodes)).shader_node
    return gather_sampler(
        first_valid_shader_node,
        export_settings)


def __gather_source(blender_shader_sockets, default_sockets, export_settings):
    source, image_data, factor = gltf2_blender_gather_image.gather_image(blender_shader_sockets, default_sockets, export_settings)


    if export_settings['gltf_keep_original_textures'] is False \
            and export_settings['gltf_image_format'] != "WEBP" \
            and source is not None \
            and source.mime_type == "image/webp":

        if export_settings['gltf_webp_fallback'] is False:
            # Already managed in __gather_extensions
            pass
        else:
            # Need to create a PNG texture

            new_mime_type = "image/png"
            new_data, _ = image_data.encode(new_mime_type, export_settings)

            if export_settings['gltf_format'] == 'GLTF_SEPARATE':
                buffer_view = None
                uri = ImageData(
                    data=new_data,
                    mime_type=new_mime_type,
                    name=source.uri.name
                )
                name = source.uri.name

            else:
                uri = None
                buffer_view = BinaryData(data=new_data)
                name = source.name

            png_image = __make_webp_image(buffer_view, None, None, new_mime_type, name, uri, export_settings)

        # We inverted the png & webp image, to have the png as main source
        return png_image, source, image_data, factor
    return source, None, image_data, factor

# Helpers
