# Copyright 2018-2026 The glTF-Blender-IO authors.
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
from ...material import texture_info as gltf2_blender_gather_texture_info
from ..search_node_tree import \
    NodeSocket, \
    NodeTreeSearcher, \
    FilterByType, \
    get_texture_node_from_socket


# EXT_materials_bump: d = h * bumpFactor, in meters, in heightSpace ("object" or "world").
#
# Two Blender setups map to it:
# - Material Output Displacement <- Displacement node (bump only): heightSpace from the node space, bumpFactor = Scale.
# - Principled BSDF Normal <- Bump node: Blender evaluates the Bump node against world space positions,
#   so heightSpace is "world", bumpFactor = Distance (exact when Strength is 1).
# If both are used, the Displacement node is exported.
def export_bump(bmat, export_settings):
    export_settings['current_texture_transform'] = {}

    found = __find_displacement(bmat, export_settings)
    if found is None:
        found = __find_bump(bmat, export_settings)
    if found is None:
        return None, {}, {}

    height_socket, bump_factor, height_space, factor_path = found
    if bump_factor is None or bump_factor == 0.0:
        return None, {}, {}

    bump_texture, uvmap_info, udim_info, _ = gltf2_blender_gather_texture_info.gather_texture_info(
        height_socket,
        (height_socket,),
        export_settings,
        kind='DATA',
    )
    if bump_texture is None and len(udim_info) == 0:
        return None, {}, {}

    bump_extension = {'heightSpace': height_space}
    if bump_factor != 1.0:
        bump_extension['bumpFactor'] = bump_factor
    if bump_texture is not None:
        bump_extension['bumpTexture'] = bump_texture

    # Storing path for KHR_animation_pointer
    if factor_path is not None:
        path_ = {}
        path_['length'] = 1
        path_['path'] = "/materials/XXX/extensions/EXT_materials_bump/bumpFactor"
        export_settings['current_paths'][factor_path] = path_

    if len(export_settings['current_texture_transform']) != 0:
        for k in export_settings['current_texture_transform'].keys():
            path_ = {}
            path_['length'] = export_settings['current_texture_transform'][k]['length']
            path_['path'] = export_settings['current_texture_transform'][k]['path'].replace(
                "YYY", "extensions/EXT_materials_bump/bumpTexture/extensions")
            path_['vector_type'] = export_settings['current_texture_transform'][k]['vector_type']
            if k in export_settings['current_paths']:
                if 'additional' not in export_settings['current_paths'][k]:
                    export_settings['current_paths'][k]['additional'] = []
                if path_['path'] != export_settings['current_paths'][k]['path']:
                    export_settings['current_paths'][k]['additional'].append(path_['path'])
            else:
                export_settings['current_paths'][k] = path_

    export_settings['current_texture_transform'] = {}

    return Extension('EXT_materials_bump', bump_extension, False), \
        {'bumpTexture': uvmap_info}, \
        {'bumpTexture': udim_info} if len(udim_info.keys()) > 0 else {}


def __find_displacement(bmat, export_settings):
    # With 'DISPLACEMENT' method, Blender only moves the vertices: there is no bump to export
    # TODO: true displacement can't be represented in glTF. With 'BOTH', only the bump part is exported
    if bmat.material.displacement_method == 'DISPLACEMENT':
        return None

    outputs = [n for n in bmat.get_all_nodes_of_type(bpy.types.ShaderNodeOutputMaterial) if n[0].is_active_output]
    if not outputs:
        return None
    output, group_path = outputs[0]
    result = NodeTreeSearcher.from_socket(
        NodeSocket(output.inputs['Displacement'], group_path),
        FilterByType(bpy.types.ShaderNodeDisplacement),
        export_settings)
    if not result:
        return None
    node = result[0].shader_node
    height_socket = NodeSocket(node.inputs['Height'], result[0].group_path)
    if not __has_height_texture(node, height_socket, export_settings):
        return None

    scale = node.inputs['Scale']
    if scale.is_linked:
        export_settings['log'].warning(
            "Displacement node Scale is linked; EXT_materials_bump is not exported for material '{}'".format(
                bmat.name))
        return height_socket, None, None, None

    # Midlevel only adds a constant to the height, so it doesn't change the bump
    return height_socket, scale.default_value, 'world' if node.space == 'WORLD' else 'object', \
        "node_tree." + scale.path_from_id() + ".default_value"


def __find_bump(bmat, export_settings):
    normal_socket = bmat.get_socket("Normal")
    if normal_socket.socket is None:
        return None
    result = NodeTreeSearcher.from_socket(normal_socket, FilterByType(bpy.types.ShaderNodeBump), export_settings)
    if not result:
        return None
    node = result[0].shader_node
    height_socket = NodeSocket(node.inputs['Height'], result[0].group_path)
    if not __has_height_texture(node, height_socket, export_settings):
        return None

    strength, distance = node.inputs['Strength'], node.inputs['Distance']
    if strength.is_linked or distance.is_linked:
        export_settings['log'].warning(
            "Bump node Strength or Distance is linked; EXT_materials_bump is not exported for material '{}'".format(
                bmat.name))
        return height_socket, None, None, None

    # Blender Bump Strength blends normals: normalize(s * N_bump + (1 - s) * N).
    # For small slopes this is close to scaling the height by s, so bumpFactor = Strength * Distance.
    # Invert negates the height.
    factor = distance.default_value * strength.default_value
    if node.invert:
        factor = -factor

    # Distance animation can only be exported as is when it is the bumpFactor
    path = None
    if strength.default_value == 1.0 and not node.invert:
        path = "node_tree." + distance.path_from_id() + ".default_value"

    return height_socket, factor, 'world', path


def __has_height_texture(node, height_socket, export_settings):
    if get_texture_node_from_socket(height_socket, export_settings) is not None:
        return True
    if height_socket.socket.is_linked:
        export_settings['log'].warning(
            "{} node Height is not driven by an image texture; EXT_materials_bump is not exported".format(node.name))
    return False
