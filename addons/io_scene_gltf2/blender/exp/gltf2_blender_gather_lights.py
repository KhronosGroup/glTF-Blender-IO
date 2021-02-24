# Copyright 2018-2021 The glTF-Blender-IO authors.
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
import math
from typing import Optional, List, Dict, Any

from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached
from ..com.gltf2_blender_extras import generate_extras

from io_scene_gltf2.io.com import gltf2_io_lights_punctual
from io_scene_gltf2.io.com import gltf2_io_debug

from io_scene_gltf2.blender.exp import gltf2_blender_gather_light_spots
from io_scene_gltf2.blender.exp import gltf2_blender_search_node_tree


@cached
def gather_lights_punctual(blender_lamp, export_settings) -> Optional[Dict[str, Any]]:
    if not __filter_lights_punctual(blender_lamp, export_settings):
        return None

    light = gltf2_io_lights_punctual.Light(
        color=__gather_color(blender_lamp, export_settings),
        intensity=__gather_intensity(blender_lamp, export_settings),
        spot=__gather_spot(blender_lamp, export_settings),
        type=__gather_type(blender_lamp, export_settings),
        range=__gather_range(blender_lamp, export_settings),
        name=__gather_name(blender_lamp, export_settings),
        extensions=__gather_extensions(blender_lamp, export_settings),
        extras=__gather_extras(blender_lamp, export_settings)
    )

    return light.to_dict()


def __filter_lights_punctual(blender_lamp, export_settings) -> bool:
    if blender_lamp.type in ["HEMI", "AREA"]:
        gltf2_io_debug.print_console("WARNING", "Unsupported light source {}".format(blender_lamp.type))
        return False

    return True


def __gather_color(blender_lamp, export_settings) -> Optional[List[float]]:
    emission_node = __get_cycles_emission_node(blender_lamp)
    if emission_node is not None:
        return list(emission_node.inputs["Color"].default_value)[:3]

    return list(blender_lamp.color)


def __gather_intensity(blender_lamp, _) -> Optional[float]:
    emission_node = __get_cycles_emission_node(blender_lamp)
    if emission_node is not None:
        if blender_lamp.type != 'SUN':
            # When using cycles, the strength should be influenced by a LightFalloff node
            result = gltf2_blender_search_node_tree.from_socket(
                emission_node.inputs.get("Strength"),
                gltf2_blender_search_node_tree.FilterByType(bpy.types.ShaderNodeLightFalloff)
            )
            if result:
                quadratic_falloff_node = result[0].shader_node
                emission_strength = quadratic_falloff_node.inputs["Strength"].default_value / (math.pi * 4.0)
            else:
                gltf2_io_debug.print_console('WARNING',
                                             'No quadratic light falloff node attached to emission strength property')
                emission_strength = blender_lamp.energy
        else:
            emission_strength = emission_node.inputs["Strength"].default_value
        return emission_strength

    return blender_lamp.energy


def __gather_spot(blender_lamp, export_settings) -> Optional[gltf2_io_lights_punctual.LightSpot]:
    if blender_lamp.type == "SPOT":
        return gltf2_blender_gather_light_spots.gather_light_spot(blender_lamp, export_settings)
    return None


def __gather_type(blender_lamp, _) -> str:
    return {
        "POINT": "point",
        "SUN": "directional",
        "SPOT": "spot"
    }[blender_lamp.type]


def __gather_range(blender_lamp, export_settings) -> Optional[float]:
    if blender_lamp.use_custom_distance:
        return blender_lamp.cutoff_distance
    return None


def __gather_name(blender_lamp, export_settings) -> Optional[str]:
    return blender_lamp.name


def __gather_extensions(blender_lamp, export_settings) -> Optional[dict]:
    return None


def __gather_extras(blender_lamp, export_settings) -> Optional[Any]:
    if export_settings['gltf_extras']:
        return generate_extras(blender_lamp)
    return None


def __get_cycles_emission_node(blender_lamp) -> Optional[bpy.types.ShaderNodeEmission]:
    if blender_lamp.use_nodes and blender_lamp.node_tree:
        for currentNode in blender_lamp.node_tree.nodes:
            is_shadernode_output = isinstance(currentNode, bpy.types.ShaderNodeOutputLight)
            if is_shadernode_output:
                if not currentNode.is_active_output:
                    continue
                result = gltf2_blender_search_node_tree.from_socket(
                    currentNode.inputs.get("Surface"),
                    gltf2_blender_search_node_tree.FilterByType(bpy.types.ShaderNodeEmission)
                )
                if not result:
                    continue
                return result[0].shader_node
    return None
