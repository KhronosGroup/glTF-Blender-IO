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
from ......blender.com.conversion import get_gltf_interpolation
from .channel_target import gather_data_sampled_channel_target
from .sampler import gather_data_sampled_animation_sampler


def gather_data_sampled_channels(blender_type_data, blender_id, blender_action_name, slot_identifier,
                                 additional_key, export_settings) -> typing.List[gltf2_io.AnimationChannel]:
    channels = []

    list_of_animated_data_channels = {}  # TODOPointer

    baseColorFactor_alpha_merged_already_done = False
    for path in export_settings['KHR_animation_pointer'][blender_type_data][blender_id]['paths'].keys():

        # Do not manage alpha, as it will be managaed by the baseColorFactor (merging Color and alpha)
        if export_settings['KHR_animation_pointer'][blender_type_data][blender_id]['paths'][path][
                'path'] == "/materials/XXX/pbrMetallicRoughness/baseColorFactor" and baseColorFactor_alpha_merged_already_done is True:
            continue

        channel = gather_sampled_data_channel(
            blender_type_data,
            blender_id,
            path,
            blender_action_name,
            slot_identifier,
            path in list_of_animated_data_channels.keys(),
            list_of_animated_data_channels[path] if path in list_of_animated_data_channels.keys() else get_gltf_interpolation(export_settings['gltf_sampling_interpolation_fallback'], export_settings),
            additional_key,
            export_settings)
        if channel is not None:
            channels.append(channel)

        if export_settings['KHR_animation_pointer'][blender_type_data][blender_id]['paths'][path]['path'] == "/materials/XXX/pbrMetallicRoughness/baseColorFactor":
            baseColorFactor_alpha_merged_already_done = True

    return channels


def gather_sampled_data_channel(
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

    __target = __gather_target(blender_type_data, blender_id, channel, additional_key, export_settings)
    if __target.path is not None:
        sampler, alpha_cst = __gather_sampler(
            blender_type_data,
            blender_id,
            channel,
            action_name,
            slot_identifier,
            node_channel_is_animated,
            node_channel_interpolation,
            additional_key,
            export_settings)

        if sampler is None:
            # After check, no need to animate this node for this channel
            return None

        # Add temporatory data for alpha, in target object
        __target.tmp_alpha_cst = alpha_cst

        animation_channel = gltf2_io.AnimationChannel(
            extensions=None,
            extras=None,
            sampler=sampler,
            target=__target
        )

        return animation_channel
    return None


def __gather_target(
    blender_type_data: str,
    blender_id: str,
    channel: str,
    additional_key: str,  # Used to differentiate between material / material node_tree
    export_settings
) -> gltf2_io.AnimationChannelTarget:

    return gather_data_sampled_channel_target(
        blender_type_data, blender_id, channel, additional_key, export_settings)


def __gather_sampler(
        blender_type_data,
        blender_id,
        channel,
        action_name,
        slot_identifier,
        node_channel_is_animated,
        node_channel_interpolation,
        additional_key,
        export_settings):
    return gather_data_sampled_animation_sampler(
        blender_type_data,
        blender_id,
        channel,
        action_name,
        slot_identifier,
        node_channel_is_animated,
        node_channel_interpolation,
        additional_key,
        export_settings
    )
