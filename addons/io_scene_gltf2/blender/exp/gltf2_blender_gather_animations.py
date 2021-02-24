# Copyright 2018-2021 The glTF-Blender-IO authors.
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
from io_scene_gltf2.blender.exp import gltf2_blender_gather_animation_channels
from io_scene_gltf2.io.com.gltf2_io_debug import print_console
from ..com.gltf2_blender_extras import generate_extras
from io_scene_gltf2.io.exp.gltf2_io_user_extensions import export_user_extensions


def gather_animations(blender_object: bpy.types.Object,
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

    # Collect all 'actions' affecting this object. There is a direct mapping between blender actions and glTF animations
    blender_actions = __get_blender_actions(blender_object, export_settings)

    # save the current active action of the object, if any
    # We will restore it after export
    current_action = None
    if blender_object.animation_data and blender_object.animation_data.action:
        current_action = blender_object.animation_data.action
    # Remove any solo (starred) NLA track. Restored after export
    solo_track = None
    if blender_object.animation_data:
        for track in blender_object.animation_data.nla_tracks:
            if track.is_solo:
                solo_track = track
                track.is_solo = False
                break

    # Export all collected actions.
    for blender_action, track_name, on_type in blender_actions:

        # Set action as active, to be able to bake if needed
        if on_type == "OBJECT": # Not for shapekeys!
            if blender_object.animation_data.action is None \
                    or (blender_object.animation_data.action.name != blender_action.name):
                if blender_object.animation_data.is_property_readonly('action'):
                    # NLA stuff: some track are on readonly mode, we can't change action
                    error = "Action is readonly. Please check NLA editor"
                    print_console("WARNING", "Animation '{}' could not be exported. Cause: {}".format(blender_action.name, error))
                    continue
                try:
                    blender_object.animation_data.action = blender_action
                except:
                    error = "Action is readonly. Please check NLA editor"
                    print_console("WARNING", "Animation '{}' could not be exported. Cause: {}".format(blender_action.name, error))
                    continue

        # No need to set active shapekeys animations, this is needed for bone baking

        animation = __gather_animation(blender_action, blender_object, export_settings)
        if animation is not None:
            animations.append(animation)

            # Store data for merging animation later
            if track_name is not None: # Do not take into account animation not in NLA
                # Do not take into account default NLA track names
                if not (track_name.startswith("NlaTrack") or track_name.startswith("[Action Stash]")):
                    if track_name not in tracks.keys():
                        tracks[track_name] = []
                    tracks[track_name].append(offset + len(animations)-1) # Store index of animation in animations

    # Restore action status
    # TODO: do this in a finally
    if blender_object.animation_data:
        if blender_object.animation_data.action is not None:
            if current_action is None:
                # remove last exported action
                blender_object.animation_data.action = None
            elif blender_object.animation_data.action.name != current_action.name:
                # Restore action that was active at start of exporting
                blender_object.animation_data.action = current_action
        if solo_track is not None:
            solo_track.is_solo = True

    return animations, tracks


def __gather_animation(blender_action: bpy.types.Action,
                       blender_object: bpy.types.Object,
                       export_settings
                       ) -> typing.Optional[gltf2_io.Animation]:
    if not __filter_animation(blender_action, blender_object, export_settings):
        return None

    name = __gather_name(blender_action, blender_object, export_settings)
    try:
        animation = gltf2_io.Animation(
            channels=__gather_channels(blender_action, blender_object, export_settings),
            extensions=__gather_extensions(blender_action, blender_object, export_settings),
            extras=__gather_extras(blender_action, blender_object, export_settings),
            name=name,
            samplers=__gather_samplers(blender_action, blender_object, export_settings)
        )
    except RuntimeError as error:
        print_console("WARNING", "Animation '{}' could not be exported. Cause: {}".format(name, error))
        return None

    # To allow reuse of samplers in one animation,
    __link_samplers(animation, export_settings)

    if not animation.channels:
        return None

    export_user_extensions('gather_animation_hook', export_settings, animation, blender_action, blender_object)

    return animation


def __filter_animation(blender_action: bpy.types.Action,
                       blender_object: bpy.types.Object,
                       export_settings
                       ) -> bool:
    if blender_action.users == 0:
        return False

    return True


def __gather_channels(blender_action: bpy.types.Action,
                      blender_object: bpy.types.Object,
                      export_settings
                      ) -> typing.List[gltf2_io.AnimationChannel]:
    return gltf2_blender_gather_animation_channels.gather_animation_channels(
        blender_action, blender_object, export_settings)


def __gather_extensions(blender_action: bpy.types.Action,
                        blender_object: bpy.types.Object,
                        export_settings
                        ) -> typing.Any:
    return None


def __gather_extras(blender_action: bpy.types.Action,
                    blender_object: bpy.types.Object,
                    export_settings
                    ) -> typing.Any:

    if export_settings['gltf_extras']:
        return generate_extras(blender_action)
    return None


def __gather_name(blender_action: bpy.types.Action,
                  blender_object: bpy.types.Object,
                  export_settings
                  ) -> typing.Optional[str]:
    return blender_action.name


def __gather_samplers(blender_action: bpy.types.Action,
                      blender_object: bpy.types.Object,
                      export_settings
                      ) -> typing.List[gltf2_io.AnimationSampler]:
    # We need to gather the samplers after gathering all channels --> populate this list in __link_samplers
    return []


def __link_samplers(animation: gltf2_io.Animation, export_settings):
    """
    Move animation samplers to their own list and store their indices at their previous locations.

    After gathering, samplers are stored in the channels properties of the animation and need to be moved
    to their own list while storing an index into this list at the position where they previously were.
    This behaviour is similar to that of the glTFExporter that traverses all nodes
    :param animation:
    :param export_settings:
    :return:
    """
    # TODO: move this to some util module and update gltf2 exporter also
    T = typing.TypeVar('T')

    def __append_unique_and_get_index(l: typing.List[T], item: T):
        if item in l:
            return l.index(item)
        else:
            index = len(l)
            l.append(item)
            return index

    for i, channel in enumerate(animation.channels):
        animation.channels[i].sampler = __append_unique_and_get_index(animation.samplers, channel.sampler)


def __get_blender_actions(blender_object: bpy.types.Object,
                            export_settings
                          ) -> typing.List[typing.Tuple[bpy.types.Action, str, str]]:
    blender_actions = []
    blender_tracks = {}
    action_on_type = {}

    if blender_object.animation_data is not None:
        # Collect active action.
        if blender_object.animation_data.action is not None:
            blender_actions.append(blender_object.animation_data.action)
            blender_tracks[blender_object.animation_data.action.name] = None
            action_on_type[blender_object.animation_data.action.name] = "OBJECT"

        # Collect associated strips from NLA tracks.
        if export_settings['gltf_nla_strips'] is True:
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

    if blender_object.type == "MESH" \
            and blender_object.data is not None \
            and blender_object.data.shape_keys is not None \
            and blender_object.data.shape_keys.animation_data is not None:

            if blender_object.data.shape_keys.animation_data.action is not None:
                blender_actions.append(blender_object.data.shape_keys.animation_data.action)
                blender_tracks[blender_object.data.shape_keys.animation_data.action.name] = None
                action_on_type[blender_object.data.shape_keys.animation_data.action.name] = "SHAPEKEY"

            if export_settings['gltf_nla_strips'] is True:
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

    # Remove duplicate actions.
    blender_actions = list(set(blender_actions))
    # sort animations alphabetically (case insensitive) so they have a defined order and match Blender's Action list
    blender_actions.sort(key = lambda a: a.name.lower())

    return [(blender_action, blender_tracks[blender_action.name], action_on_type[blender_action.name]) for blender_action in blender_actions]
