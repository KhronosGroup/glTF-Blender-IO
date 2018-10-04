# Copyright (c) 2018 The Khronos Group Inc.
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


from io_scene_gltf2.blender.exp.gltf2_blender_gather import cached
from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.blender.exp import gltf2_blender_search_node_tree


@cached
def gather_material(blender_material, export_settings):
    """
    Gather the material used by the blender primitive
    :param blender_material: the blender material used in the glTF primitive
    :param export_settings:
    :return: a glTF material
    """
    if not __filter_material(blender_material, export_settings):
        return None

    material = gltf2_io.Material(
        alpha_cutoff=__gather_alpha_cutoff(blender_material, export_settings),
        alpha_mode=__gather_alpha_mode(blender_material, export_settings),
        double_sided=__gather_double_sided(blender_material, export_settings),
        emissive_factor=__gather_emmissive_factor(blender_material, export_settings),
        emissive_texture=__gather_emissive_texture(blender_material, export_settings),
        extensions=__gather_extensions(blender_material, export_settings),
        extras=__gather_extras(blender_material, export_settings),
        name=__gather_name(blender_material, export_settings),
        normal_texture=__gather_normal_texture(blender_material, export_settings),
        occlusion_texture=__gather_occlusion_texture(blender_material, export_settings),
        pbr_metallic_roughness=__gather_pbr_metallic_roughness(blender_material, export_settings)
    )

    return material
    # material = blender_primitive['material']
    #
    #     if get_material_requires_texcoords(glTF, material) and not export_settings['gltf_texcoords']:
    #         material = -1
    #
    #     if get_material_requires_normals(glTF, material) and not export_settings['gltf_normals']:
    #         material = -1
    #
    #     # Meshes/primitives without material are allowed.
    #     if material >= 0:
    #         primitive.material = material
    #     else:
    #         print_console('WARNING', 'Material ' + internal_primitive[
    #             'material'] + ' not found. Please assign glTF 2.0 material or enable Blinn-Phong material in export.')


def __filter_material(blender_material, export_settings):
    # if not blender_material.use_nodes:
    #     return False
    # if not blender_material.node_tree:
    #     return False
    return True


def __gather_alpha_cutoff(blender_material, export_settings):
    return None


def __gather_alpha_mode(blender_material, export_settings):
    return None


def __gather_double_sided(blender_material, export_settings):
    return None


def __gather_emmissive_factor(blender_material, export_settings):
    return None


def __gather_emissive_texture(blender_material, export_settings):
    if blender_material.node_tree and blender_material.use_nodes:
        emissive_link = [link for link in blender_material.node_tree.links if link.to_socket.name == "Emissive"]
        if not emissive_link:
            return None
        emissive_socket = emissive_link[0].to_socket
        # search the node tree for textures, beginning from the 'emissive' socket in the material
        emissive_tex_nodes = gltf2_blender_search_node_tree.gather_from_socket(
            emissive_socket,
            gltf2_blender_search_node_tree.FilterByType(bpy.types.ShaderNodeTexImage))

    else:
        # TODO: gather texture from tex node
        pass
    return None


def __gather_extensions(blender_material, export_settings):
    # TODO specular glossiness extension
    return None


def __gather_extras(blender_material, export_setttings):
    return None


def __gather_name(blender_material, export_settings):
    return None


def __gather_normal_texture(blender_material, export_settings):
    return None


def __gather_occlusion_texture(blender_material, export_settings):
    return None


def __gather_pbr_metallic_roughness(blender_material, export_settings):
    # TODO
    return None

