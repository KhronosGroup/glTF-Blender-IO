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

from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.blender.exp import gltf2_blender_gather_texture_info, gltf2_blender_search_node_tree
from io_scene_gltf2.blender.exp import gltf2_blender_get
from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached
from io_scene_gltf2.io.com.gltf2_io_debug import print_console
from io_scene_gltf2.io.exp.gltf2_io_user_extensions import export_user_extensions


@cached
def gather_material_pbr_metallic_roughness(blender_material, orm_texture, export_settings):
    if not __filter_pbr_material(blender_material, export_settings):
        return None

    material = gltf2_io.MaterialPBRMetallicRoughness(
        base_color_factor=__gather_base_color_factor(blender_material, export_settings),
        base_color_texture=__gather_base_color_texture(blender_material, export_settings),
        extensions=__gather_extensions(blender_material, export_settings),
        extras=__gather_extras(blender_material, export_settings),
        metallic_factor=__gather_metallic_factor(blender_material, export_settings),
        metallic_roughness_texture=__gather_metallic_roughness_texture(blender_material, orm_texture, export_settings),
        roughness_factor=__gather_roughness_factor(blender_material, export_settings)
    )

    export_user_extensions('gather_material_pbr_metallic_roughness_hook', export_settings, material, blender_material, orm_texture)

    return material


def __filter_pbr_material(blender_material, export_settings):
    return True


def __gather_base_color_factor(blender_material, export_settings):
    alpha_socket = gltf2_blender_get.get_socket(blender_material, "Alpha")
    alpha = alpha_socket.default_value if alpha_socket is not None and not alpha_socket.is_linked else 1.0

    base_color_socket = gltf2_blender_get.get_socket(blender_material, "Base Color")
    if base_color_socket is None:
        base_color_socket = gltf2_blender_get.get_socket(blender_material, "BaseColor")
    if base_color_socket is None:
        base_color_socket = gltf2_blender_get.get_socket_old(blender_material, "BaseColorFactor")
    if base_color_socket is None:
        base_color_socket = gltf2_blender_get.get_socket(blender_material, "Background")
    if not isinstance(base_color_socket, bpy.types.NodeSocket):
        return None
    if not base_color_socket.is_linked:
        return list(base_color_socket.default_value)[:3] + [alpha]

    texture_node = __get_tex_from_socket(base_color_socket)
    if texture_node is None:
        return None

    def is_valid_multiply_node(node):
        return isinstance(node, bpy.types.ShaderNodeMixRGB) and \
               node.blend_type == "MULTIPLY" and \
               len(node.inputs) == 3

    multiply_node = next((link.from_node for link in texture_node.path if is_valid_multiply_node(link.from_node)), None)
    if multiply_node is None:
        return None

    def is_factor_socket(socket):
        return isinstance(socket, bpy.types.NodeSocketColor) and \
               (not socket.is_linked or socket.links[0] not in texture_node.path)

    factor_socket = next((socket for socket in multiply_node.inputs if is_factor_socket(socket)), None)
    if factor_socket is None:
        return None

    if factor_socket.is_linked:
        print_console("WARNING", "BaseColorFactor only supports sockets without links (in Node '{}')."
                      .format(multiply_node.name))
        return None

    return list(factor_socket.default_value)[:3] + [alpha]


def __gather_base_color_texture(blender_material, export_settings):
    base_color_socket = gltf2_blender_get.get_socket(blender_material, "Base Color")
    if base_color_socket is None:
        base_color_socket = gltf2_blender_get.get_socket(blender_material, "BaseColor")
    if base_color_socket is None:
        base_color_socket = gltf2_blender_get.get_socket_old(blender_material, "BaseColor")
    if base_color_socket is None:
        base_color_socket = gltf2_blender_get.get_socket(blender_material, "Background")

    alpha_socket = gltf2_blender_get.get_socket(blender_material, "Alpha")
    if alpha_socket is not None and alpha_socket.is_linked:
        inputs = (base_color_socket, alpha_socket, )
    else:
        inputs = (base_color_socket,)

    return gltf2_blender_gather_texture_info.gather_texture_info(inputs, export_settings)


def __get_tex_from_socket(blender_shader_socket: bpy.types.NodeSocket):
    result = gltf2_blender_search_node_tree.from_socket(
        blender_shader_socket,
        gltf2_blender_search_node_tree.FilterByType(bpy.types.ShaderNodeTexImage))
    if not result:
        return None
    return result[0]


def __gather_extensions(blender_material, export_settings):
    return None


def __gather_extras(blender_material, export_settings):
    return None


def __gather_metallic_factor(blender_material, export_settings):
    metallic_socket = gltf2_blender_get.get_socket(blender_material, "Metallic")
    if metallic_socket is None:
        metallic_socket = gltf2_blender_get.get_socket_old(blender_material, "MetallicFactor")
    if isinstance(metallic_socket, bpy.types.NodeSocket) and not metallic_socket.is_linked:
        return metallic_socket.default_value
    return None


def __gather_metallic_roughness_texture(blender_material, orm_texture, export_settings):
    if orm_texture is not None:
        texture_input = orm_texture
    else:
        metallic_socket = gltf2_blender_get.get_socket(blender_material, "Metallic")
        roughness_socket = gltf2_blender_get.get_socket(blender_material, "Roughness")

        hasMetal = metallic_socket is not None and __has_image_node_from_socket(metallic_socket)
        hasRough = roughness_socket is not None and __has_image_node_from_socket(roughness_socket)

        if not hasMetal and not hasRough:
            metallic_roughness = gltf2_blender_get.get_socket_old(blender_material, "MetallicRoughness")
            if metallic_roughness is None or not __has_image_node_from_socket(metallic_roughness):
                return None
            texture_input = (metallic_roughness,)
        elif not hasMetal:
            texture_input = (roughness_socket,)
        elif not hasRough:
            texture_input = (metallic_socket,)
        else:
            texture_input = (metallic_socket, roughness_socket)

    return gltf2_blender_gather_texture_info.gather_texture_info(texture_input, export_settings)


def __gather_roughness_factor(blender_material, export_settings):
    roughness_socket = gltf2_blender_get.get_socket(blender_material, "Roughness")
    if roughness_socket is None:
        roughness_socket = gltf2_blender_get.get_socket_old(blender_material, "RoughnessFactor")
    if isinstance(roughness_socket, bpy.types.NodeSocket) and not roughness_socket.is_linked:
        return roughness_socket.default_value
    return None

def __has_image_node_from_socket(socket):
    result = gltf2_blender_search_node_tree.from_socket(
        socket,
        gltf2_blender_search_node_tree.FilterByType(bpy.types.ShaderNodeTexImage))
    if not result:
        return False
    return True
