# Copyright 2018-2019 The glTF-Blender-IO authors.
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

from ..com.gltf2_blender_data_path import get_target_object_path, get_target_property_name
from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.io.com import gltf2_io_debug
from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached
from io_scene_gltf2.blender.exp import gltf2_blender_gather_animation_samplers
from io_scene_gltf2.blender.exp import gltf2_blender_gather_animation_channel_target
from io_scene_gltf2.blender.exp import gltf2_blender_get


@cached
def gather_animation_channels(blender_action: bpy.types.Action,
                              blender_object: bpy.types.Object,
                              export_settings
                              ) -> typing.List[gltf2_io.AnimationChannel]:
    channels = []

    if blender_object.type == "ARMATURE" and export_settings['gltf_force_sampling'] is True:
        # We have to store sampled animation data for every deformation bones

        # First calculate range of animation for baking
        bake_range_start = None
        bake_range_end = None
        groups = __get_channel_groups(blender_action, blender_object, export_settings)
        for chans in groups:
            ranges = [channel.range() for channel in chans]
            if bake_range_start is None:
                bake_range_start = min([channel.range()[0] for channel in chans])
            else:
                bake_range_start = min(bake_range_start, min([channel.range()[0] for channel in chans]))
            if bake_range_end is None:
                bake_range_end = max([channel.range()[1] for channel in chans])
            else:
                bake_range_end = max(bake_range_end, max([channel.range()[1] for channel in chans]))

        # Then bake all bones
        for bone in blender_object.data.bones:
            for p in ["location", "rotation_quaternion", "scale"]:
                channel = __gather_animation_channel(
                    (),
                    blender_object,
                    export_settings,
                    bone.name,
                    p,
                    bake_range_start,
                    bake_range_end,
                    blender_action.name)
                channels.append(channel)
    else:
        for channel_group in __get_channel_groups(blender_action, blender_object, export_settings):
            channel = __gather_animation_channel(channel_group, blender_object, export_settings, None, None, None, None, blender_action.name)
            if channel is not None:
                channels.append(channel)

    return channels


def __gather_animation_channel(channels: typing.Tuple[bpy.types.FCurve],
                               blender_object: bpy.types.Object,
                               export_settings,
                               bake_bone: typing.Union[str, None],
                               bake_channel: typing.Union[str, None],
                               bake_range_start,
                               bake_range_end,
                               action_name: str
                               ) -> typing.Union[gltf2_io.AnimationChannel, None]:
    if not __filter_animation_channel(channels, blender_object, export_settings):
        return None

    return gltf2_io.AnimationChannel(
        extensions=__gather_extensions(channels, blender_object, export_settings, bake_bone),
        extras=__gather_extras(channels, blender_object, export_settings, bake_bone),
        sampler=__gather_sampler(channels, blender_object, export_settings, bake_bone, bake_channel, bake_range_start, bake_range_end, action_name),
        target=__gather_target(channels, blender_object, export_settings, bake_bone, bake_channel)
    )


def __filter_animation_channel(channels: typing.Tuple[bpy.types.FCurve],
                               blender_object: bpy.types.Object,
                               export_settings
                               ) -> bool:
    return True


def __gather_extensions(channels: typing.Tuple[bpy.types.FCurve],
                        blender_object: bpy.types.Object,
                        export_settings,
                        bake_bone: typing.Union[str, None]
                        ) -> typing.Any:
    return None


def __gather_extras(channels: typing.Tuple[bpy.types.FCurve],
                    blender_object: bpy.types.Object,
                    export_settings,
                    bake_bone: typing.Union[str, None]
                    ) -> typing.Any:
    return None


def __gather_sampler(channels: typing.Tuple[bpy.types.FCurve],
                     blender_object: bpy.types.Object,
                     export_settings,
                     bake_bone: typing.Union[str, None],
                     bake_channel: typing.Union[str, None],
                     bake_range_start,
                     bake_range_end,
                     action_name
                     ) -> gltf2_io.AnimationSampler:
    return gltf2_blender_gather_animation_samplers.gather_animation_sampler(
        channels,
        blender_object,
        bake_bone,
        bake_channel,
        bake_range_start,
        bake_range_end,
        action_name,
        export_settings
    )


def __gather_target(channels: typing.Tuple[bpy.types.FCurve],
                    blender_object: bpy.types.Object,
                    export_settings,
                    bake_bone: typing.Union[str, None],
                    bake_channel: typing.Union[str, None]
                    ) -> gltf2_io.AnimationChannelTarget:
    return gltf2_blender_gather_animation_channel_target.gather_animation_channel_target(
        channels, blender_object, bake_bone, bake_channel, export_settings)


def __get_channel_groups(blender_action: bpy.types.Action, blender_object: bpy.types.Object, export_settings):
    targets = {}
    for fcurve in blender_action.fcurves:
        target_property = get_target_property_name(fcurve.data_path)
        object_path = get_target_object_path(fcurve.data_path)

        # find the object affected by this action
        if not object_path:
            target = blender_object
        else:
            try:
                target = gltf2_blender_get.get_object_from_datapath(blender_object, object_path)
            except ValueError as e:
                # if the object is a mesh and the action target path can not be resolved, we know that this is a morph
                # animation.
                if blender_object.type == "MESH":
                    # if you need the specific shape key for some reason, this is it:
                    # shape_key = blender_object.data.shape_keys.path_resolve(object_path)
                    target = blender_object.data.shape_keys
                else:
                    gltf2_io_debug.print_console("WARNING", "Animation target {} not found".format(object_path))
                    continue

        # group channels by target object and affected property of the target
        target_properties = targets.get(target, {})
        channels = target_properties.get(target_property, [])
        channels.append(fcurve)
        target_properties[target_property] = channels
        targets[target] = target_properties

    groups = []
    for p in targets.values():
        groups += list(p.values())

    return map(tuple, groups)
