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
from ....exp import gltf2_blender_get
from ...material import gltf2_blender_gather_texture_info


def export_sheen(blender_material, export_settings):
    sheen_extension = {}

    sheenTint_socket = gltf2_blender_get.get_socket(blender_material, "Sheen Tint")
    sheenRoughness_socket = gltf2_blender_get.get_socket(blender_material, "Sheen Roughness")
    sheen_socket = gltf2_blender_get.get_socket(blender_material, "Sheen")

    if sheenTint_socket is None or sheenRoughness_socket is None or sheen_socket is None:
        return None, None

    if sheen_socket.is_linked is False and sheen_socket.default_value == 0.0:
        return None, None

    #TODOExt : What to do if sheen_socket is linked?

    sheenTint_non_linked = isinstance(sheenTint_socket, bpy.types.NodeSocket) and not sheenTint_socket.is_linked
    sheenRoughness_non_linked = isinstance(sheenRoughness_socket, bpy.types.NodeSocket) and not sheenRoughness_socket.is_linked


    use_actives_uvmaps = []

    if sheenTint_non_linked is True:
        color = sheenTint_socket.default_value[:3]
        if color != (0.0, 0.0, 0.0):
            sheen_extension['sheenColorFactor'] = color
    else:
        # Factor
        fac = gltf2_blender_get.get_factor_from_socket(sheenTint_socket, kind='RGB')
        if fac is None:
            fac = [1.0, 1.0, 1.0] # Default is 0.0/0.0/0.0, so we need to set it to 1 if no factor
        if fac is not None and fac != [0.0, 0.0, 0.0]:
            sheen_extension['sheenColorFactor'] = fac

        # Texture
        if gltf2_blender_get.has_image_node_from_socket(sheenTint_socket):
            original_sheenColor_texture, original_sheenColor_use_active_uvmap, _ = gltf2_blender_gather_texture_info.gather_texture_info(
                sheenTint_socket,
                (sheenTint_socket,),
                (),
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
        if fac is None:
            fac = 1.0 # Default is 0.0 so we need to set it to 1.0 if no factor
        if fac is not None and fac != 0.0:
            sheen_extension['sheenRoughnessFactor'] = fac

        # Texture
        if gltf2_blender_get.has_image_node_from_socket(sheenRoughness_socket):
            original_sheenRoughness_texture, original_sheenRoughness_use_active_uvmap, _ = gltf2_blender_gather_texture_info.gather_texture_info(
                sheenRoughness_socket,
                (sheenRoughness_socket,),
                (),
                export_settings,
            )
            sheen_extension['sheenRoughnessTexture'] = original_sheenRoughness_texture
            if original_sheenRoughness_use_active_uvmap:
                use_actives_uvmaps.append("sheenRoughnessTexture")

    return Extension('KHR_materials_sheen', sheen_extension, False), use_actives_uvmaps
