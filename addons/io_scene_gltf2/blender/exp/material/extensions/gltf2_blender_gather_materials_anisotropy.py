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
from ..gltf2_blender_search_node_tree import detect_anisotropy_nodes, get_socket

def export_anisotropy(blender_material, export_settings):

    anisotropy_extension = {}
    uvmap_infos = {}

    anisotropy_socket = get_socket(blender_material, 'Anisotropic')
    anisotropy_rotation_socket = get_socket(blender_material, 'Anisotropic Rotation')
    anisotropy_tangent_socket = get_socket(blender_material, 'Tangent')

    if anisotropy_socket.socket is None or anisotropy_rotation_socket.socket is None or anisotropy_tangent_socket.socket is None:
        return None, {}

    if anisotropy_socket.socket.is_linked is False and anisotropy_rotation_socket.socket.is_linked is False:
        # We don't need the complex node setup, just export the value
        anisotropyStrength = anisotropy_socket.socket.default_value
        if anisotropyStrength != 0.0:
            anisotropy_extension['anisotropyStrength'] = anisotropyStrength
        anisotropyRotation = anisotropy_rotation_socket.socket.default_value
        if anisotropyRotation != 0.0:
            anisotropy_extension['anisotropyRotation'] = anisotropyRotation

        if len(anisotropy_extension) == 0:
            return None, {}

        return Extension('KHR_materials_anisotropy', anisotropy_extension, False), uvmap_infos

    # Get complex node setup

    is_anisotropy, anisotropy_data = detect_anisotropy_nodes(
        anisotropy_socket,
        anisotropy_rotation_socket,
        anisotropy_tangent_socket,
        export_settings
    )

    if not is_anisotropy:
        return None, {}

    if anisotropy_data['anisotropyStrength'] != 0.0:
        anisotropy_extension['anisotropyStrength'] = anisotropy_data['anisotropyStrength']
    if anisotropy_data['anisotropyRotation'] != 0.0:
        anisotropy_extension['anisotropyRotation'] = anisotropy_data['anisotropyRotation']

    # Get texture data
    # No need to check here that we have a texture, this check is already done insode detect_anisotropy_nodes
    anisotropy_texture, uvmap_info , _ = gltf2_blender_gather_texture_info.gather_texture_info(
        anisotropy_data['tex_socket'],
        (anisotropy_data['tex_socket'],),
        (),
        export_settings,
    )
    anisotropy_extension['anisotropyTexture'] = anisotropy_texture
    uvmap_infos.update({'anisotropyTexture': uvmap_info})


    return Extension('KHR_materials_anisotropy', anisotropy_extension, False), uvmap_infos
