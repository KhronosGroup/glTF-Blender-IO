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
    return None, None # Deactivate for now #TODOExt
    sheen_extension = {}
    sheen_ext_enabled = False

    sheen_socket = gltf2_blender_get.get_socket(blender_material, 'Sheen')
    sheen_tint_socket = gltf2_blender_get.get_socket(blender_material, 'Sheen Tint')
    base_color_socket = gltf2_blender_get.get_socket(blender_material, 'Base Color')

    # TODOExt replace by __has_image_node_from_socket calls
    sheen_not_linked = isinstance(sheen_socket, bpy.types.NodeSocket) and not sheen_socket.is_linked
    sheen_tint_not_linked = isinstance(sheen_tint_socket, bpy.types.NodeSocket) and not sheen_tint_socket.is_linked
    base_color_not_linked = isinstance(base_color_socket, bpy.types.NodeSocket) and not base_color_socket.is_linked

    sheen = sheen_socket.default_value if sheen_not_linked else None
    sheen_tint = sheen_tint_socket.default_value if sheen_tint_not_linked else None

    if sheen == 0.0:
        return None, None

    no_texture = sheen_not_linked and sheen_tint_not_linked and base_color_not_linked

    use_actives_uvmaps = []

    if no_texture:
        #TODOExt how to approximate?
        # This is not the definitive mapping, only a placeholder
        sheen_ext_enabled = True
        sheen_extension['sheenColorFactor'] = [sheen * sheen_tint] * 3
    else:
        # There will be a texture, with a complex calculation (no direct channel mapping)
        sockets = (sheen_socket, sheen_tint_socket, base_color_socket)

        # Set primary socket having a texture
        primary_socket = sheen_socket
        if sheen_not_linked:
            primary_socket = sheen_tint_socket
            if sheen_tint_not_linked:
                primary_socket = base_color_socket
        
        #TODOExt if both output textures are needed, using same socket as input:
         # * use primary socket to differenciate?
            
        sheenColorTexture, use_active_uvmap, _ = gltf2_blender_gather_texture_info.gather_texture_info(
            primary_socket, 
            sockets, 
            export_settings,
            filter_type='ANY')
        if sheenColorTexture is None:
            return None, None
        if use_active_uvmap:
            use_actives_uvmaps.append("sheenColorTexture")

        sheen_ext_enabled = True
        sheen_extension['sheenColorTexture'] = sheenColorTexture

    sheen_extension = Extension('KHR_materials_sheen', sheen_extension, False) if sheen_ext_enabled else None
    return sheen_extension, use_actives_uvmaps