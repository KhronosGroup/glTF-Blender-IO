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
from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached
from io_scene_gltf2.io.exp.gltf2_io_user_extensions import export_user_extensions
from io_scene_gltf2.io.com.gltf2_io_constants import TextureFilter, TextureWrap
from io_scene_gltf2.blender.exp.gltf2_blender_get import (
    previous_node,
    previous_socket,
    get_const_from_socket,
)


@cached
def gather_sampler(blender_shader_node: bpy.types.Node, export_settings):
    wrap_s, wrap_t = __gather_wrap(blender_shader_node, export_settings)

    sampler = gltf2_io.Sampler(
        extensions=__gather_extensions(blender_shader_node, export_settings),
        extras=__gather_extras(blender_shader_node, export_settings),
        mag_filter=__gather_mag_filter(blender_shader_node, export_settings),
        min_filter=__gather_min_filter(blender_shader_node, export_settings),
        name=__gather_name(blender_shader_node, export_settings),
        wrap_s=wrap_s,
        wrap_t=wrap_t,
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
    return TextureFilter.LinearMipmapLinear


def __gather_name(blender_shader_node, export_settings):
    return None


def __gather_wrap(blender_shader_node, export_settings):
    # First gather from the Texture node
    if blender_shader_node.extension == 'EXTEND':
        wrap_s = TextureWrap.ClampToEdge
    elif blender_shader_node.extension == 'CLIP':
        # Not possible in glTF, but ClampToEdge is closest
        wrap_s = TextureWrap.ClampToEdge
    else:
        wrap_s = TextureWrap.Repeat
    wrap_t = wrap_s

    # Take manual wrapping into account
    result = detect_manual_uv_wrapping(blender_shader_node)
    if result:
        if result['wrap_s'] is not None: wrap_s = result['wrap_s']
        if result['wrap_t'] is not None: wrap_t = result['wrap_t']

    # Omit if both are repeat
    if (wrap_s, wrap_t) == (TextureWrap.Repeat, TextureWrap.Repeat):
        wrap_s, wrap_t = None, None

    return wrap_s, wrap_t


def detect_manual_uv_wrapping(blender_shader_node):
    # Detects UV wrapping done using math nodes. This is for emulating wrap
    # modes Blender doesn't support. It looks like
    #
    #     next_socket => [Sep XYZ] => [Wrap S] => [Comb XYZ] => blender_shader_node
    #                              => [Wrap T] =>
    #
    # The [Wrap _] blocks are either math nodes (eg. PINGPONG for mirrored
    # repeat), or can be omitted.
    #
    # Returns None if not detected. Otherwise a dict containing the wrap
    # mode in each direction (or None), and next_socket.
    result = {}

    comb = previous_node(blender_shader_node.inputs['Vector'])
    if comb is None or comb.type != 'COMBXYZ': return None

    for soc in ['X', 'Y']:
        node = previous_node(comb.inputs[soc])
        if node is None: return None

        if node.type == 'SEPXYZ':
            # Passed through without change
            wrap = None
            prev_socket = previous_socket(comb.inputs[soc])
        elif node.type == 'MATH':
            # Math node applies a manual wrap
            if (node.operation == 'PINGPONG' and
                    get_const_from_socket(node.inputs[1], kind='VALUE') == 1.0):  # scale = 1
                wrap = TextureWrap.MirroredRepeat
            elif (node.operation == 'WRAP' and
                    get_const_from_socket(node.inputs[1], kind='VALUE') == 0.0 and  # min = 0
                    get_const_from_socket(node.inputs[2], kind='VALUE') == 1.0):    # max = 1
                wrap = TextureWrap.Repeat
            else:
                return None

            prev_socket = previous_socket(node.inputs[0])
        else:
            return None

        if prev_socket is None: return None
        prev_node = prev_socket.node
        if prev_node.type != 'SEPXYZ': return None
        # Make sure X goes to X, etc.
        if prev_socket.name != soc: return None
        # Make sure both attach to the same SeparateXYZ node
        if soc == 'X':
            sep = prev_node
        else:
            if sep != prev_node: return None

        result['wrap_s' if soc == 'X' else 'wrap_t'] = wrap

    result['next_socket'] = sep.inputs[0]
    return result
