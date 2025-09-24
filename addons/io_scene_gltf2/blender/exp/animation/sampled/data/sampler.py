# Copyright 2018-2023 The glTF-Blender-IO authors.
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
import typing
from ......io.com import gltf2_io
from ......io.exp import binary_data as gltf2_io_binary_data
from ......io.com import constants as gltf2_io_constants
from ....cache import cached
from ....accessors import gather_accessor
from .keyframes import gather_data_sampled_keyframes


@cached
def gather_data_sampled_animation_sampler(
        blender_type_data: str,
        blender_id: str,
        channel: str,
        action_name: str,
        slot_identifier: str,
        node_channel_is_animated: bool,
        node_channel_interpolation: str,
        additional_key: str,  # Used to differentiate between material / material node_tree
        export_settings
):

    keyframes, alpha_cst = __gather_keyframes(
        blender_type_data,
        blender_id,
        channel,
        action_name,
        slot_identifier,
        node_channel_is_animated,
        additional_key,
        export_settings)

    if keyframes is None:
        # After check, no need to animate this node for this channel
        return None, None

    # Now we are raw input/output, we need to convert to glTF data
    input, output = __convert_keyframes(blender_type_data, blender_id, channel, keyframes, action_name, export_settings)

    sampler = gltf2_io.AnimationSampler(extensions=None, extras=None, input=input, interpolation=__gather_interpolation(
        blender_type_data, node_channel_is_animated, node_channel_interpolation, keyframes, export_settings), output=output)

    return sampler, alpha_cst


def __gather_keyframes(
        blender_type_data,
        blender_id,
        channel,
        action_name,
        slot_identifier,
        node_channel_is_animated,
        additional_key,  # Used to differentiate between material / material node_tree
        export_settings):

    keyframes, alpha_cst = gather_data_sampled_keyframes(
        blender_type_data,
        blender_id,
        channel,
        action_name,
        slot_identifier,
        node_channel_is_animated,
        additional_key,
        export_settings
    )

    if keyframes is None:
        # After check, no need to animation this node
        return None, None

    return keyframes, alpha_cst


def __convert_keyframes(blender_type_data, blender_id, channel, keyframes, action_name, export_settings):

    # Sliding can come from:
    # - option SLIDE for negative frames
    # - option to start animation at frame 0 for looping
    if blender_id in export_settings['slide'].keys() and action_name in export_settings['slide'][blender_id].keys():
        for k in keyframes:
            k.frame += -export_settings['slide'][blender_id][action_name]
            k.seconds = k.frame / bpy.context.scene.render.fps

    times = [k.seconds for k in keyframes]
    input = gather_accessor(
        gltf2_io_binary_data.BinaryData.from_list(times, gltf2_io_constants.ComponentType.Float),
        gltf2_io_constants.ComponentType.Float,
        len(times),
        tuple([max(times)]),
        tuple([min(times)]),
        gltf2_io_constants.DataType.Scalar,
        export_settings)

    values = []
    for keyframe in keyframes:
        keyframe_value = __convert_to_gltf(keyframe.value)
        values += keyframe_value

     # store the keyframe data in a binary buffer
    component_type = gltf2_io_constants.ComponentType.Float
    if type(keyframes[0].value).__name__ != "float":
        data_type = gltf2_io_constants.DataType.vec_type_from_num(len(keyframes[0].value))
    else:
        data_type = gltf2_io_constants.DataType.vec_type_from_num(1)

    output = gather_accessor(
        gltf2_io_binary_data.BinaryData.from_list(values, component_type),
        component_type,
        len(values) // gltf2_io_constants.DataType.num_elements(data_type),
        None,
        None,
        data_type,
        export_settings
    )

    return input, output


def __gather_interpolation(
        blender_type_data,
        node_channel_is_animated,
        node_channel_interpolation,
        keyframes,
        export_settings):
    # TODOPointer
    return export_settings['gltf_sampling_interpolation_fallback']


def __convert_to_gltf(value):
    return value if type(value).__name__ != "float" else [value]
