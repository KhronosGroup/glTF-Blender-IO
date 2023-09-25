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


def export_volume(blender_material, export_settings):
    # Implementation based on https://github.com/KhronosGroup/glTF-Blender-IO/issues/1454#issuecomment-928319444

    # If no transmission --> No volume
    transmission_enabled = False
    transmission_socket = gltf2_blender_get.get_socket(blender_material, 'Transmission')
    if isinstance(transmission_socket, bpy.types.NodeSocket) and not transmission_socket.is_linked:
        transmission_enabled = transmission_socket.default_value > 0
    elif gltf2_blender_get.has_image_node_from_socket(transmission_socket):
        transmission_enabled = True

    if transmission_enabled is False:
        return None, {}

    volume_extension = {}
    has_thickness_texture = False
    thickness_slots = ()
    uvmap_info = {}

    thicknesss_socket = gltf2_blender_get.get_socket_old(blender_material, 'Thickness')
    if thicknesss_socket is None:
        # If no thickness (here because there is no glTF Material Output node), no volume extension export
            return None, {}

    density_socket = gltf2_blender_get.get_socket(blender_material, 'Density', volume=True)
    attenuation_color_socket = gltf2_blender_get.get_socket(blender_material, 'Color', volume=True)
    # Even if density or attenuation are not set, we export volume extension

    if isinstance(attenuation_color_socket, bpy.types.NodeSocket):
        rgb = gltf2_blender_get.get_const_from_default_value_socket(attenuation_color_socket, kind='RGB')
        volume_extension['attenuationColor'] = rgb

    if isinstance(density_socket, bpy.types.NodeSocket):
        density = gltf2_blender_get.get_const_from_default_value_socket(density_socket, kind='VALUE')
        volume_extension['attenuationDistance'] = 1.0 / density if density != 0 else None # infinity (Using None as glTF default)


    if isinstance(thicknesss_socket, bpy.types.NodeSocket) and not thicknesss_socket.is_linked:
        val = thicknesss_socket.default_value
        if val == 0.0:
            # If no thickness, no volume extension export
            return None, {}
        volume_extension['thicknessFactor'] = val
    elif gltf2_blender_get.has_image_node_from_socket(thicknesss_socket):
        fac = gltf2_blender_get.get_factor_from_socket(thicknesss_socket, kind='VALUE')
        # default value in glTF is 0.0, but if there is a texture without factor, use 1
        volume_extension['thicknessFactor'] = fac if fac != None else 1.0
        has_thickness_texture = True

       # Pack thickness channel (R).
    if has_thickness_texture:
        thickness_slots = (thicknesss_socket,)

    if len(thickness_slots) > 0:
        combined_texture, uvmap_info, _ = gltf2_blender_gather_texture_info.gather_texture_info(
            thicknesss_socket,
            thickness_slots,
            (),
            export_settings,
        )
        if has_thickness_texture:
            volume_extension['thicknessTexture'] = combined_texture

    return Extension('KHR_materials_volume', volume_extension, False), {'thicknessTexture': uvmap_info}
