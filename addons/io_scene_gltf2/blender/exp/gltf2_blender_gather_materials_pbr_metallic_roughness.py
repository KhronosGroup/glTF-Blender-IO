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

from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.blender.exp import gltf2_blender_gather_texture_info, gltf2_blender_search_node_tree
from io_scene_gltf2.blender.exp import gltf2_blender_get
from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached
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
    if not blender_material.use_nodes:
        return [*blender_material.diffuse_color[:3], 1.0]

    rgb, alpha = None, None

    alpha_socket = gltf2_blender_get.get_socket(blender_material, "Alpha")
    if isinstance(alpha_socket, bpy.types.NodeSocket):
        alpha = gltf2_blender_get.get_factor_from_socket(alpha_socket, kind='VALUE')

    base_color_socket = gltf2_blender_get.get_socket(blender_material, "Base Color")
    if base_color_socket is None:
        base_color_socket = gltf2_blender_get.get_socket(blender_material, "BaseColor")
    if base_color_socket is None:
        base_color_socket = gltf2_blender_get.get_socket_old(blender_material, "BaseColorFactor")
    if isinstance(base_color_socket, bpy.types.NodeSocket):
        rgb = gltf2_blender_get.get_factor_from_socket(base_color_socket, kind='RGB')

    if rgb is None: rgb = [1.0, 1.0, 1.0]
    if alpha is None: alpha = 1.0

    rgba = [*rgb, alpha]

    if rgba == [1, 1, 1, 1]: return None
    return rgba


def __gather_base_color_texture(blender_material, export_settings):
    base_color_socket = gltf2_blender_get.get_socket(blender_material, "Base Color")
    if base_color_socket is None:
        base_color_socket = gltf2_blender_get.get_socket(blender_material, "BaseColor")
    if base_color_socket is None:
        base_color_socket = gltf2_blender_get.get_socket_old(blender_material, "BaseColor")

    alpha_socket = gltf2_blender_get.get_socket(blender_material, "Alpha")

    # keep sockets that have some texture : color and/or alpha
    inputs = tuple(
        socket for socket in [base_color_socket, alpha_socket]
        if socket is not None and __has_image_node_from_socket(socket)
    )
    if not inputs:
        return None

    return gltf2_blender_gather_texture_info.gather_texture_info(inputs[0], inputs, export_settings)


def __gather_extensions(blender_material, export_settings):
    return None


def __gather_extras(blender_material, export_settings):
    return None


def __gather_metallic_factor(blender_material, export_settings):
    if not blender_material.use_nodes:
        return blender_material.metallic

    metallic_socket = gltf2_blender_get.get_socket(blender_material, "Metallic")
    if metallic_socket is None:
        metallic_socket = gltf2_blender_get.get_socket_old(blender_material, "MetallicFactor")
    if isinstance(metallic_socket, bpy.types.NodeSocket):
        fac = gltf2_blender_get.get_factor_from_socket(metallic_socket, kind='VALUE')
        return fac if fac != 1 else None
    return None


def __gather_metallic_roughness_texture(blender_material, orm_texture, export_settings):
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

    return gltf2_blender_gather_texture_info.gather_texture_info(
        texture_input[0],
        orm_texture or texture_input,
        export_settings,
    )


def __gather_roughness_factor(blender_material, export_settings):
    if not blender_material.use_nodes:
        return blender_material.roughness

    roughness_socket = gltf2_blender_get.get_socket(blender_material, "Roughness")
    if roughness_socket is None:
        roughness_socket = gltf2_blender_get.get_socket_old(blender_material, "RoughnessFactor")
    if isinstance(roughness_socket, bpy.types.NodeSocket):
        fac = gltf2_blender_get.get_factor_from_socket(roughness_socket, kind='VALUE')
        return fac if fac != 1 else None
    return None

def __has_image_node_from_socket(socket):
    result = gltf2_blender_search_node_tree.from_socket(
        socket,
        gltf2_blender_search_node_tree.FilterByType(bpy.types.ShaderNodeTexImage))
    if not result:
        return False
    return True
