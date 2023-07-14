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

def export_transmission(blender_material, export_settings):
    transmission_enabled = False
    has_transmission_texture = False

    transmission_extension = {}
    transmission_slots = ()

    transmission_socket = gltf2_blender_get.get_socket(blender_material.node_tree, blender_material.use_nodes, 'Transmission')

    if isinstance(transmission_socket, bpy.types.NodeSocket) and not transmission_socket.is_linked:
        transmission_extension['transmissionFactor'] = transmission_socket.default_value
        transmission_enabled = transmission_extension['transmissionFactor'] > 0

        path_ = {}
        path_['length'] = 1
        path_['path'] = "/materials/XXX/extensions/KHR_materials_transmission/transmissionFactor"
        export_settings['current_paths']["node_tree." + transmission_socket.path_from_id() + ".default_value"] = path_

    elif gltf2_blender_get.has_image_node_from_socket(transmission_socket):
        fac, path = gltf2_blender_get.get_factor_from_socket(transmission_socket, kind='VALUE')
        transmission_extension['transmissionFactor'] = fac if fac is not None else 1.0
        has_transmission_texture = True
        transmission_enabled = True

        # Storing path for KHR_animation_pointer
        if path is not None:
            path_ = {}
            path_['length'] = 1
            path_['path'] = "/materials/XXX/extensions/KHR_materials_transmission/transmissionFactor"
            export_settings['current_paths'][path] = path_

    if not transmission_enabled:
        return None, None

    # Pack transmission channel (R).
    if has_transmission_texture:
        transmission_slots = (transmission_socket,)

    use_actives_uvmaps = []

    if len(transmission_slots) > 0:
        combined_texture, use_active_uvmap, _ = gltf2_blender_gather_texture_info.gather_texture_info(
            transmission_socket,
            transmission_slots,
            export_settings,
        )
        if has_transmission_texture:
            transmission_extension['transmissionTexture'] = combined_texture
        if use_active_uvmap:
            use_actives_uvmaps.append("transmissionTexture")

    return Extension('KHR_materials_transmission', transmission_extension, False), use_actives_uvmaps
