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

import bpy
from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached
from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.blender.exp import gltf2_blender_gather_texture

@cached
def gather_texture_info(blender_shader_node, export_settings):
    if not __filter_texture_info(blender_shader_node, export_settings):
        return None

    texture_info = gltf2_io.TextureInfo(
        extensions=__gather_extensions(blender_shader_node, export_settings),
        extras=__gather_extras(blender_shader_node, export_settings),
        index=__gather_index(blender_shader_node, export_settings),
        tex_coord=__gather_tex_coord(blender_shader_node, export_settings)
    )

    return texture_info


def __filter_texture_info(blender_shader_node, export_settings):
    if not isinstance(blender_shader_node, bpy.types.ShaderNodeTexImage):
        return False
    return True


def __gather_extensions(blender_shader_node, export_settings):
    return None


def __gather_extras(blender_shader_node, export_settings):
    return None


def __gather_index(blender_shader_node, export_settings):
    # We just put the actual shader into the 'index' member
    return gltf2_blender_gather_texture.gather_texture(blender_shader_node, export_settings)


def __gather_tex_coord(blender_shader_node, export_settings):
    if len(blender_shader_node.inputs['Vector'].links) == 0:
        return 0

    input_node = blender_shader_node.inputs['Vector'].links[0].from_node

    if isinstance(input_node, bpy.types.ShaderNodeMapping):

        if len(input_node.inputs['Vector'].links) == 0:
            return 0

        input_node = input_node.inputs['Vector'].links[0].from_node

    if not isinstance(input_node, bpy.types.ShaderNodeUVMap):
        return 0

    if input_node.uv_map == '':
        return 0

    # Try to gather map index.
    for blender_mesh in bpy.data.meshes:
        texCoordIndex = blender_mesh.uv_textures.find(input_node.uv_map)
        if texCoordIndex >= 0:
            return texCoordIndex

    return 0
