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

from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.blender.exp import gltf2_blender_gather_texture_info, gltf2_blender_search_node_tree
from io_scene_gltf2.blender.exp import gltf2_blender_get
from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached
from io_scene_gltf2.io.exp.gltf2_io_user_extensions import export_user_extensions
from io_scene_gltf2.blender.com.gltf2_blender_extras import generate_extras


@cached
def gather_material_pbrSpecularGlossiness(blender_material, export_settings):
    required_nodes = ["Diffuse BSDF", "Glossy BSDF"]
    is_enabled = len([n for n in blender_material.node_tree.nodes if n.name in required_nodes]) == 2
    if not is_enabled:
        return None
        
    extras = __gather_extras(blender_material, export_settings)
    if extras and "KHR_materials_pbrSpecularGlossiness" in extras:
        extras = extras["KHR_materials_pbrSpecularGlossiness"]
    else:
        extras = None

    diffuse_texture, use_active_uvmap_diffuse_texture = __gather_diffuse_color_texture(blender_material, export_settings)
    specular_glossiness_texture, use_active_uvmap_specular_glossiness_texture = __gather_specular_glossiness_texture(blender_material, export_settings)
    extension = { 'diffuseFactor': __gather_diffuse_color_factor(blender_material, export_settings),
        'diffuseTexture': diffuse_texture,
        'extensions': __gather_extensions(blender_material, export_settings),
        'extras': extras,
        'specularFactor': __gather_specular_color_factor(blender_material, export_settings),
        'specularGlossinessTexture': specular_glossiness_texture,
        'glossinessFactor': __gather_glossiness_factor(blender_material, export_settings),
    }

    # merge all use_active_uvmap infos
    uvmap_actives = []
    if use_active_uvmap_diffuse_texture is True:
        uvmap_actives.append("diffuseTexture")
    if use_active_uvmap_specular_glossiness_texture is True:
        uvmap_actives.append("specularGlossinessTexture")

    return extension, uvmap_actives


def __gather_diffuse_color_factor(blender_material, export_settings):
    if not blender_material.use_nodes:
        return [*blender_material.diffuse_color[:3], 1.0]

    rgb = [1.0, 1.0, 1.0]

    diffuse_color_socket = gltf2_blender_get.get_socket_from_node(blender_material, "Diffuse BSDF", "Color")
    if isinstance(diffuse_color_socket, bpy.types.NodeSocketColor):
        rgb = gltf2_blender_get.get_factor_from_socket(diffuse_color_socket, kind='RGB')

    alpha = 1.0

    alpha_socket = gltf2_blender_get.get_socket_from_node(blender_material, "Transparent BSDF", "Fac")
    if isinstance(alpha_socket, bpy.types.NodeSocket):
        alpha = gltf2_blender_get.get_factor_from_socket(alpha_socket, kind='VALUE')

    if rgb is None :
        rgb = [1.0, 1.0, 1.0]

    if alpha is None :
        alpha = 1.0

    rgba = [*rgb[:3], alpha]

    if rgba == [1.0, 1.0, 1.0, 1.0]: return None

    return rgba


def __gather_diffuse_color_texture(blender_material, export_settings):
    diffuse_color_socket = gltf2_blender_get.get_socket_from_node(blender_material, "Diffuse BSDF", "Color")

    alpha_socket = gltf2_blender_get.get_socket_from_node(blender_material, "Transparent BSDF", "Fac")

    # keep sockets that have some texture : color and/or alpha
    inputs = tuple(
        socket for socket in [diffuse_color_socket, alpha_socket]
        if socket is not None and __has_image_node_from_socket(socket)
    )
    
    if not inputs:
        return None, None

    return gltf2_blender_gather_texture_info.gather_texture_info(inputs[0], inputs, export_settings)


def __gather_extensions(blender_material, export_settings):
    return None


def __gather_extras(blender_material, export_settings):
    if blender_material.use_nodes and export_settings['gltf_extras']:
        output_node = blender_material.node_tree.nodes["Material Output"]
        return generate_extras(output_node)
    return None

def __gather_specular_color_factor(blender_material, export_settings):
    if not blender_material.use_nodes:
        specular_intensity = blender_material.specular_intensity
        return [specular_intensity, specular_intensity, specular_intensity, 1.0]

    rgba = None

    specular_color_socket = gltf2_blender_get.get_socket_from_node(blender_material, "Glossy BSDF", "Color")
    if isinstance(specular_color_socket, bpy.types.NodeSocketColor):
        rgba = gltf2_blender_get.get_factor_from_socket(specular_color_socket, kind='RGB')

    if rgba is None: rgba = [1.0, 1.0, 1.0, 1.0]

    if rgba == [1, 1, 1, 1]: return None
    return rgba


def __gather_specular_glossiness_texture(blender_material, export_settings):
    specular_glossiness_socket = gltf2_blender_get.get_socket_from_node(blender_material, "Glossy BSDF", "Color")

    # keep socket if it has some texture : color
    input = specular_glossiness_socket if specular_glossiness_socket is not None and __has_image_node_from_socket(specular_glossiness_socket) else None
    if not input:
        return None, None

    inputs = tuple([input])
    if not inputs:
        return None, None

    return gltf2_blender_gather_texture_info.gather_texture_info(inputs[0], inputs, export_settings)

def __gather_glossiness_factor(blender_material, export_settings):
    if not blender_material.use_nodes:
        roughness = blender_material.roughness
        return roughness

    value = None

    glossiness_color_socket = gltf2_blender_get.get_socket_from_node(blender_material, "Glossy BSDF", "Roughness")
    if isinstance(glossiness_color_socket, bpy.types.NodeSocket):
        value = gltf2_blender_get.get_factor_from_socket(glossiness_color_socket, kind='VALUE')

    if value is None: value = 0.5

    return value

def __has_image_node_from_socket(socket):
    result = gltf2_blender_search_node_tree.from_socket(
        socket,
        gltf2_blender_search_node_tree.FilterByType(bpy.types.ShaderNodeTexImage))
    if not result:
        return False
    return True
