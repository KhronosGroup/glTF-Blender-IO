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

from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.blender.exp import gltf2_blender_gather_texture
from io_scene_gltf2.blender.exp import gltf2_blender_search_node_tree
from io_scene_gltf2.blender.exp import gltf2_blender_get

def gather_material_pbr_metallic_roughness(blender_material, export_settings):
    if not __filter_pbr_material(blender_material, export_settings):
        return None

    material = gltf2_io.MaterialPBRMetallicRoughness(
        base_color_factor=__gather_base_color_factor(blender_material, export_settings),
        base_color_texture=__gather_base_color_texture(blender_material, export_settings),
        extensions=__gather_extensions(blender_material, export_settings),
        extras=__gather_extras(blender_material, export_settings),
        metallic_factor= __gather_metallic_factor(blender_material, export_settings),
        metallic_roughness_texture=__gather_metallic_roughness_texture(blender_material, export_settings),
        roughness_factor= __gather_roughness_factor(blender_material, export_settings)
    )

    return material


def __filter_pbr_material(blender_material, export_settings):
    return True


def __gather_base_color_factor(blender_material, export_settings):
    # TODO
    return None


def __gather_base_color_texture(blender_material, export_settings):
    base_color_socket = gltf2_blender_get.get_socket_or_texture_slot(blender_material, "Base Color")
    return gltf2_blender_gather_texture.gather_texture([base_color_socket], export_settings)


def __gather_extensions(blender_material, export_settings):
    return None


def __gather_extras(blender_material, export_settings):
    return None


def __gather_metallic_factor(blender_material, export_settings):
    # TODO
    return None


def __gather_metallic_roughness_texture(blender_material, export_settings):
    metallic_socket = gltf2_blender_get.get_socket_or_texture_slot(blender_material, "Metallic")
    roughness_socket = gltf2_blender_get.get_socket_or_texture_slot(blender_material, "Roughness")

    return gltf2_blender_gather_texture.gather_texture([metallic_socket, roughness_socket], export_settings)


def __gather_roughness_factor(blender_material, export_settings):
    return None