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

import bpy
import typing
from io_scene_gltf2.io.com import gltf2_io
from .gltf2_blender_gather_armature_channel_target import gather_armature_sampled_channel_target
from .gltf2_blender_gather_armature_sampler import gather_bone_sampled_animation_sampler
from io_scene_gltf2.io.exp.gltf2_io_user_extensions import export_user_extensions
from io_scene_gltf2.blender.exp import gltf2_blender_gather_drivers
from .gltf2_blender_gather_armature_keyframes import get_bone_matrix
from .gltf2_blender_gather_object_channels import gather_sampled_object_channel


def gather_armature_sampled_channels(armature_uuid, blender_action_name, export_settings)  -> typing.List[gltf2_io.AnimationChannel]:
    channels = []

    #TODOANIM use_frame_range? Managed here or at upper level
    #TODOANIM : check if there is really some animation on the action must be done before

    # Then bake all bones
    bones_to_be_animated = []
    bones_uuid = export_settings["vtree"].get_all_bones(armature_uuid)
    bones_to_be_animated = [export_settings["vtree"].nodes[b].blender_bone.name for b in bones_uuid]

    # List of really animated bones is needed for optimization decision
    # TODOANIM : need to implement that (with not sampled code)
    # TODOANIM use bone.name instead of bone?
    list_of_animated_bone_channels = []
    # for channel_group in __get_channel_groups(blender_action, blender_object, export_settings):
    #     channel_group_sorted = __get_channel_group_sorted(channel_group, blender_object)
    #     list_of_animated_bone_channels.extend([(gltf2_blender_get.get_object_from_datapath(blender_object, get_target_object_path(i.data_path)).name, get_target_property_name(i.data_path)) for i in channel_group])

    for bone in bones_to_be_animated:
        for p in ["location", "rotation_quaternion", "scale"]:
            channel = gather_sampled_bone_channel(
                armature_uuid,
                bone,
                p,
                blender_action_name,
                (bone, p) in list_of_animated_bone_channels,
                export_settings)
            if channel is not None:
                channels.append(channel)

    # Retrieve animation on armature object itself, if any
    # If armature is baked (no animation of armature), need to use all channels
    if blender_action_name == armature_uuid:
        armature_channels = ["location", "rotation_quaternion", "scale"]
    else:
        armature_channels = __gather_armature_object_channel(bpy.data.actions[blender_action_name], export_settings)
    for channel in armature_channels:
        armature_channel = gather_sampled_object_channel(
            armature_uuid,
            channel,
            blender_action_name,
            True, # channel is animated (because we detect it on __gather_armature_object_channel)
            export_settings
            )

        if armature_channel is not None:
            channels.append(armature_channel)
    

    # Retrieve channels for drivers, if needed
    #TODOANIM need to be done on bake weights anim

    # resetting driver caches
    gltf2_blender_gather_drivers.get_sk_driver_values.reset_cache()
    gltf2_blender_gather_drivers.get_sk_drivers.reset_cache()
    # resetting bone caches
    get_bone_matrix.reset_cache() #TODOANIM when we will have a cache system

    return channels

def gather_sampled_bone_channel(
        armature_uuid: str,
        bone: str,
        channel: str,
        action_name: str,
        node_channel_is_animated: bool,
        export_settings
        ):

    __target= __gather_target(armature_uuid, bone, channel, export_settings)
    if __target.path is not None:
        sampler = __gather_sampler(armature_uuid, bone, channel, action_name, node_channel_is_animated, export_settings)

        if sampler is None:
            # After check, no need to animate this node for this channel
            return None

        animation_channel = gltf2_io.AnimationChannel(
            extensions=None,
            extras=None,
            sampler=sampler,
            target=__target
        )

        export_user_extensions('gather_animation_channel_hook',
                               export_settings,
                               animation_channel,
                               channel,
                               export_settings['vtree'].nodes[armature_uuid].blender_object,
                               bone,
                               node_channel_is_animated
                               )

        return animation_channel
    return None

    
def __gather_target(armature_uuid: str,
                    bone: str,
                    channel: str,
                    export_settings
                    ) -> gltf2_io.AnimationChannelTarget:

    return gather_armature_sampled_channel_target(
        armature_uuid, bone, channel, export_settings)

def __gather_sampler(armature_uuid, bone, channel, action_name, node_channel_is_animated, export_settings):
    return gather_bone_sampled_animation_sampler(
        armature_uuid,
        bone,
        channel,
        action_name,
        node_channel_is_animated,
        export_settings
        )

def __gather_armature_object_channel(blender_action: str, export_settings):
    channels = []
    for p in ["location", "rotation_quaternion", "scale", "delta_location", "delta_scale", "delta_rotation_euler", "delta_rotation_quaternion"]:
        if p in [f.data_path for f in blender_action.fcurves]:
            channels.append(
                {
                    "location":"location",
                    "rotation_quaternion": "rotation_quaternion",
                    "scale": "scale",
                    "delta_location": "location",
                    "delta_scale": "scale",
                    "delta_rotation_euler": "rotation_quaternion",
                    "delta_rotation_quaternion": "rotation_quaternion"
                }.get(p)
            )

    return list(set(channels)) #remove doubles