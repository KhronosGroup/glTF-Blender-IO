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

from ..com.gltf2_blender_data_path import get_target_object_path, get_target_property_name, get_rotation_modes
from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.io.com import gltf2_io_debug
from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached
from io_scene_gltf2.blender.exp import gltf2_blender_gather_animation_samplers
from io_scene_gltf2.blender.exp import gltf2_blender_gather_animation_channel_target
from io_scene_gltf2.blender.exp import gltf2_blender_gather_animation_sampler_keyframes
from io_scene_gltf2.blender.exp import gltf2_blender_get
from io_scene_gltf2.blender.exp import gltf2_blender_gather_skins
from io_scene_gltf2.blender.exp import gltf2_blender_gather_drivers
from io_scene_gltf2.io.exp.gltf2_io_user_extensions import export_user_extensions


@cached
def gather_animation_channels(blender_action: bpy.types.Action,
                              blender_object: bpy.types.Object,
                              export_settings
                              ) -> typing.List[gltf2_io.AnimationChannel]:
    channels = []


    # First calculate range of animation for baking
    # This is need if user set 'Force sampling' and in case we need to bake
    bake_range_start = None
    bake_range_end = None
    groups = __get_channel_groups(blender_action, blender_object, export_settings)
    # Note: channels has some None items only for SK if some SK are not animated
    for chans in groups:
        ranges = [channel.range() for channel in chans  if channel is not None]
        if bake_range_start is None:
            bake_range_start = min([channel.range()[0] for channel in chans  if channel is not None])
        else:
            bake_range_start = min(bake_range_start, min([channel.range()[0] for channel in chans  if channel is not None]))
        if bake_range_end is None:
            bake_range_end = max([channel.range()[1] for channel in chans  if channel is not None])
        else:
            bake_range_end = max(bake_range_end, max([channel.range()[1] for channel in chans  if channel is not None]))


    if blender_object.type == "ARMATURE" and export_settings['gltf_force_sampling'] is True:
        # We have to store sampled animation data for every deformation bones

        # Check that there are some anim in this action
        if bake_range_start is None:
            return []

        # Then bake all bones
        bones_to_be_animated = []
        if export_settings["gltf_def_bones"] is False:
            bones_to_be_animated = blender_object.data.bones
        else:
            bones_to_be_animated, _, _ = gltf2_blender_gather_skins.get_bone_tree(None, blender_object)
            bones_to_be_animated = [blender_object.pose.bones[b.name] for b in bones_to_be_animated]

        for bone in bones_to_be_animated:
            for p in ["location", "rotation_quaternion", "scale"]:
                channel = __gather_animation_channel(
                    (),
                    blender_object,
                    export_settings,
                    bone.name,
                    p,
                    bake_range_start,
                    bake_range_end,
                    blender_action.name,
                    None)
                channels.append(channel)


        # Retrieve animation on armature object itself, if any
        fcurves_armature = __gather_armature_object_channel_groups(blender_action, blender_object, export_settings)
        for channel_group in fcurves_armature:
            # No need to sort on armature, that can't have SK
            if len(channel_group) == 0:
                # Only errors on channels, ignoring
                continue
            channel = __gather_animation_channel(channel_group, blender_object, export_settings, None, None, bake_range_start, bake_range_end, blender_action.name, None)
            if channel is not None:
                channels.append(channel)


        # Retrieve channels for drivers, if needed
        obj_driver = blender_object.proxy if blender_object.proxy else blender_object
        drivers_to_manage = gltf2_blender_gather_drivers.get_sk_drivers(obj_driver)
        for obj, fcurves in drivers_to_manage:
            channel = __gather_animation_channel(
                fcurves,
                blender_object,
                export_settings,
                None,
                None,
                bake_range_start,
                bake_range_end,
                blender_action.name,
                obj)
            channels.append(channel)

    else:
        for channel_group in __get_channel_groups(blender_action, blender_object, export_settings):
            channel_group_sorted = __get_channel_group_sorted(channel_group, blender_object)
            if len(channel_group_sorted) == 0:
                # Only errors on channels, ignoring
                continue
            channel = __gather_animation_channel(channel_group_sorted, blender_object, export_settings, None, None, bake_range_start, bake_range_end, blender_action.name, None)
            if channel is not None:
                channels.append(channel)


    # resetting driver caches
    gltf2_blender_gather_drivers.get_sk_driver_values.reset_cache()
    gltf2_blender_gather_drivers.get_sk_drivers.reset_cache()
    # resetting bone caches
    gltf2_blender_gather_animation_sampler_keyframes.get_bone_matrix.reset_cache()

    return channels

def __get_channel_group_sorted(channels: typing.Tuple[bpy.types.FCurve], blender_object: bpy.types.Object):
    # if this is shapekey animation, we need to sort in same order than shapekeys
    # else, no need to sort
    if blender_object.type == "MESH":
        first_channel = channels[0]
        object_path = get_target_object_path(first_channel.data_path)
        if object_path:
            if not blender_object.data.shape_keys:
                # Something is wrong. Maybe the user assigned an armature action
                # to a mesh object. Returning without sorting
                return channels

            # This is shapekeys, we need to sort channels
            shapekeys_idx = {}
            cpt_sk = 0
            for sk in blender_object.data.shape_keys.key_blocks:
                if sk == sk.relative_key:
                    continue
                if sk.mute is True:
                    continue
                shapekeys_idx[sk.name] = cpt_sk
                cpt_sk += 1

            # Note: channels will have some None items only for SK if some SK are not animated
            idx_channel_mapping = []
            all_sorted_channels = []
            for sk_c in channels:
                try:
                    sk_name = blender_object.data.shape_keys.path_resolve(get_target_object_path(sk_c.data_path)).name
                    idx = shapekeys_idx[sk_name]
                    idx_channel_mapping.append((shapekeys_idx[sk_name], sk_c))
                except:
                    # Something is wrong. For example, an armature action linked to a mesh object
                    continue

            existing_idx = dict(idx_channel_mapping)
            for i in range(0, cpt_sk):
                if i not in existing_idx.keys():
                    all_sorted_channels.append(None)
                else:
                    all_sorted_channels.append(existing_idx[i])

            if all([i is None for i in all_sorted_channels]): # all channel in error, and some non keyed SK
                return channels             # This happen when an armature action is linked to a mesh object with non keyed SK

            return tuple(all_sorted_channels)

    # if not shapekeys, stay in same order, because order doesn't matter
    return channels

def __gather_animation_channel(channels: typing.Tuple[bpy.types.FCurve],
                               blender_object: bpy.types.Object,
                               export_settings,
                               bake_bone: typing.Union[str, None],
                               bake_channel: typing.Union[str, None],
                               bake_range_start,
                               bake_range_end,
                               action_name: str,
                               driver_obj
                               ) -> typing.Union[gltf2_io.AnimationChannel, None]:
    if not __filter_animation_channel(channels, blender_object, export_settings):
        return None

    __target= __gather_target(channels, blender_object, export_settings, bake_bone, bake_channel, driver_obj)
    if __target.path is not None:
        animation_channel = gltf2_io.AnimationChannel(
            extensions=__gather_extensions(channels, blender_object, export_settings, bake_bone),
            extras=__gather_extras(channels, blender_object, export_settings, bake_bone),
            sampler=__gather_sampler(channels, blender_object, export_settings, bake_bone, bake_channel, bake_range_start, bake_range_end, action_name, driver_obj),
            target=__target
        )

        export_user_extensions('gather_animation_channel_hook',
                               export_settings,
                               animation_channel,
                               channels,
                               blender_object,
                               bake_bone,
                               bake_channel,
                               bake_range_start,
                               bake_range_end,
                               action_name)

        return animation_channel
    return None


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
                     action_name,
                     driver_obj
                     ) -> gltf2_io.AnimationSampler:
    return gltf2_blender_gather_animation_samplers.gather_animation_sampler(
        channels,
        blender_object,
        bake_bone,
        bake_channel,
        bake_range_start,
        bake_range_end,
        action_name,
        driver_obj,
        export_settings
    )


def __gather_target(channels: typing.Tuple[bpy.types.FCurve],
                    blender_object: bpy.types.Object,
                    export_settings,
                    bake_bone: typing.Union[str, None],
                    bake_channel: typing.Union[str, None],
                    driver_obj
                    ) -> gltf2_io.AnimationChannelTarget:
    return gltf2_blender_gather_animation_channel_target.gather_animation_channel_target(
        channels, blender_object, bake_bone, bake_channel, driver_obj, export_settings)


def __get_channel_groups(blender_action: bpy.types.Action, blender_object: bpy.types.Object, export_settings):
    targets = {}
    multiple_rotation_mode_detected = False
    for fcurve in blender_action.fcurves:
        # In some invalid files, channel hasn't any keyframes ... this channel need to be ignored
        if len(fcurve.keyframe_points) == 0:
            continue
        try:
            target_property = get_target_property_name(fcurve.data_path)
        except:
            gltf2_io_debug.print_console("WARNING", "Invalid animation fcurve name on action {}".format(blender_action.name))
            continue
        object_path = get_target_object_path(fcurve.data_path)

        # find the object affected by this action
        if not object_path:
            target = blender_object
        else:
            try:
                target = gltf2_blender_get.get_object_from_datapath(blender_object, object_path)
                if blender_object.type == "MESH" and object_path.startswith("key_blocks"):
                    shape_key = blender_object.data.shape_keys.path_resolve(object_path)
                    if shape_key.mute is True:
                        continue
                    target = blender_object.data.shape_keys
            except ValueError as e:
                # if the object is a mesh and the action target path can not be resolved, we know that this is a morph
                # animation.
                if blender_object.type == "MESH":
                    try:
                        shape_key = blender_object.data.shape_keys.path_resolve(object_path)
                        if shape_key.mute is True:
                            continue
                        target = blender_object.data.shape_keys
                    except:
                        # Something is wrong, for example a bone animation is linked to an object mesh...
                        gltf2_io_debug.print_console("WARNING", "Animation target {} not found".format(object_path))
                        continue
                else:
                    gltf2_io_debug.print_console("WARNING", "Animation target {} not found".format(object_path))
                    continue

        # Detect that object or bone are not multiple keyed for euler and quaternion
        # Keep only the current rotation mode used by object / bone
        rotation, rotation_modes = get_rotation_modes(target_property)
        if rotation and target.rotation_mode not in rotation_modes:
            multiple_rotation_mode_detected = True
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

    if multiple_rotation_mode_detected is True:
        gltf2_io_debug.print_console("WARNING", "Multiple rotation mode detected for {}".format(blender_object.name))

    return map(tuple, groups)

def __gather_armature_object_channel_groups(blender_action: bpy.types.Action, blender_object: bpy.types.Object, export_settings):

    targets = {}

    if blender_object.type != "ARMATURE":
        return tuple()

    for fcurve in blender_action.fcurves:
        object_path = get_target_object_path(fcurve.data_path)
        if object_path != "":
            continue

        # In some invalid files, channel hasn't any keyframes ... this channel need to be ignored
        if len(fcurve.keyframe_points) == 0:
            continue
        try:
            target_property = get_target_property_name(fcurve.data_path)
        except:
            gltf2_io_debug.print_console("WARNING", "Invalid animation fcurve name on action {}".format(blender_action.name))
            continue
        target = gltf2_blender_get.get_object_from_datapath(blender_object, object_path)

        # Detect that armature is not multiple keyed for euler and quaternion
        # Keep only the current rotation mode used by object
        rotation, rotation_modes = get_rotation_modes(target_property)
        if rotation and target.rotation_mode not in rotation_modes:
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
