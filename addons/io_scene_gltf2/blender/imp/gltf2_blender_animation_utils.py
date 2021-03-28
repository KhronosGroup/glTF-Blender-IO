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

def simulate_stash(obj, track_name, action, start_frame=None):
    # Simulate stash :
    # * add a track
    # * add an action on track
    # * lock & mute the track
    if not obj.animation_data:
        obj.animation_data_create()
    tracks = obj.animation_data.nla_tracks
    new_track = tracks.new(prev=None)
    new_track.name = track_name
    if start_frame is None:
        start_frame = bpy.context.scene.frame_start
    _strip = new_track.strips.new(action.name, start_frame, action)
    new_track.lock = True
    new_track.mute = True

def restore_animation_on_object(obj, anim_name):
    if not getattr(obj, 'animation_data', None):
        return

    for track in obj.animation_data.nla_tracks:
        if track.name != anim_name:
            continue
        if not track.strips:
            continue

        obj.animation_data.action = track.strips[0].action
        return

    obj.animation_data.action = None

def make_fcurve(action, co, data_path, index=0, group_name='', interpolation=None):
    try:
        fcurve = action.fcurves.new(data_path=data_path, index=index, action_group=group_name)
    except:
        # Some non valid files can have multiple target path
        return None

    fcurve.keyframe_points.add(len(co) // 2)
    fcurve.keyframe_points.foreach_set('co', co)

    # Setting interpolation
    ipo = {
        'CUBICSPLINE': 'BEZIER',
        'LINEAR': 'LINEAR',
        'STEP': 'CONSTANT',
    }[interpolation or 'LINEAR']
    ipo = bpy.types.Keyframe.bl_rna.properties['interpolation'].enum_items[ipo].value
    fcurve.keyframe_points.foreach_set('interpolation', [ipo] * len(fcurve.keyframe_points))

    # For CUBICSPLINE, also set the handle types to AUTO
    if interpolation == 'CUBICSPLINE':
        ty = bpy.types.Keyframe.bl_rna.properties['handle_left_type'].enum_items['AUTO'].value
        fcurve.keyframe_points.foreach_set('handle_left_type', [ty] * len(fcurve.keyframe_points))
        fcurve.keyframe_points.foreach_set('handle_right_type', [ty] * len(fcurve.keyframe_points))

    fcurve.update() # force updating tangents (this may change when tangent will be managed)

    return fcurve
