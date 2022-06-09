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
    base_color = base_color_socket.default_value[0:3] if base_color_not_linked else None

    if sheen == 0.0:
        return None, []

    no_texture = sheen_not_linked and sheen_tint_not_linked and base_color_not_linked

    use_actives_uvmaps = []

    if no_texture:
        # See: https://developer.blender.org/diffusion/B/browse/master/source/blender/gpu/shaders/material/gpu_shader_material_principled.glsl;7f578998235d94d193ebe4699af308f932b6af6c$2-6
        sheen_ext_enabled = True
        # TODOExt Approximation discussion in progress
        base_color_tint = __tint_from_color(base_color)
        
        sheenColorFactor = [
            max(0, min(1, sheen * ((1 - sheen_tint) + (sheen_tint * base_color_tint[0])))),
            max(0, min(1, sheen * ((1 - sheen_tint) + (sheen_tint * base_color_tint[1])))),
            max(0, min(1, sheen * ((1 - sheen_tint) + (sheen_tint * base_color_tint[2])))),
        ]
        sheen_extension['sheenColorFactor'] = sheenColorFactor

        # TODOExt: Determine correct sheen roughness value.
        sheen_extension['sheenRoughnessFactor'] = 0.25

    else:
        # There will be a texture, with a complex calculation (no direct channel mapping)
        sockets = (sheen_socket, sheen_tint_socket, base_color_socket)

        # Set primary socket having a texture
        primary_socket = sheen_socket
        if sheen_not_linked:
            primary_socket = sheen_tint_socket
            if sheen_tint_not_linked:
                primary_socket = base_color_socket
        
        # If one day both output textures are needed (color and roughness),
        # We will need to use primary socket to differentiate both texture in numpy calculation
        
        # Currently, only color is used
            
        sheenColorTexture, use_active_uvmap, sheenColorFactor = gltf2_blender_gather_texture_info.gather_texture_info(
            primary_socket, 
            sockets, 
            export_settings,
            filter_type='ANY')
        if sheenColorTexture is None:
            return None, []
        if use_active_uvmap:
            use_actives_uvmaps.append("sheenColorTexture")

        sheen_ext_enabled = True
        sheen_extension['sheenColorTexture'] = sheenColorTexture
        sheen_extension['sheenRoughnessFactor'] = 0.25 # TODOExt: Determine correct sheen roughness value.

        if sheenColorFactor is not None:
            sheen_extension['sheenColorFactor'] = sheenColorFactor

    sheen_extension = Extension('KHR_materials_sheen', sheen_extension, False) if sheen_ext_enabled else None
    return sheen_extension, use_actives_uvmaps

def __tint_from_color(color):
    # Luminance approximation.
    luminance = color[0] * 0.3 + color[1] * 0.6 + color[2] * 0.1

    if luminance > 0:
        # Normalize to isolate hue and saturation.
        return [
            color[0] / luminance,
            color[1] / luminance,
            color[2] / luminance
        ]

    return [1, 1, 1]