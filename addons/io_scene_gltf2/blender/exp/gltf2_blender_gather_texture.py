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
from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached
from io_scene_gltf2.blender.exp import gltf2_blender_gather_sampler
from io_scene_gltf2.blender.exp import gltf2_blender_gather_image


@cached
def gather_texture(blender_shader_node, export_settings):
    if not __filter_texture(blender_shader_node, export_settings):
        return None

    return gltf2_io.Texture(
        extensions=__gather_extensions(blender_shader_node, export_settings),
        extras=__gather_extras(blender_shader_node, export_settings),
        name=__gather_name(blender_shader_node, export_settings),
        sampler=__gather_sampler(blender_shader_node, export_settings),
        source=__gather_source(blender_shader_node, export_settings)
    )


def __filter_texture(blender_shader_node , export_settings):
    if not isinstance(blender_shader_node, bpy.types.ShaderNodeTexImage):
        return False
    return True


def __gather_extensions(blender_shader_node , export_settings):
    return None


def __gather_extras(blender_shader_node , export_settings):
    return None


def __gather_name(blender_shader_node , export_settings):
    return None


def __gather_sampler(blender_shader_node , export_settings):
    return gltf2_blender_gather_sampler.gather_sampler(blender_shader_node, export_settings)


def __gather_source(blender_shader_node , export_settings):
    blender_image = blender_shader_node.image
    return gltf2_blender_gather_image.gather_image(blender_image, export_settings)