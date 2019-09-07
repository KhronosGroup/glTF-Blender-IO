# Copyright 2019 The glTF-Blender-IO authors.
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

def simulate_stash(obj, gltf_animation_name, action, start_frame):
    # Simulate stash :
    # * add a track
    # * add an action on track
    # * lock & mute the track
    # * remove active action from object
    tracks = obj.animation_data.nla_tracks
    new_track = tracks.new(prev=None)
    new_track.name = gltf_animation_name if gltf_animation_name is not None else action.name
    strip = new_track.strips.new(action.name, start_frame, action)
    new_track.lock = True
    new_track.mute = True
    obj.animation_data.action = None

def restore_last_action(obj):

    if not obj.animation_data:
        return
    tracks = obj.animation_data.nla_tracks
    if len(tracks) == 0:
        return
    if len(tracks[0].strips) == 0:
        return
    obj.animation_data.action = tracks[0].strips[0].action
