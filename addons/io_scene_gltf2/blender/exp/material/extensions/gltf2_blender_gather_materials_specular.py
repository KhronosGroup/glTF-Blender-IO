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
from ...material.gltf2_blender_gather_texture_info import gather_texture_info

def export_specular(blender_material, export_settings):
    specular_extension = {}

    specular_socket = gltf2_blender_get.get_socket(blender_material, 'Specular IOR Level')
    speculartint_socket = gltf2_blender_get.get_socket(blender_material, 'Specular Tint')

    if specular_socket is None or speculartint_socket is None:
        return None, {}

    uvmap_infos = {}

    specular_non_linked = isinstance(specular_socket, bpy.types.NodeSocket) and not specular_socket.is_linked
    specularcolor_non_linked = isinstance(speculartint_socket, bpy.types.NodeSocket) and not speculartint_socket.is_linked

    if specular_non_linked is True:
        fac = specular_socket.default_value
        if fac != 1.0:
            specular_extension['specularFactor'] = fac
        if fac == 0.0:
            return None, {}
    else:
        # Factor
        fac, path = gltf2_blender_get.get_factor_from_socket(specular_socket, kind='VALUE')
        if fac is not None and fac != 1.0:
            specular_extension['specularFactor'] = fac

        if fac == 0.0:
            return None, {}

        # Texture
        if gltf2_blender_get.has_image_node_from_socket(specular_socket):
            original_specular_texture, uvmap_info, _ = gather_texture_info(
                specular_socket,
                (specular_socket,),
                (),
                export_settings,
            )
            specular_extension['specularTexture'] = original_specular_texture
            uvmap_infos.update({'specularTexture': uvmap_info})

    if specularcolor_non_linked is True:
        color = speculartint_socket.default_value[:3]
        if color != (1.0, 1.0, 1.0):
            specular_extension['specularColorFactor'] = color
    else:
        # Factor
        fac, path = gltf2_blender_get.get_factor_from_socket(speculartint_socket, kind='RGB')
        if fac is not None and fac != (1.0, 1.0, 1.0):
            specular_extension['specularColorFactor'] = fac

        # Texture
        if gltf2_blender_get.has_image_node_from_socket(speculartint_socket):
            original_specularcolor_texture, uvmap_info, _ = gather_texture_info(
                speculartint_socket,
                (speculartint_socket,),
                (),
                export_settings,
            )
            specular_extension['specularColorTexture'] = original_specularcolor_texture
            uvmap_infos.update({'specularColorTexture': uvmap_info})

    return Extension('KHR_materials_specular', specular_extension, False), uvmap_infos
