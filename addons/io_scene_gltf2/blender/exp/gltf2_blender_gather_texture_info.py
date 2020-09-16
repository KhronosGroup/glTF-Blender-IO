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
from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached
from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.blender.exp import gltf2_blender_gather_texture
from io_scene_gltf2.blender.exp import gltf2_blender_search_node_tree
from io_scene_gltf2.blender.exp import gltf2_blender_get
from io_scene_gltf2.io.com.gltf2_io_extensions import Extension
from io_scene_gltf2.io.exp.gltf2_io_user_extensions import export_user_extensions


# blender_shader_sockets determine the texture and primary_socket determines
# the textranform and UVMap. Ex: when combining an ORM texture, for
# occlusion the primary_socket would be the occlusion socket, and
# blender_shader_sockets would be the (O,R,M) sockets.

def gather_texture_info(primary_socket, blender_shader_sockets, export_settings):
    return __gather_texture_info_helper(primary_socket, blender_shader_sockets, 'DEFAULT', export_settings)

def gather_material_normal_texture_info_class(primary_socket, blender_shader_sockets, export_settings):
    return __gather_texture_info_helper(primary_socket, blender_shader_sockets, 'NORMAL', export_settings)

def gather_material_occlusion_texture_info_class(primary_socket, blender_shader_sockets, export_settings):
    return __gather_texture_info_helper(primary_socket, blender_shader_sockets, 'OCCLUSION', export_settings)


@cached
def __gather_texture_info_helper(
        primary_socket: bpy.types.NodeSocket,
        blender_shader_sockets: typing.Tuple[bpy.types.NodeSocket],
        kind: str,
        export_settings):
    if not __filter_texture_info(primary_socket, blender_shader_sockets, export_settings):
        return None

    fields = {
        'extensions': __gather_extensions(primary_socket, export_settings),
        'extras': __gather_extras(blender_shader_sockets, export_settings),
        'index': __gather_index(blender_shader_sockets, export_settings),
        'tex_coord': __gather_tex_coord(primary_socket, export_settings),
    }

    if kind == 'DEFAULT':
        texture_info = gltf2_io.TextureInfo(**fields)

    elif kind == 'NORMAL':
        fields['scale'] = __gather_normal_scale(primary_socket, export_settings)
        texture_info = gltf2_io.MaterialNormalTextureInfoClass(**fields)

    elif kind == 'OCCLUSION':
        fields['strength'] = __gather_occlusion_strength(primary_socket, export_settings)
        texture_info = gltf2_io.MaterialOcclusionTextureInfoClass(**fields)

    if texture_info.index is None:
        return None

    export_user_extensions('gather_texture_info_hook', export_settings, texture_info, blender_shader_sockets)

    return texture_info


def __filter_texture_info(primary_socket, blender_shader_sockets, export_settings):
    if primary_socket is None:
        return False
    if __get_tex_from_socket(primary_socket) is None:
        return False
    if not blender_shader_sockets:
        return False
    if not all([elem is not None for elem in blender_shader_sockets]):
        return False
    if any([__get_tex_from_socket(socket) is None for socket in blender_shader_sockets]):
        # sockets do not lead to a texture --> discard
        return False

    return True


def __gather_extensions(primary_socket, export_settings):
    if not hasattr(primary_socket, 'links'):
        return None

    texture_node = __get_tex_from_socket(primary_socket).shader_node
    if texture_node is None:
        return None
    texture_transform = gltf2_blender_get.get_texture_transform_from_texture_node(texture_node)
    if texture_transform is None:
        return None

    extension = Extension("KHR_texture_transform", texture_transform)
    return {"KHR_texture_transform": extension}


def __gather_extras(blender_shader_sockets, export_settings):
    return None


# MaterialNormalTextureInfo only
def __gather_normal_scale(primary_socket, export_settings):
    result = gltf2_blender_search_node_tree.from_socket(
        primary_socket,
        gltf2_blender_search_node_tree.FilterByType(bpy.types.ShaderNodeNormalMap))
    if not result:
        return None
    strengthInput = result[0].shader_node.inputs['Strength']
    if not strengthInput.is_linked and strengthInput.default_value != 1:
        return strengthInput.default_value
    return None


# MaterialOcclusionTextureInfo only
def __gather_occlusion_strength(primary_socket, export_settings):
    return None


def __gather_index(blender_shader_sockets, export_settings):
    # We just put the actual shader into the 'index' member
    return gltf2_blender_gather_texture.gather_texture(blender_shader_sockets, export_settings)


def __gather_tex_coord(primary_socket, export_settings):
    blender_shader_node = __get_tex_from_socket(primary_socket).shader_node
    if len(blender_shader_node.inputs['Vector'].links) == 0:
        return 0

    input_node = blender_shader_node.inputs['Vector'].links[0].from_node

    if isinstance(input_node, bpy.types.ShaderNodeMapping):

        if len(input_node.inputs['Vector'].links) == 0:
            return 0

        input_node = input_node.inputs['Vector'].links[0].from_node

    if not isinstance(input_node, bpy.types.ShaderNodeUVMap):
        return 0

    if input_node.uv_map == '':
        return 0

    # Try to gather map index.
    for blender_mesh in bpy.data.meshes:
        texCoordIndex = blender_mesh.uv_layers.find(input_node.uv_map)
        if texCoordIndex >= 0:
            return texCoordIndex

    return 0


def __get_tex_from_socket(socket):
    result = gltf2_blender_search_node_tree.from_socket(
        socket,
        gltf2_blender_search_node_tree.FilterByType(bpy.types.ShaderNodeTexImage))
    if not result:
        return None
    if result[0].shader_node.image is None:
        return None
    return result[0]


def check_same_size_images(
    blender_shader_sockets: typing.Tuple[bpy.types.NodeSocket],
) -> bool:
    """Check that all sockets leads to images of the same size."""
    if not blender_shader_sockets or not all(blender_shader_sockets):
        return False

    sizes = set()
    for socket in blender_shader_sockets:
        tex = __get_tex_from_socket(socket)
        if tex is None:
            return False
        size = tex.shader_node.image.size
        sizes.add((size[0], size[1]))

    return len(sizes) == 1
