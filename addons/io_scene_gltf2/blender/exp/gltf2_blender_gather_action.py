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
from ..com.gltf2_blender_data_path import is_bone_anim_channel
from io_scene_gltf2.io.exp.gltf2_io_user_extensions import export_user_extensions
from io_scene_gltf2.blender.exp.gltf2_blender_gather_tree import VExportNode
from .gltf2_blender_gather_animation_utils import reset_bone_matrix, link_samplers
from .gltf2_blender_gather_fcurves_animation import gather_animation_fcurves
from io_scene_gltf2.io.com.gltf2_io_debug import print_console
from io_scene_gltf2.io.exp.gltf2_io_user_extensions import export_user_extensions
from .gltf2_blender_gather_armature_action_sampled import gather_action_armature_sampled
from .gltf2_blender_gather_armature_channels import gather_sampled_bone_channel
from .gltf2_blender_gather_object_action_sampled import gather_action_object_sampled
from .gltf2_blender_gather_sk_action_sampled import gather_action_sk_sampled
from .gltf2_blender_gather_object_channels import gather_object_sampled_channels, gather_sampled_object_channel
from .gltf2_blender_gather_sk_channels import gather_sampled_sk_channel


def gather_actions_animations(export_settings):

    animations = []
    merged_tracks = {}

    vtree = export_settings['vtree']
    for obj_uuid in vtree.get_all_objects():

        # Do not manage not exported objects
        if vtree.nodes[obj_uuid].node is None:
            continue

        animations_, merged_tracks = gather_action_animations(obj_uuid, merged_tracks, len(animations), export_settings)
        animations += animations_

    if export_settings['gltf_animation_mode'] == "ACTIVE_ACTIONS":
        # Fake an animation with all animations of the scene
        merged_tracks = {}
        merged_tracks_name = 'Animation'
        if(len(export_settings['gltf_nla_strips_merged_animation_name']) > 0):
            merged_tracks_name = export_settings['gltf_nla_strips_merged_animation_name']
        merged_tracks[merged_tracks_name] = []
        for idx, animation in enumerate(animations):
            merged_tracks[merged_tracks_name].append(idx)


    to_delete_idx = []
    for merged_anim_track in merged_tracks.keys():
        if len(merged_tracks[merged_anim_track]) < 2:

            # There is only 1 animation in the track
            # If name of the track is not a default name, use this name for action
            if len(merged_tracks[merged_anim_track]) != 0:
                animations[merged_tracks[merged_anim_track][0]].name = merged_anim_track

            continue

        base_animation_idx = None
        offset_sampler = 0

        for idx, anim_idx in enumerate(merged_tracks[merged_anim_track]):
            if idx == 0:
                base_animation_idx = anim_idx
                animations[anim_idx].name = merged_anim_track
                already_animated = []
                for channel in animations[anim_idx].channels:
                    already_animated.append((channel.target.node, channel.target.path))
                continue

            to_delete_idx.append(anim_idx)

            # Merging extensions
            # Provide a hook to handle extension merging since there is no way to know author intent
            export_user_extensions('merge_animation_extensions_hook', export_settings, animations[anim_idx], animations[base_animation_idx])

            # Merging extras
            # Warning, some values can be overwritten if present in multiple merged animations
            if animations[anim_idx].extras is not None:
                for k in animations[anim_idx].extras.keys():
                    if animations[base_animation_idx].extras is None:
                        animations[base_animation_idx].extras = {}
                    animations[base_animation_idx].extras[k] = animations[anim_idx].extras[k]

            offset_sampler = len(animations[base_animation_idx].samplers)
            for sampler in animations[anim_idx].samplers:
                animations[base_animation_idx].samplers.append(sampler)

            for channel in animations[anim_idx].channels:
                if (channel.target.node, channel.target.path) in already_animated:
                    print_console("WARNING", "Some strips have same channel animation ({}), on node {} !".format(channel.target.path, channel.target.node.name))
                    continue
                animations[base_animation_idx].channels.append(channel)
                animations[base_animation_idx].channels[-1].sampler = animations[base_animation_idx].channels[-1].sampler + offset_sampler
                already_animated.append((channel.target.node, channel.target.path))

    new_animations = []
    if len(to_delete_idx) != 0:
        for idx, animation in enumerate(animations):
            if idx in to_delete_idx:
                continue
            new_animations.append(animation)
    else:
        new_animations = animations


    return new_animations


def gather_action_animations(  obj_uuid: int,
                        tracks: typing.Dict[str, typing.List[int]],
                        offset: int,
                        export_settings) -> typing.Tuple[typing.List[gltf2_io.Animation], typing.Dict[str, typing.List[int]]]:
    """
    Gather all animations which contribute to the objects property, and corresponding track names

    :param blender_object: The blender object which is animated
    :param export_settings:
    :return: A list of glTF2 animations and tracks
    """
    animations = []

    blender_object = export_settings['vtree'].nodes[obj_uuid].blender_object

    # Collect all 'actions' affecting this object. There is a direct mapping between blender actions and glTF animations
    blender_actions = __get_blender_actions(blender_object, export_settings)

    # When object is not animated at all (no SK)
    # We can create an animation for this object
    if len(blender_actions) == 0:
        animation = __bake_animation(obj_uuid, export_settings)
        if animation is not None:
            animations.append(animation)


####### Keep current situation and prepare export
    current_action = None
    current_world_matrix = None
    if blender_object.animation_data and blender_object.animation_data.action:
        # There is an active action. Storing it, to be able to restore after switching all actions during export
        current_action = blender_object.animation_data.action
    elif len(blender_actions) != 0 and blender_object.animation_data is not None and blender_object.animation_data.action is None:
        # No current action set, storing world matrix of object
        current_world_matrix = blender_object.matrix_world.copy()

    # Remove any solo (starred) NLA track. Restored after export
    solo_track = None
    if blender_object.animation_data:
        for track in blender_object.animation_data.nla_tracks:
            if track.is_solo:
                solo_track = track
                track.is_solo = False
                break

    # Remove any tweak mode. Restore after export
    if blender_object.animation_data:
        restore_tweak_mode = blender_object.animation_data.use_tweak_mode

    # Remove use of NLA. Restore after export
    if blender_object.animation_data:
        current_use_nla = blender_object.animation_data.use_nla
        blender_object.animation_data.use_nla = False

    export_user_extensions('animation_switch_loop_hook', export_settings, blender_object, False)

######## Export

    # Export all collected actions.
    for blender_action, track_name, on_type in blender_actions:

        # Set action as active, to be able to bake if needed
        if on_type == "OBJECT": # Not for shapekeys!
            if blender_object.animation_data.action is None \
                    or (blender_object.animation_data.action.name != blender_action.name):
                if blender_object.animation_data.is_property_readonly('action'):
                    blender_object.animation_data.use_tweak_mode = False
                try:
                    reset_bone_matrix(blender_object, export_settings)
                    export_user_extensions('pre_animation_switch_hook', export_settings, blender_object, blender_action, track_name, on_type)
                    blender_object.animation_data.action = blender_action
                    export_user_extensions('post_animation_switch_hook', export_settings, blender_object, blender_action, track_name, on_type)
                except:
                    error = "Action is readonly. Please check NLA editor"
                    print_console("WARNING", "Animation '{}' could not be exported. Cause: {}".format(blender_action.name, error))
                    continue

        # No need to set active shapekeys animations, this is needed for bone baking

        if export_settings['gltf_force_sampling'] is True:
            if export_settings['vtree'].nodes[obj_uuid].blender_object.type == "ARMATURE":
                animation = gather_action_armature_sampled(obj_uuid, blender_action, export_settings)
            elif on_type == "OBJECT":
                animation = gather_action_object_sampled(obj_uuid, blender_action, export_settings)
            else:
                animation = gather_action_sk_sampled(obj_uuid, blender_action, export_settings)
        else:
            # Not sampled
            # This returns 
            #  - animation on fcurves
            #  - fcurve that cannot be handled not sampled, to be sampled
            # to_be_sampled is : (object_uuid , type , prop, optional(bone.name) )
            animation, to_be_sampled = gather_animation_fcurves(obj_uuid, blender_action, export_settings)
            for (obj_uuid, type_, prop, bone) in to_be_sampled:
                if type_ == "BONE":
                    channel = gather_sampled_bone_channel(obj_uuid, bone, prop, blender_action.name, True, export_settings)
                elif type_ == "OBJECT":
                    channel = gather_sampled_object_channel(obj_uuid, prop, blender_action.name, True, export_settings)
                elif type_ == "SK":
                    channel = gather_sampled_sk_channel(obj_uuid, blender_action.name, export_settings)
                else:
                    print("Type unknown. Should not happen")

                if animation is None and channel is not None:
                    # If all channels need to be sampled, no animation was created
                    # Need to create animation, and add channel
                    animation = gltf2_io.Animation(
                        channels=[channel],
                        extensions=None,
                        extras=None,
                        name=blender_action.name,
                        samplers=[]
                    )
                else:
                    if channel is not None:
                        animation.channels.append(channel)

        # If we are in a SK animation, and we need to bake (if there also in TRS anim)
        if len([a for a in blender_actions if a[2] == "OBJECT"]) == 0 and on_type == "SHAPEKEY":
            if export_settings['gltf_bake_animation'] is True and export_settings['gltf_force_sampling'] is True:
            # We also have to check if this is a skinned mesh, because we don't have to force animation baking on this case
            # (skinned meshes TRS must be ignored, says glTF specification)
                if export_settings['vtree'].nodes[obj_uuid].skin is None:
                    channels = gather_object_sampled_channels(obj_uuid, obj_uuid, export_settings)
                    if channels is not None:
                        if animation is None:
                            animation = gltf2_io.Animation(
                                    channels=channels,
                                    extensions=None, # as other animations
                                    extras=None, # Because there is no animation to get extras from
                                    name=blender_object.name, # Use object name as animation name
                                    samplers=[]
                                )
                        else:
                            animation.channels.extend(channels)

        if animation is not None:
            link_samplers(animation, export_settings)
            animations.append(animation)

            # Store data for merging animation later
            if track_name is not None: # Do not take into account animation not in NLA
                # Do not take into account default NLA track names
                if not (track_name.startswith("NlaTrack") or track_name.startswith("[Action Stash]")):
                    if track_name not in tracks.keys():
                        tracks[track_name] = []
                    tracks[track_name].append(offset + len(animations)-1) # Store index of animation in animations


####### Restoring current situation

    # Restore action status
    # TODO: do this in a finally
    if blender_object.animation_data:
        if blender_object.animation_data.action is not None:
            if current_action is None:
                # remove last exported action
                reset_bone_matrix(blender_object, export_settings)
                blender_object.animation_data.action = None
            elif blender_object.animation_data.action.name != current_action.name:
                # Restore action that was active at start of exporting
                reset_bone_matrix(blender_object, export_settings)
                blender_object.animation_data.action = current_action
        if solo_track is not None:
            solo_track.is_solo = True
        blender_object.animation_data.use_tweak_mode = restore_tweak_mode
        blender_object.animation_data.use_nla = current_use_nla

    if current_world_matrix is not None:
        blender_object.matrix_world = current_world_matrix

    export_user_extensions('animation_switch_loop_hook', export_settings, blender_object, True)

    return animations, tracks

def __bake_animation(obj_uuid: str, export_settings):

    blender_object = export_settings['vtree'].nodes[obj_uuid].blender_object

    # No TRS animation are found for this object.
    # But we may need to bake
    # (Only when force sampling is ON)
    # If force sampling is OFF, can lead to inconsistent export anyway
    if export_settings['gltf_bake_animation'] is True and blender_object.type != "ARMATURE" and export_settings['gltf_force_sampling'] is True:
        # We also have to check if this is a skinned mesh, because we don't have to force animation baking on this case
        # (skinned meshes TRS must be ignored, says glTF specification)
        if export_settings['vtree'].nodes[obj_uuid].skin is None:
            animation = gather_action_object_sampled(obj_uuid, None, export_settings)

            if animation is not None and animation.channels:
                link_samplers(animation, export_settings)
                return animation
    elif export_settings['gltf_bake_animation'] is True and blender_object.type == "ARMATURE":
        # We need to bake all bones. Because some bone can have some constraints linking to
        # some other armature bones, for example

        # if there is no animation in file => no need to bake
        if len(bpy.data.actions) > 0:
            animation = gather_action_armature_sampled(obj_uuid, None, export_settings)

            link_samplers(animation, export_settings)
            if animation is not None:
                return animation
    return None

def __get_blender_actions(blender_object: bpy.types.Object,
                            export_settings
                          ) -> typing.List[typing.Tuple[bpy.types.Action, str, str]]:
    blender_actions = []
    blender_tracks = {}
    action_on_type = {}

    export_user_extensions('pre_gather_actions_hook', export_settings, blender_object)

    if blender_object.animation_data is not None:
        # Collect active action.
        if blender_object.animation_data.action is not None:
            blender_actions.append(blender_object.animation_data.action)
            blender_tracks[blender_object.animation_data.action.name] = None
            action_on_type[blender_object.animation_data.action.name] = "OBJECT"

        # Collect associated strips from NLA tracks.
        if export_settings['gltf_animation_mode'] == "ACTIONS":
            for track in blender_object.animation_data.nla_tracks:
                # Multi-strip tracks do not export correctly yet (they need to be baked),
                # so skip them for now and only write single-strip tracks.
                non_muted_strips = [strip for strip in track.strips if strip.action is not None and strip.mute is False]
                if track.strips is None or len(non_muted_strips) != 1:
                    continue
                for strip in non_muted_strips:
                    blender_actions.append(strip.action)
                    blender_tracks[strip.action.name] = track.name # Always set after possible active action -> None will be overwrite
                    action_on_type[strip.action.name] = "OBJECT"

    # TODOANIM : for caching, actions linked to SK must be after actions about TRS
    if export_settings['gltf_morph_anim'] and blender_object.type == "MESH" \
            and blender_object.data is not None \
            and blender_object.data.shape_keys is not None \
            and blender_object.data.shape_keys.animation_data is not None:

            if blender_object.data.shape_keys.animation_data.action is not None:
                blender_actions.append(blender_object.data.shape_keys.animation_data.action)
                blender_tracks[blender_object.data.shape_keys.animation_data.action.name] = None
                action_on_type[blender_object.data.shape_keys.animation_data.action.name] = "SHAPEKEY"

            if export_settings['gltf_animation_mode'] == "ACTIONS":
                for track in blender_object.data.shape_keys.animation_data.nla_tracks:
                    # Multi-strip tracks do not export correctly yet (they need to be baked),
                    # so skip them for now and only write single-strip tracks.
                    non_muted_strips = [strip for strip in track.strips if strip.action is not None and strip.mute is False]
                    if track.strips is None or len(non_muted_strips) != 1:
                        continue
                    for strip in non_muted_strips:
                        blender_actions.append(strip.action)
                        blender_tracks[strip.action.name] = track.name # Always set after possible active action -> None will be overwrite
                        action_on_type[strip.action.name] = "SHAPEKEY"

    # If there are only 1 armature, include all animations, even if not in NLA
    if export_settings['gltf_export_anim_single_armature'] is True:
        if blender_object.type == "ARMATURE":
            if len(export_settings['vtree'].get_all_node_of_type(VExportNode.ARMATURE)) == 1:
                # Keep all actions on objects (no Shapekey animation)
                for act in [a for a in bpy.data.actions if a.id_root == "OBJECT"]:
                    # We need to check this is an armature action
                    # Checking that at least 1 bone is animated
                    if not __is_armature_action(act):
                        continue
                    # Check if this action is already taken into account
                    if act.name in blender_tracks.keys():
                        continue
                    blender_actions.append(act)
                    blender_tracks[act.name] = None
                    action_on_type[act.name] = "OBJECT"

    # Use a class to get parameters, to be able to modify them
    class GatherActionHookParameters:
        def __init__(self, blender_actions, blender_tracks, action_on_type):
            self.blender_actions = blender_actions
            self.blender_tracks = blender_tracks
            self.action_on_type = action_on_type

    gatheractionhookparams = GatherActionHookParameters(blender_actions, blender_tracks, action_on_type)

    export_user_extensions('gather_actions_hook', export_settings, blender_object, gatheractionhookparams)

    # Get params back from hooks
    blender_actions = gatheractionhookparams.blender_actions
    blender_tracks = gatheractionhookparams.blender_tracks
    action_on_type = gatheractionhookparams.action_on_type

    # Remove duplicate actions.
    blender_actions = list(set(blender_actions))
    # sort animations alphabetically (case insensitive) so they have a defined order and match Blender's Action list
    blender_actions.sort(key = lambda a: a.name.lower())

    return [(blender_action, blender_tracks[blender_action.name], action_on_type[blender_action.name]) for blender_action in blender_actions]

def __is_armature_action(blender_action) -> bool:
    for fcurve in blender_action.fcurves:
        if is_bone_anim_channel(fcurve.data_path):
            return True
    return False