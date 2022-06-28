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


def export_sheen(blender_material, export_settings):
    sheen_extension = {}

    sheenColor_socket = gltf2_blender_get.get_socket(blender_material, "sheenColor")
    sheenRoughness_socket = gltf2_blender_get.get_socket(blender_material, "sheenRoughness")

    if sheenColor_socket is None or sheenRoughness_socket is None:
        return None, None

    sheenColor_non_linked = isinstance(sheenColor_socket, bpy.types.NodeSocket) and not sheenColor_socket.is_linked
    sheenRoughness_non_linked = isinstance(sheenRoughness_socket, bpy.types.NodeSocket) and not sheenRoughness_socket.is_linked


    use_actives_uvmaps = []

    if sheenColor_non_linked is True:
        color = sheenColor_socket.default_value[:3]
        if color != (0.0, 0.0, 0.0):
            sheen_extension['sheenColorFactor'] = color
    else:
        # Factor
        fac = gltf2_blender_get.get_factor_from_socket(sheenColor_socket, kind='RGB')
        if fac is not None and fac != [0.0, 0.0, 0.0]:
            sheen_extension['sheenColorFactor'] = fac
        
        # Texture
        if gltf2_blender_get.has_image_node_from_socket(sheenColor_socket):
            original_sheenColor_texture, original_sheenColor_use_active_uvmap, _ = gltf2_blender_gather_texture_info.gather_texture_info(
                sheenColor_socket,
                (sheenColor_socket,),
                export_settings,
            )
            sheen_extension['sheenColorTexture'] = original_sheenColor_texture
            if original_sheenColor_use_active_uvmap:
                use_actives_uvmaps.append("sheenColorTexture")


    if sheenRoughness_non_linked is True:
        fac = sheenRoughness_socket.default_value
        if fac != 0.0:
            sheen_extension['sheenRoughnessFactor'] = fac
    else:
        # Factor
        fac = gltf2_blender_get.get_factor_from_socket(sheenRoughness_socket, kind='VALUE')
        if fac is not None and fac != 0.0:
            sheen_extension['sheenRoughnessFactor'] = fac
        
        # Texture
        if gltf2_blender_get.has_image_node_from_socket(sheenRoughness_socket):
            original_sheenRoughness_texture, original_sheenRoughness_use_active_uvmap, _ = gltf2_blender_gather_texture_info.gather_texture_info(
                sheenRoughness_socket,
                (sheenRoughness_socket,),
                export_settings,
            )
            sheen_extension['sheenRoughnessTexture'] = original_sheenRoughness_texture
            if original_sheenRoughness_use_active_uvmap:
                use_actives_uvmaps.append("sheenRoughnessTexture")
    
    return Extension('KHR_materials_sheen', sheen_extension, False), use_actives_uvmaps
