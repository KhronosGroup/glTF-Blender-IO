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
from io_scene_gltf2.io.com.gltf2_io_extensions import Extension
from io_scene_gltf2.blender.exp import gltf2_blender_get
from io_scene_gltf2.blender.exp import gltf2_blender_gather_texture_info

def export_clearcoat(blender_material, export_settings):
    clearcoat_enabled = False
    has_clearcoat_texture = False
    has_clearcoat_roughness_texture = False

    clearcoat_extension = {}
    clearcoat_roughness_slots = ()

    clearcoat_socket = gltf2_blender_get.get_socket(blender_material, 'Clearcoat')
    clearcoat_roughness_socket = gltf2_blender_get.get_socket(blender_material, 'Clearcoat Roughness')
    clearcoat_normal_socket = gltf2_blender_get.get_socket(blender_material, 'Clearcoat Normal')

    if isinstance(clearcoat_socket, bpy.types.NodeSocket) and not clearcoat_socket.is_linked:
        clearcoat_extension['clearcoatFactor'] = clearcoat_socket.default_value
        clearcoat_enabled = clearcoat_extension['clearcoatFactor'] > 0
    elif gltf2_blender_get.has_image_node_from_socket(clearcoat_socket):
        fac = gltf2_blender_get.get_factor_from_socket(clearcoat_socket, kind='VALUE')
        # default value in glTF is 0.0, but if there is a texture without factor, use 1
        clearcoat_extension['clearcoatFactor'] = fac if fac != None else 1.0
        has_clearcoat_texture = True
        clearcoat_enabled = True

    if not clearcoat_enabled:
        return None, None

    if isinstance(clearcoat_roughness_socket, bpy.types.NodeSocket) and not clearcoat_roughness_socket.is_linked:
        clearcoat_extension['clearcoatRoughnessFactor'] = clearcoat_roughness_socket.default_value
    elif gltf2_blender_get.has_image_node_from_socket(clearcoat_roughness_socket):
        fac = gltf2_blender_get.get_factor_from_socket(clearcoat_roughness_socket, kind='VALUE')
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

    use_actives_uvmaps = []

    if len(clearcoat_roughness_slots) > 0:
        if has_clearcoat_texture:
            clearcoat_texture, clearcoat_texture_use_active_uvmap, _ = gltf2_blender_gather_texture_info.gather_texture_info(
                clearcoat_socket,
                clearcoat_roughness_slots,
                export_settings,
            )
            clearcoat_extension['clearcoatTexture'] = clearcoat_texture
            if clearcoat_texture_use_active_uvmap:
                use_actives_uvmaps.append("clearcoatTexture")
        if has_clearcoat_roughness_texture:
            clearcoat_roughness_texture, clearcoat_roughness_texture_use_active_uvmap, _ = gltf2_blender_gather_texture_info.gather_texture_info(
                clearcoat_roughness_socket,
                clearcoat_roughness_slots,
                export_settings,
            )
            clearcoat_extension['clearcoatRoughnessTexture'] = clearcoat_roughness_texture
            if clearcoat_roughness_texture_use_active_uvmap:
                use_actives_uvmaps.append("clearcoatRoughnessTexture")
    if gltf2_blender_get.has_image_node_from_socket(clearcoat_normal_socket):
        clearcoat_normal_texture, clearcoat_normal_texture_use_active_uvmap, _ = gltf2_blender_gather_texture_info.gather_material_normal_texture_info_class(
            clearcoat_normal_socket,
            (clearcoat_normal_socket,),
            export_settings
        )
        clearcoat_extension['clearcoatNormalTexture'] = clearcoat_normal_texture
        if clearcoat_normal_texture_use_active_uvmap:
            use_actives_uvmaps.append("clearcoatNormalTexture")

    return Extension('KHR_materials_clearcoat', clearcoat_extension, False), use_actives_uvmaps
