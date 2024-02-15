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
from ....io.com import gltf2_io
from ....io.exp.gltf2_io_user_extensions import export_user_extensions
from ..gltf2_blender_gather_cache import cached
from ..gltf2_blender_gather_tree import VExportNode
from .gltf2_blender_gather_animation_utils import merge_tracks_perform, bake_animation, add_slide_data, reset_bone_matrix, reset_sk_data
from .gltf2_blender_gather_drivers import get_sk_drivers
from .sampled.gltf2_blender_gather_animation_sampling_cache import get_cache_data

def gather_tracks_animations(export_settings):

    animations = []
    merged_tracks = {}

    vtree = export_settings['vtree']
    for obj_uuid in vtree.get_all_objects():

        # Do not manage not exported objects
        if vtree.nodes[obj_uuid].node is None:
            if export_settings['gltf_armature_object_remove'] is True:
                # Manage armature object, as this is the object that has the animation
                if not vtree.nodes[obj_uuid].blender_object:
                    continue
            else:
                continue

        if export_settings['vtree'].nodes[obj_uuid].blender_type == VExportNode.COLLECTION:
            continue

        animations_, merged_tracks = gather_track_animations(obj_uuid, merged_tracks, len(animations), export_settings)
        animations += animations_

    new_animations = merge_tracks_perform(merged_tracks, animations, export_settings)

    return new_animations


def gather_track_animations(  obj_uuid: int,
                        tracks: typing.Dict[str, typing.List[int]],
                        offset: int,
                        export_settings) -> typing.Tuple[typing.List[gltf2_io.Animation], typing.Dict[str, typing.List[int]]]:

    animations = []

    # Bake situation does not export any extra animation channels, as we bake TRS + weights on Track or scene level, without direct
    # Access to fcurve and action data

    blender_object = export_settings['vtree'].nodes[obj_uuid].blender_object
    # Collect all tracks affecting this object.
    blender_tracks = __get_blender_tracks(obj_uuid, export_settings)

    ####### Keep current situation
    current_action = None
    current_sk_action = None
    current_world_matrix = None
    current_use_nla = None
    current_use_nla_sk = None
    restore_track_mute = {}
    restore_track_mute["OBJECT"] = {}
    restore_track_mute["SHAPEKEY"] = {}

    if blender_object.animation_data:
        current_action = blender_object.animation_data.action
        current_use_nla = blender_object.animation_data.use_nla
        restore_tweak_mode = blender_object.animation_data.use_tweak_mode
    current_world_matrix = blender_object.matrix_world.copy()


    if blender_object.type == "MESH" \
            and blender_object.data is not None \
            and blender_object.data.shape_keys is not None \
            and blender_object.data.shape_keys.animation_data is not None:
        current_sk_action = blender_object.data.shape_keys.animation_data.action
        current_use_nla_sk = blender_object.data.shape_keys.animation_data.use_nla

    ####### Prepare export for obj
    solo_track = None
    if blender_object.animation_data:
        blender_object.animation_data.action = None
        blender_object.animation_data.use_nla = True
    # Remove any solo (starred) NLA track. Restored after export
        for track in blender_object.animation_data.nla_tracks:
            if track.is_solo:
                solo_track = track
                track.is_solo = False
                break

    solo_track_sk = None
    if blender_object.type == "MESH" \
            and blender_object.data is not None \
            and blender_object.data.shape_keys is not None \
            and blender_object.data.shape_keys.animation_data is not None:
    # Remove any solo (starred) NLA track. Restored after export
        for track in blender_object.data.shape_keys.animation_data.nla_tracks:
            if track.is_solo:
                solo_track_sk = track
                track.is_solo = False
                break

    # Mute all channels
    for track_group in [b[0] for b in blender_tracks if b[2] == "OBJECT"]:
        for track in track_group:
            restore_track_mute["OBJECT"][track.idx] = blender_object.animation_data.nla_tracks[track.idx].mute
            blender_object.animation_data.nla_tracks[track.idx].mute = True
    for track_group in [b[0] for b in blender_tracks if b[2] == "SHAPEKEY"]:
        for track in track_group:
            restore_track_mute["SHAPEKEY"][track.idx] = blender_object.data.shape_keys.animation_data.nla_tracks[track.idx].mute
            blender_object.data.shape_keys.animation_data.nla_tracks[track.idx].mute = True


    export_user_extensions('animation_track_switch_loop_hook', export_settings, blender_object, False)

    ######## Export

    # Export all collected actions.
    for bl_tracks, track_name, on_type in blender_tracks:
        prepare_tracks_range(obj_uuid, bl_tracks, track_name, export_settings)

        if on_type == "OBJECT":
            # Enable tracks
            for track in bl_tracks:
                export_user_extensions('pre_animation_track_switch_hook', export_settings, blender_object, track, track_name, on_type)
                blender_object.animation_data.nla_tracks[track.idx].mute = False
                export_user_extensions('post_animation_track_switch_hook', export_settings, blender_object, track, track_name, on_type)
        else:
            # Enable tracks
            for track in bl_tracks:
                export_user_extensions('pre_animation_track_switch_hook', export_settings, blender_object, track, track_name, on_type)
                blender_object.data.shape_keys.animation_data.nla_tracks[track.idx].mute = False
                export_user_extensions('post_animation_track_switch_hook', export_settings, blender_object, track, track_name, on_type)

        reset_bone_matrix(blender_object, export_settings)
        if on_type == "SHAPEKEY":
            reset_sk_data(blender_object, blender_tracks, export_settings)

        ##### Export animation
        animation = bake_animation(obj_uuid, track_name, export_settings, mode=on_type)
        get_cache_data.reset_cache()
        if animation is not None:
            animations.append(animation)

            # Store data for merging animation later
            # Do not take into account default NLA track names
            if not (track_name.startswith("NlaTrack") or track_name.startswith("[Action Stash]")):
                if track_name not in tracks.keys():
                    tracks[track_name] = []
                tracks[track_name].append(offset + len(animations)-1) # Store index of animation in animations

        # Restoring muting
        if on_type == "OBJECT":
            for track in bl_tracks:
                blender_object.animation_data.nla_tracks[track.idx].mute = True
        else:
            for track in bl_tracks:
                blender_object.data.shape_keys.animation_data.nla_tracks[track.idx].mute = True


    ############## Restoring
    if current_action is not None:
        blender_object.animation_data.action = current_action
    if current_sk_action is not None:
        blender_object.data.shape_keys.animation_data.action = current_sk_action
    if solo_track is not None:
        solo_track.is_solo = True
    if solo_track_sk is not None:
        solo_track_sk.is_solo = True
    if blender_object.animation_data:
        blender_object.animation_data.use_nla = current_use_nla
        blender_object.animation_data.use_tweak_mode = restore_tweak_mode
        for track_group in [b[0] for b in blender_tracks if b[2] == "OBJECT"]:
            for track in track_group:
                blender_object.animation_data.nla_tracks[track.idx].mute = restore_track_mute["OBJECT"][track.idx]
    if blender_object.type == "MESH" \
            and blender_object.data is not None \
            and blender_object.data.shape_keys is not None \
            and blender_object.data.shape_keys.animation_data is not None:
        blender_object.data.shape_keys.animation_data.use_nla = current_use_nla_sk
        for track_group in [b[0] for b in blender_tracks if b[2] == "SHAPEKEY"]:
            for track in track_group:
                blender_object.data.shape_keys.animation_data.nla_tracks[track.idx].mute = restore_track_mute["SHAPEKEY"][track.idx]

    blender_object.matrix_world = current_world_matrix

    export_user_extensions('animation_track_switch_loop_hook', export_settings, blender_object, True)

    return animations, tracks

@cached
def __get_blender_tracks(obj_uuid: str, export_settings):

    blender_object = export_settings['vtree'].nodes[obj_uuid].blender_object
    export_user_extensions('pre_gather_tracks_hook', export_settings, blender_object)

    tracks, names, types = __get_nla_tracks_obj(obj_uuid, export_settings)
    tracks_sk, names_sk, types_sk = __get_nla_tracks_sk(obj_uuid, export_settings)

    tracks.extend(tracks_sk)
    names.extend(names_sk)
    types.extend(types_sk)

    # Use a class to get parameters, to be able to modify them
    class GatherTrackHookParameters:
        def __init__(self, blender_tracks, blender_tracks_name, track_on_type):
            self.blender_tracks = blender_tracks
            self.blender_tracks_name = blender_tracks_name
            self.track_on_type = track_on_type

    gathertrackhookparams = GatherTrackHookParameters(tracks, names, types)

    export_user_extensions('gather_tracks_hook', export_settings, blender_object, gathertrackhookparams)

    # Get params back from hooks
    tracks = gathertrackhookparams.blender_tracks
    names = gathertrackhookparams.blender_tracks_name
    types = gathertrackhookparams.track_on_type

    return list(zip(tracks, names, types))

class NLATrack:
    def __init__(self, idx, frame_start, frame_end, default_solo, default_muted):
        self.idx = idx
        self.frame_start = frame_start
        self.frame_end = frame_end
        self.default_solo = default_solo
        self.default_muted = default_muted

def __get_nla_tracks_obj(obj_uuid: str, export_settings):

    obj = export_settings['vtree'].nodes[obj_uuid].blender_object

    if not obj.animation_data:
        return [], [], []
    if len(obj.animation_data.nla_tracks) == 0:
        return [], [], []

    exported_tracks = []

    current_exported_tracks = []

    for idx_track, track in enumerate(obj.animation_data.nla_tracks):
        if len(track.strips) == 0:
            continue

        stored_track = NLATrack(
            idx_track,
            track.strips[0].frame_start,
            track.strips[-1].frame_end,
            track.is_solo,
            track.mute
        )

        # Keep tracks where some blending together
        if any([strip.blend_type != 'REPLACE' for strip in track.strips]):
            # There is some blending. Keeping with previous track
            pass
        else:
            # The previous one(s) can go to the list, if any (not for first track)
            if len(current_exported_tracks) != 0:
                exported_tracks.append(current_exported_tracks)
                current_exported_tracks = []
        current_exported_tracks.append(stored_track)

    # End of loop. Keep the last one(s)
    exported_tracks.append(current_exported_tracks)

    track_names = [obj.animation_data.nla_tracks[tracks_group[0].idx].name for tracks_group in exported_tracks]
    on_types = ['OBJECT'] * len(track_names)
    return exported_tracks, track_names, on_types


def __get_nla_tracks_sk(obj_uuid: str, export_settings):

    obj = export_settings['vtree'].nodes[obj_uuid].blender_object

    if not obj.type == "MESH":
        return [], [], []
    if obj.data is None:
        return [], [], []
    if obj.data.shape_keys is None:
        return [], [], []
    if not obj.data.shape_keys.animation_data:
        return [], [], []
    if len(obj.data.shape_keys.animation_data.nla_tracks) == 0:
        return [], [], []

    exported_tracks = []

    current_exported_tracks = []

    for idx_track, track in enumerate(obj.data.shape_keys.animation_data.nla_tracks):
        if len(track.strips) == 0:
            continue

        stored_track = NLATrack(
            idx_track,
            track.strips[0].frame_start,
            track.strips[-1].frame_end,
            track.is_solo,
            track.mute
        )

        # Keep tracks where some blending together
        if any([strip.blend_type != 'REPLACE' for strip in track.strips]):
            # There is some blending. Keeping with previous track
            pass
        else:
            # The previous one(s) can go to the list, if any (not for first track)
            if len(current_exported_tracks) != 0:
                exported_tracks.append(current_exported_tracks)
                current_exported_tracks = []
        current_exported_tracks.append(stored_track)

    # End of loop. Keep the last one(s)
    exported_tracks.append(current_exported_tracks)

    track_names = [obj.data.shape_keys.animation_data.nla_tracks[tracks_group[0].idx].name for tracks_group in exported_tracks]
    on_types = ['SHAPEKEY'] * len(track_names)
    return exported_tracks, track_names, on_types

def prepare_tracks_range(obj_uuid, tracks, track_name, export_settings):

    track_slide = {}

    for idx, btrack in enumerate(tracks):
        frame_start = btrack.frame_start if idx == 0 else min(frame_start, btrack.frame_start)
        frame_end = btrack.frame_end if idx == 0 else max(frame_end, btrack.frame_end)

    # If some negative frame and crop -> set start at 0
    if frame_start < 0 and export_settings['gltf_negative_frames'] == "CROP":
        frame_start = 0

    if export_settings['gltf_frame_range'] is True:
        frame_start = max(bpy.context.scene.frame_start, frame_start)
        frame_end = min(bpy.context.scene.frame_end, frame_end)

    export_settings['ranges'][obj_uuid] = {}
    export_settings['ranges'][obj_uuid][track_name] = {}
    export_settings['ranges'][obj_uuid][track_name]['start'] = int(frame_start)
    export_settings['ranges'][obj_uuid][track_name]['end'] = int(frame_end)

    if export_settings['gltf_negative_frames'] == "SLIDE":
        if not (track_name.startswith("NlaTrack") or track_name.startswith("[Action Stash]")):
            if track_name not in track_slide.keys() or (track_name in track_slide.keys() and frame_start < track_slide[track_name]):
                track_slide.update({track_name:frame_start})
        else:
            if frame_start < 0:
                add_slide_data(frame_start, obj_uuid, track_name, export_settings)


    if export_settings['gltf_anim_slide_to_zero'] is True and frame_start > 0:
        if not (track_name.startswith("NlaTrack") or track_name.startswith("[Action Stash]")):
            if track_name not in track_slide.keys() or (track_name in track_slide.keys() and frame_start < track_slide[track_name]):
                track_slide.update({track_name:frame_start})
        else:
            add_slide_data(frame_start, obj_uuid, track_name, export_settings)


    # For drivers
    if export_settings['vtree'].nodes[obj_uuid].blender_type == VExportNode.ARMATURE and export_settings['gltf_morph_anim'] is True:
        obj_drivers = get_sk_drivers(obj_uuid, export_settings)
        for obj_dr in obj_drivers:
            if obj_dr not in export_settings['ranges']:
                export_settings['ranges'][obj_dr] = {}
            export_settings['ranges'][obj_dr][obj_uuid + "_" + track_name] = {}
            export_settings['ranges'][obj_dr][obj_uuid + "_" + track_name]['start'] = frame_start
            export_settings['ranges'][obj_dr][obj_uuid + "_" + track_name]['end'] = frame_end

    if (export_settings['gltf_negative_frames'] == "SLIDE" \
            or export_settings['gltf_anim_slide_to_zero'] is True) \
            and len(track_slide) > 0:

        if track_name in track_slide.keys():
            if export_settings['gltf_negative_frames'] == "SLIDE" and track_slide[track_name] < 0:
                add_slide_data(track_slide[track_name], obj_uuid, track_name, export_settings)
            elif export_settings['gltf_anim_slide_to_zero'] is True:
                add_slide_data(track_slide[track_name], obj_uuid, track_name, export_settings)
