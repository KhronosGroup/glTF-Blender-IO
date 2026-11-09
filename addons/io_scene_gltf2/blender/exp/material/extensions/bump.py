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


# EXT_materials_bump: d = h * bumpFactor, in metres, in heightSpace ("object" or "world").
#
# Two Blender setups map to it:
# - Material Output Displacement <- Displacement node (bump only): heightSpace from the node space, bumpFactor = Scale.
# - Principled BSDF Normal <- Bump node: Blender evaluates the Bump node against world space positions,
#   so heightSpace is "world", bumpFactor = Distance (exact when Strength is 1).
def export_bump(bmat, export_settings):
    export_settings['current_texture_transform'] = {}
    log = export_settings['log']

    found = __find_displacement(bmat, export_settings)
    bump = __find_bump(bmat, export_settings)
    if found is not None and bump is not None:
        log.warning("Material '{}' uses both a Displacement node and a Bump node; "
                    "only the Displacement node is exported as EXT_materials_bump".format(bmat.name))
    if found is None:
        found = bump
    if found is None:
        return None, {}, {}

    height_socket, bump_factor, height_space = found
    if bump_factor is None:
        return None, {}, {}

    __check_height_image(height_socket, export_settings)

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

    # ponytail: no KHR_animation_pointer paths for bumpFactor / bumpTexture transform yet
    export_settings['current_texture_transform'] = {}

    return Extension('EXT_materials_bump', bump_extension, False), \
        {'bumpTexture': uvmap_info}, \
        {'bumpTexture': udim_info} if len(udim_info.keys()) > 0 else {}


def __find_displacement(bmat, export_settings):
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

    log = export_settings['log']
    if bmat.material.displacement_method != 'BUMP':
        log.warning("Material '{}' uses true displacement; only its bump (normal perturbation) is exported "
                    "as EXT_materials_bump".format(bmat.name))

    scale = node.inputs['Scale']
    if scale.is_linked:
        log.warning("Displacement node Scale is linked; EXT_materials_bump is not exported for material '{}'".format(
            bmat.name))
        return height_socket, None, None

    return height_socket, __check_factor(scale.default_value, bmat, export_settings), \
        'world' if node.space == 'WORLD' else 'object'


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

    log = export_settings['log']
    strength, distance = node.inputs['Strength'], node.inputs['Distance']
    if strength.is_linked or distance.is_linked:
        log.warning("Bump node Strength or Distance is linked; EXT_materials_bump is not exported for "
                    "material '{}'".format(bmat.name))
        return height_socket, None, None

    factor = distance.default_value
    if strength.default_value != 1.0:
        # Blender Bump Strength blends normals: normalize(s * N_bump + (1 - s) * N).
        # For small slopes this is close to scaling the height by s.
        factor *= strength.default_value
        log.warning("Bump node Strength {} is not 1.0; exported as bumpFactor = Strength * Distance, "
                    "which is an approximation".format(strength.default_value))
    if node.invert:
        factor = -factor

    return height_socket, __check_factor(factor, bmat, export_settings), 'world'


def __has_height_texture(node, height_socket, export_settings):
    if get_texture_node_from_socket(height_socket, export_settings) is not None:
        return True
    if height_socket.socket.is_linked:
        export_settings['log'].warning(
            "{} node Height is not driven by an image texture; EXT_materials_bump is not exported".format(node.name))
    return False


def __check_factor(factor, bmat, export_settings):
    # A negative factor (Bump invert, negative Distance or Scale) means the height is inverted.
    # bumpFactor must be >= 0, so it can't be represented.
    if factor < 0.0:
        export_settings['log'].warning(
            "Material '{}' has an inverted bump (Invert, or negative Distance/Scale), which EXT_materials_bump "
            "can't represent (bumpFactor must be >= 0); bump is not exported".format(bmat.name))
        return None
    if factor == 0.0:
        return None
    return factor


def __check_height_image(height_socket, export_settings):
    result = get_texture_node_from_socket(height_socket, export_settings)
    image = result.shader_node.image
    log = export_settings['log']
    if not image.colorspace_settings.is_data and image.colorspace_settings.name != 'Non-Color':
        log.warning("Height image '{}' uses color space '{}'; EXT_materials_bump reads it as linear data, "
                    "set it to Non-Color".format(image.name, image.colorspace_settings.name))
    via_channel = any(isinstance(link.from_node, bpy.types.ShaderNodeSeparateColor)
                      or link.from_socket.identifier == 'Alpha' for link in result.path)
    # ponytail: depth >= 24 is a cheap "this image has RGB channels" check, no pixel scan
    if not via_channel and image.depth >= 24:
        log.warning("Height image '{}' is plugged in through its Color output: Blender uses its luminance, "
                    "the red channel is exported".format(image.name))
