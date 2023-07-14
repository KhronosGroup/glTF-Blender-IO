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
from .gltf2_blender_gather_material_channel_target import gather_material_sampled_channel_target
from .gltf2_blender_gather_material_sampler import gather_material_sampled_animation_sampler


def gather_material_sampled_channels(blender_material_id, blender_action_name, export_settings)  -> typing.List[gltf2_io.AnimationChannel]:
    channels = []

    for path in export_settings['KHR_animation_pointer']['materials'][blender_material_id]['paths'].keys():
        channel = gather_sampled_material_channel(
            blender_material_id,
            path,
            blender_action_name,
            True,    #TODOPointer
            "LINEAR", #TODOPointer
            export_settings)
        if channel is not None:
            channels.append(channel)

    return channels


def gather_sampled_material_channel(
        material_id: str,
        channel: str,
        action_name: str,
        node_channel_is_animated: bool,
        node_channel_interpolation: str,
        export_settings
        ):

    __target= __gather_target(material_id, channel, export_settings)
    if __target.path is not None:
        sampler = __gather_sampler(material_id, channel, action_name, node_channel_is_animated, node_channel_interpolation, export_settings)

        if sampler is None:
            # After check, no need to animate this node for this channel
            return None

        animation_channel = gltf2_io.AnimationChannel(
            extensions=None,
            extras=None,
            sampler=sampler,
            target=__target
        )

        return animation_channel
    return None

def __gather_target(material_id,
                    channel: str,
                    export_settings
                    ) -> gltf2_io.AnimationChannelTarget:

    return gather_material_sampled_channel_target(
        material_id, channel, export_settings)

def __gather_sampler(material_id, channel, action_name, node_channel_is_animated, node_channel_interpolation, export_settings):
    return gather_material_sampled_animation_sampler(
        material_id,
        channel,
        action_name,
        node_channel_is_animated,
        node_channel_interpolation,
        export_settings
        )
