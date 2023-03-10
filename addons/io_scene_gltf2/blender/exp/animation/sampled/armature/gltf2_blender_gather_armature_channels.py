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
from ......io.com import gltf2_io
from ......io.exp.gltf2_io_user_extensions import export_user_extensions
from ......blender.com.gltf2_blender_conversion import get_gltf_interpolation
from .....com.gltf2_blender_conversion import get_target, get_channel_from_target
from ...fcurves.gltf2_blender_gather_fcurves_channels import get_channel_groups
from ...gltf2_blender_gather_drivers import get_sk_drivers
from ..object.gltf2_blender_gather_object_channels import gather_sampled_object_channel
from ..shapekeys.gltf2_blender_gather_sk_channels import gather_sampled_sk_channel
from .gltf2_blender_gather_armature_channel_target import gather_armature_sampled_channel_target
from .gltf2_blender_gather_armature_sampler import gather_bone_sampled_animation_sampler

def gather_armature_sampled_channels(armature_uuid, blender_action_name, export_settings)  -> typing.List[gltf2_io.AnimationChannel]:
    channels = []

    # Then bake all bones
    bones_to_be_animated = []
    bones_uuid = export_settings["vtree"].get_all_bones(armature_uuid)
    bones_to_be_animated = [export_settings["vtree"].nodes[b].blender_bone.name for b in bones_uuid]

    # List of really animated bones is needed for optimization decision
    list_of_animated_bone_channels = {}
    if armature_uuid != blender_action_name and blender_action_name in bpy.data.actions:
        # Not bake situation
        channels_animated, to_be_sampled = get_channel_groups(armature_uuid, bpy.data.actions[blender_action_name], export_settings)
        for chan in [chan for chan in channels_animated.values() if chan['bone'] is not None]:
            for prop in chan['properties'].keys():
                list_of_animated_bone_channels[
                        (
                            chan['bone'],
                            get_channel_from_target(get_target(prop))
                        )
                    ] = get_gltf_interpolation(chan['properties'][prop][0].keyframe_points[0].interpolation) # Could be exported without sampling : keep interpolation

        for _, _, chan_prop, chan_bone in [chan for chan in to_be_sampled if chan[1] == "BONE"]:
            list_of_animated_bone_channels[
                    (
                        chan_bone,
                        chan_prop,
                    )
                ] = "LINEAR" # if forced to be sampled, keep LINEAR interpolation


    for bone in bones_to_be_animated:
        for p in ["location", "rotation_quaternion", "scale"]:
            channel = gather_sampled_bone_channel(
                armature_uuid,
                bone,
                p,
                blender_action_name,
                (bone, p) in list_of_animated_bone_channels.keys(),
                list_of_animated_bone_channels[(bone, p)] if (bone, p) in list_of_animated_bone_channels.keys() else "LINEAR",
                export_settings)
            if channel is not None:
                channels.append(channel)

    # Retrieve animation on armature object itself, if any
    # If armature is baked (no animation of armature), need to use all channels
    if blender_action_name == armature_uuid or export_settings['gltf_animation_mode'] in ["SCENE", "NLA_TRACKS"]:
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
    drivers_to_manage = get_sk_drivers(armature_uuid, export_settings)
    for obj_driver_uuid in drivers_to_manage:
        channel = gather_sampled_sk_channel(obj_driver_uuid, armature_uuid + "_" + blender_action_name, export_settings)
        if channel is not None:
            channels.append(channel)

    return channels

def gather_sampled_bone_channel(
        armature_uuid: str,
        bone: str,
        channel: str,
        action_name: str,
        node_channel_is_animated: bool,
        node_channel_interpolation: str,
        export_settings
        ):

    __target= __gather_target(armature_uuid, bone, channel, export_settings)
    if __target.path is not None:
        sampler = __gather_sampler(armature_uuid, bone, channel, action_name, node_channel_is_animated, node_channel_interpolation, export_settings)

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
                               action_name,
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

def __gather_sampler(armature_uuid, bone, channel, action_name, node_channel_is_animated, node_channel_interpolation, export_settings):
    return gather_bone_sampled_animation_sampler(
        armature_uuid,
        bone,
        channel,
        action_name,
        node_channel_is_animated,
        node_channel_interpolation,
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
