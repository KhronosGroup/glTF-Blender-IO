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
from ....io.com import gltf2_io
from ....io.exp.gltf2_io_user_extensions import export_user_extensions
from ...exp import gltf2_blender_get
from ..gltf2_blender_gather_cache import cached
from ..gltf2_blender_get import image_tex_is_valid_from_socket
from .gltf2_blender_search_node_tree import get_vertex_color_info
from .gltf2_blender_gather_texture_info import gather_texture_info

@cached
def gather_material_pbr_metallic_roughness(blender_material, orm_texture, export_settings):
    if not __filter_pbr_material(blender_material, export_settings):
        return None, {}

    uvmap_infos = {}

    base_color_texture, uvmap_info, vc_info, _ = __gather_base_color_texture(blender_material, export_settings)
    uvmap_infos.update(uvmap_info)
    metallic_roughness_texture, uvmap_info, _ = __gather_metallic_roughness_texture(blender_material, orm_texture, export_settings)
    uvmap_infos.update(uvmap_info)

    material = gltf2_io.MaterialPBRMetallicRoughness(
        base_color_factor=__gather_base_color_factor(blender_material, export_settings),
        base_color_texture=base_color_texture,
        extensions=__gather_extensions(blender_material, export_settings),
        extras=__gather_extras(blender_material, export_settings),
        metallic_factor=__gather_metallic_factor(blender_material, export_settings),
        metallic_roughness_texture=metallic_roughness_texture,
        roughness_factor=__gather_roughness_factor(blender_material, export_settings)
    )

    export_user_extensions('gather_material_pbr_metallic_roughness_hook', export_settings, material, blender_material, orm_texture)

    return material, uvmap_infos, vc_info


def __filter_pbr_material(blender_material, export_settings):
    return True


def __gather_base_color_factor(blender_material, export_settings):
    if not blender_material.use_nodes:
        return [*blender_material.diffuse_color[:3], 1.0]

    rgb, alpha = None, None

    path_alpha = None
    path = None
    alpha_socket = gltf2_blender_get.get_socket(blender_material.node_tree, blender_material.use_nodes, "Alpha")
    if isinstance(alpha_socket, bpy.types.NodeSocket):
        if export_settings['gltf_image_format'] != "NONE":
            alpha, path_alpha = gltf2_blender_get.get_factor_from_socket(alpha_socket, kind='VALUE')
        else:
            alpha, path_alpha = gltf2_blender_get.get_const_from_default_value_socket(alpha_socket, kind='VALUE')

    base_color_socket = gltf2_blender_get.get_socket(blender_material.node_tree, blender_material.use_nodes,"Base Color")
    if base_color_socket is None:
        base_color_socket = gltf2_blender_get.get_socket(blender_material.node_tree, blender_material.use_nodes,"BaseColor")
    if base_color_socket is None:
        base_color_socket = gltf2_blender_get.get_socket_old(blender_material, "BaseColorFactor")
    if isinstance(base_color_socket, bpy.types.NodeSocket):
        if export_settings['gltf_image_format'] != "NONE":
            rgb, path = gltf2_blender_get.get_factor_from_socket(base_color_socket, kind='RGB')
        else:
            rgb, path = gltf2_blender_get.get_const_from_default_value_socket(base_color_socket, kind='RGB')

    # Storing path for KHR_animation_pointer
    if path is not None:
        path_ = {}
        path_['length'] = 3
        path_['path'] = "/materials/XXX/pbrMetallicRoughness/baseColorFactor"
        path_['additional_path'] = path_alpha
        export_settings['current_paths'][path] = path_

    # Storing path for KHR_animation_pointer
    if path_alpha is not None:
        path_ = {}
        path_['length'] = 1
        path_['path'] = "/materials/XXX/pbrMetallicRoughness/baseColorFactor"
        path_['additional_path'] = path
        export_settings['current_paths'][path_alpha] = path_

    if rgb is None: rgb = [1.0, 1.0, 1.0]
    if alpha is None: alpha = 1.0

    # Need to clamp between 0.0 and 1.0: Blender color can be outside this range
    rgb = [max(min(c, 1.0), 0.0) for c in rgb]

    rgba = [*rgb, alpha]

    if rgba == [1, 1, 1, 1]: return None
    return rgba


def __gather_base_color_texture(blender_material, export_settings):
    base_color_socket = gltf2_blender_get.get_socket(blender_material.node_tree, blender_material.use_nodes, "Base Color")
    if base_color_socket is None:
        base_color_socket = gltf2_blender_get.get_socket(blender_material.node_tree, blender_material.use_nodes, "BaseColor")
    if base_color_socket is None:
        base_color_socket = gltf2_blender_get.get_socket_old(blender_material, "BaseColor")

    alpha_socket = gltf2_blender_get.get_socket(blender_material.node_tree, blender_material.use_nodes, "Alpha")

    # keep sockets that have some texture : color and/or alpha
    inputs = tuple(
        socket for socket in [base_color_socket, alpha_socket]
        if socket is not None and image_tex_is_valid_from_socket(socket)
    )
    if not inputs:
        return None, {}, {"uv_info": {}, "vc_info": {}}, None

    tex, uvmap_info, factor = gather_texture_info(inputs[0], inputs, (), export_settings)
    vc_info = get_vertex_color_info(inputs[0], inputs, export_settings)

    if len(export_settings['current_texture_transform']) != 0:
        for k in export_settings['current_texture_transform'].keys():
            path_ = {}
            path_['length'] = export_settings['current_texture_transform'][k]['length']
            path_['path'] = export_settings['current_texture_transform'][k]['path'].replace("YYY", "pbrMetallicRoughness/baseColorTexture/extensions")
            export_settings['current_paths'][k] = path_

    export_settings['current_texture_transform'] = {}

    return tex, {'baseColorTexture': uvmap_info}, vc_info, factor


def __gather_extensions(blender_material, export_settings):
    return None


def __gather_extras(blender_material, export_settings):
    return None


def __gather_metallic_factor(blender_material, export_settings):
    if not blender_material.use_nodes:
        return blender_material.metallic

    metallic_socket = gltf2_blender_get.get_socket(blender_material.node_tree, blender_material.use_nodes, "Metallic")
    if metallic_socket is None:
        metallic_socket = gltf2_blender_get.get_socket_old(blender_material, "MetallicFactor")
    if isinstance(metallic_socket, bpy.types.NodeSocket):
        fac, path = gltf2_blender_get.get_factor_from_socket(metallic_socket, kind='VALUE')

        # Storing path for KHR_animation_pointer
        if path is not None:
            path_ = {}
            path_['length'] = 1
            path_['path'] = "/materials/XXX/pbrMetallicRoughness/metallicFactor"
            export_settings['current_paths'][path] = path_

        return fac if fac != 1 else None

    return None


def __gather_metallic_roughness_texture(blender_material, orm_texture, export_settings):
    metallic_socket = gltf2_blender_get.get_socket(blender_material.node_tree, blender_material.use_nodes, "Metallic")
    roughness_socket = gltf2_blender_get.get_socket(blender_material.node_tree, blender_material.use_nodes, "Roughness")

    hasMetal = metallic_socket is not None and image_tex_is_valid_from_socket(metallic_socket)
    hasRough = roughness_socket is not None and image_tex_is_valid_from_socket(roughness_socket)

    default_sockets = ()
    if not hasMetal and not hasRough:
        metallic_roughness = gltf2_blender_get.get_socket_old(blender_material, "MetallicRoughness")
        if metallic_roughness is None or not image_tex_is_valid_from_socket(metallic_roughness):
            return None, {}, None
        texture_input = (metallic_roughness,)
    elif not hasMetal:
        texture_input = (roughness_socket,)
        default_sockets = (metallic_socket,)
    elif not hasRough:
        texture_input = (metallic_socket,)
        default_sockets = (roughness_socket,)
    else:
        texture_input = (metallic_socket, roughness_socket)
        default_sockets = ()

    tex, uvmap_info, factor = gather_texture_info(
        texture_input[0],
        orm_texture or texture_input,
        default_sockets,
        export_settings,
    )

    return tex, {'metallicRoughnessTexture': uvmap_info}, factor

def __gather_roughness_factor(blender_material, export_settings):
    if not blender_material.use_nodes:
        return blender_material.roughness

    roughness_socket = gltf2_blender_get.get_socket(blender_material.node_tree, blender_material.use_nodes, "Roughness")
    if roughness_socket is None:
        roughness_socket = gltf2_blender_get.get_socket_old(blender_material, "RoughnessFactor")
    if isinstance(roughness_socket, bpy.types.NodeSocket):
        fac, path = gltf2_blender_get.get_factor_from_socket(roughness_socket, kind='VALUE')

        # Storing path for KHR_animation_pointer
        if path is not None:
            path_ = {}
            path_['length'] = 1
            path_['path'] = "/materials/XXX/pbrMetallicRoughness/roughnessFactor"
            export_settings['current_paths'][path] = path_

        return fac if fac != 1 else None
    return None

def get_default_pbr_for_emissive_node():
    return gltf2_io.MaterialPBRMetallicRoughness(
        base_color_factor=[0.0,0.0,0.0,1.0],
        base_color_texture=None,
        extensions=None,
        extras=None,
        metallic_factor=None,
        metallic_roughness_texture=None,
        roughness_factor=None
    )


