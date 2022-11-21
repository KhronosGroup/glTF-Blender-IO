# Copyright 2018-2022 The glTF-Blender-IO authors.
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

import typing
from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached
from .gltf2_blender_gather_object_channel_target import gather_object_baked_channel_target
from io_scene_gltf2.io.exp.gltf2_io_user_extensions import export_user_extensions
from .gltf2_blender_gather_object_sampler import gather_object_bake_animation_sampler


#TODOANIM cached?
def gather_object_baked_channels(object_uuid, blender_action, export_settings)  -> typing.List[gltf2_io.AnimationChannel]:

    channels = []

    # TODOANIM : need to implement that (with not sampled code)
    list_of_animated_channels = []

    for p in ["location", "rotation_quaternion", "scale"]:
        channel = gather_object_channel(
            object_uuid,
            p,
            blender_action.name,
            p in list_of_animated_channels,
            export_settings
            )
        if channel is not None:
            channels.append(channel)

    #TODOANIM add hooks

    return channels if len(channels) > 0 else None

@cached
def gather_object_channel(
        obj_uuid: str,
        channel: str,
        action_name: str,
        node_channel_is_animated: bool,
        export_settings
        ):

    __target= __gather_target(obj_uuid, channel, export_settings)
    if __target.path is not None:
        sampler = __gather_sampler(obj_uuid, channel, action_name, node_channel_is_animated, export_settings)

        if sampler is None:
            # After check, no need to animate this node for this channel
            return None

        animation_channel = gltf2_io.AnimationChannel(
            extensions=None,
            extras=None,
            sampler=sampler,
            target=__target
        )

        export_user_extensions('gather_animation_channel_hook', #TODOANIM
                               export_settings,
                               animation_channel,
                               channel,
                               export_settings['vtree'].nodes[obj_uuid].blender_object,
                               node_channel_is_animated
                               )

        return animation_channel
    return None


def __gather_target(
        obj_uuid: str,
        channel: str, 
        export_settings
        ):

    return gather_object_baked_channel_target(
        obj_uuid, channel, export_settings)

def __gather_sampler(
        obj_uuid: str,
        channel: str,
        action_name: str,
        node_channel_is_animated: bool,
        export_settings):


    return gather_object_bake_animation_sampler(
        obj_uuid,
        channel,
        action_name,
        node_channel_is_animated,
        export_settings
        )