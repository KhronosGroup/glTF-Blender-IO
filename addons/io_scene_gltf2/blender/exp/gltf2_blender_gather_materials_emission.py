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

def export_emission_factor(blender_material, export_settings):
    emissive_socket = gltf2_blender_get.get_socket(blender_material, "Emissive")
    if emissive_socket is None:
        emissive_socket = gltf2_blender_get.get_socket_old(blender_material, "EmissiveFactor")
    if isinstance(emissive_socket, bpy.types.NodeSocket):
        if export_settings['gltf_image_format'] != "NONE":
            factor = gltf2_blender_get.get_factor_from_socket(emissive_socket, kind='RGB')
        else:
            factor = gltf2_blender_get.get_const_from_default_value_socket(emissive_socket, kind='RGB')

        if factor is None and emissive_socket.is_linked:
            # In glTF, the default emissiveFactor is all zeros, so if an emission texture is connected,
            # we have to manually set it to all ones.
            factor = [1.0, 1.0, 1.0]

        if factor is None: factor = [0.0, 0.0, 0.0]

        # Handle Emission Strength
        strength_socket = None
        if emissive_socket.node.type == 'EMISSION':
            strength_socket = emissive_socket.node.inputs['Strength']
        elif 'Emission Strength' in emissive_socket.node.inputs:
            strength_socket = emissive_socket.node.inputs['Emission Strength']
        strength = (
            gltf2_blender_get.get_const_from_socket(strength_socket, kind='VALUE')
            if strength_socket is not None
            else None
        )
        if strength is not None:
            factor = [f * strength for f in factor]

        # Clamp to range [0,1]
        # Official glTF clamp to range [0,1]
        # If we are outside, we need to use extension KHR_materials_emissive_strength

        if factor == [0, 0, 0]: factor = None

        return factor

    return None

def export_emission_texture(blender_material, export_settings):
    emissive = gltf2_blender_get.get_socket(blender_material, "Emissive")
    if emissive is None:
        emissive = gltf2_blender_get.get_socket_old(blender_material, "Emissive")
    emissive_texture, use_actives_uvmap_emissive, _ = gltf2_blender_gather_texture_info.gather_texture_info(emissive, (emissive,), export_settings)
    return emissive_texture, ["emissiveTexture"] if use_actives_uvmap_emissive else None

def export_emission_strength_extension(emissive_factor, export_settings):
    emissive_strength_extension = {}
    emissive_strength_extension['emissiveStrength'] = max(emissive_factor)

    return Extension('KHR_materials_emissive_strength', emissive_strength_extension, False)
