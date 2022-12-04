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

from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached
from io_scene_gltf2.io.exp.gltf2_io_user_extensions import export_user_extensions
from io_scene_gltf2.io.com import gltf2_io
from .gltf2_blender_gather_sk_channel_target import gather_sk_sampled_channel_target
from .gltf2_blender_gather_sk_sampler import gather_sk_sampled_animation_sampler



def gather_sk_sampled_channels(
        object_uuid: str,
        blender_action_name: str,
        export_settings):
    
    # Only 1 channel when exporting shape keys

    channels = []

    channel = gather_sampled_sk_channel(
        object_uuid,
        blender_action_name,
        export_settings
        )

    if channel is not None:
        channels.append(channel)

    #TODOANIM add hooks

    return channels if len(channels) > 0 else None

@cached
def gather_sampled_sk_channel(
        obj_uuid: str,
        action_name: str,
        export_settings
        ):

    __target= __gather_target(obj_uuid, export_settings)
    if __target.path is not None:
        sampler = __gather_sampler(obj_uuid, action_name, export_settings)

        if sampler is None:
            # After check, no need to animate this node for this channel
            return None

        animation_channel = gltf2_io.AnimationChannel(
            extensions=None,
            extras=None,
            sampler=sampler,
            target=__target
        )

        #TODOANIM add hooks

        return animation_channel
    return None

def __gather_target(obj_uuid: str, export_settings):
    return gather_sk_sampled_channel_target(
        obj_uuid, export_settings)

def __gather_sampler(obj_uuid: str, action_name: str, export_settings):
    return gather_sk_sampled_animation_sampler(
        obj_uuid,
        action_name,
        export_settings
        )