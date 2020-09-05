# Copyright 2018 The glTF-Blender-IO authors.
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
from io_scene_gltf2.io.exp.gltf2_io_user_extensions import export_user_extensions
from io_scene_gltf2.io.com.gltf2_io_constants import TextureFilter, TextureWrap


@cached
def gather_sampler(blender_shader_node: bpy.types.Node, export_settings):
    sampler = gltf2_io.Sampler(
        extensions=__gather_extensions(blender_shader_node, export_settings),
        extras=__gather_extras(blender_shader_node, export_settings),
        mag_filter=__gather_mag_filter(blender_shader_node, export_settings),
        min_filter=__gather_min_filter(blender_shader_node, export_settings),
        name=__gather_name(blender_shader_node, export_settings),
        wrap_s=__gather_wrap_s(blender_shader_node, export_settings),
        wrap_t=__gather_wrap_t(blender_shader_node, export_settings)
    )

    export_user_extensions('gather_sampler_hook', export_settings, sampler, blender_shader_node)

    if not sampler.extensions and not sampler.extras and not sampler.name:
        return __sampler_by_value(
            sampler.mag_filter,
            sampler.min_filter,
            sampler.wrap_s,
            sampler.wrap_t,
            export_settings,
        )

    return sampler


@cached
def __sampler_by_value(mag_filter, min_filter, wrap_s, wrap_t, export_settings):
    # @cached function to dedupe samplers with the same settings.
    return gltf2_io.Sampler(
        extensions=None,
        extras=None,
        mag_filter=mag_filter,
        min_filter=min_filter,
        name=None,
        wrap_s=wrap_s,
        wrap_t=wrap_t,
    )


def __gather_extensions(blender_shader_node, export_settings):
    return None


def __gather_extras(blender_shader_node, export_settings):
    return None


def __gather_mag_filter(blender_shader_node, export_settings):
    if blender_shader_node.interpolation == 'Closest':
        return TextureFilter.Nearest
    return TextureFilter.Linear


def __gather_min_filter(blender_shader_node, export_settings):
    if blender_shader_node.interpolation == 'Closest':
        return TextureFilter.NearestMipmapNearest
    return TextureFilter.NearestMipmapLinear


def __gather_name(blender_shader_node, export_settings):
    return None


def __gather_wrap_s(blender_shader_node, export_settings):
    if blender_shader_node.extension == 'EXTEND':
        return TextureWrap.ClampToEdge
    return None


def __gather_wrap_t(blender_shader_node, export_settings):
    if blender_shader_node.extension == 'EXTEND':
        return TextureWrap.ClampToEdge
    return None
