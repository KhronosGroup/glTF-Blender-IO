# Copyright 2018-2022 The glTF-Blender-IO authors.
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
from .....io.com.gltf2_io_extensions import Extension
from ...material import gltf2_blender_gather_texture_info
from ..gltf2_blender_search_node_tree import has_image_node_from_socket, get_socket, get_factor_from_socket

def export_clearcoat(blender_material, export_settings):
    clearcoat_enabled = False
    has_clearcoat_texture = False
    has_clearcoat_roughness_texture = False

    clearcoat_extension = {}
    clearcoat_roughness_slots = ()

    clearcoat_socket = get_socket(blender_material, 'Coat Weight')
    clearcoat_roughness_socket = get_socket(blender_material, 'Coat Roughness')
    clearcoat_normal_socket = get_socket(blender_material, 'Coat Normal')

    if isinstance(clearcoat_socket.socket, bpy.types.NodeSocket) and not clearcoat_socket.socket.is_linked:
        clearcoat_extension['clearcoatFactor'] = clearcoat_socket.socket.default_value
        clearcoat_enabled = clearcoat_extension['clearcoatFactor'] > 0
    elif has_image_node_from_socket(clearcoat_socket, export_settings):
        fac = get_factor_from_socket(clearcoat_socket, kind='VALUE')
        # default value in glTF is 0.0, but if there is a texture without factor, use 1
        clearcoat_extension['clearcoatFactor'] = fac if fac != None else 1.0
        has_clearcoat_texture = True
        clearcoat_enabled = True

    if not clearcoat_enabled:
        return None, {}, {}

    if isinstance(clearcoat_roughness_socket.socket, bpy.types.NodeSocket) and not clearcoat_roughness_socket.socket.is_linked:
        clearcoat_extension['clearcoatRoughnessFactor'] = clearcoat_roughness_socket.socket.default_value
    elif has_image_node_from_socket(clearcoat_roughness_socket, export_settings):
        fac = get_factor_from_socket(clearcoat_roughness_socket, kind='VALUE')
        # default value in glTF is 0.0, but if there is a texture without factor, use 1
        clearcoat_extension['clearcoatRoughnessFactor'] = fac if fac != None else 1.0
        has_clearcoat_roughness_texture = True

    # Pack clearcoat (R) and clearcoatRoughness (G) channels.
    if has_clearcoat_texture and has_clearcoat_roughness_texture:
        clearcoat_roughness_slots = (clearcoat_socket, clearcoat_roughness_socket,)
    elif has_clearcoat_texture:
        clearcoat_roughness_slots = (clearcoat_socket,)
    elif has_clearcoat_roughness_texture:
        clearcoat_roughness_slots = (clearcoat_roughness_socket,)

    uvmap_infos = {}
    udim_infos = {}

    if len(clearcoat_roughness_slots) > 0:
        if has_clearcoat_texture:
            clearcoat_texture, uvmap_info, udim_info, _ = gltf2_blender_gather_texture_info.gather_texture_info(
                clearcoat_socket,
                clearcoat_roughness_slots,
                export_settings,
            )
            clearcoat_extension['clearcoatTexture'] = clearcoat_texture
            uvmap_infos.update({'clearcoatTexture' : uvmap_info})
            udim_infos.update({'clearcoatTexture' : udim_info} if len(udim_info.keys()) > 0 else {})

        if has_clearcoat_roughness_texture:
            clearcoat_roughness_texture, uvmap_info, udim_info, _ = gltf2_blender_gather_texture_info.gather_texture_info(
                clearcoat_roughness_socket,
                clearcoat_roughness_slots,
                export_settings,
            )
            clearcoat_extension['clearcoatRoughnessTexture'] = clearcoat_roughness_texture
            uvmap_infos.update({'clearcoatRoughnessTexture': uvmap_info})
            udim_infos.update({'clearcoatRoughnessTexture': udim_info} if len(udim_info.keys()) > 0 else {})

    if has_image_node_from_socket(clearcoat_normal_socket, export_settings):
        clearcoat_normal_texture, uvmap_info, udim_info, _ = gltf2_blender_gather_texture_info.gather_material_normal_texture_info_class(
            clearcoat_normal_socket,
            (clearcoat_normal_socket,),
            export_settings
        )
        clearcoat_extension['clearcoatNormalTexture'] = clearcoat_normal_texture
        uvmap_infos.update({'clearcoatNormalTexture': uvmap_info})
        udim_infos.update({'clearcoatNormalTexture': udim_info} if len(udim_info.keys()) > 0 else {})

    return Extension('KHR_materials_clearcoat', clearcoat_extension, False), uvmap_infos, udim_infos
