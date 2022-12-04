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
from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached
from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import bonecache
from io_scene_gltf2.blender.exp.gltf2_blender_gather_drivers import get_sk_drivers, get_sk_driver_values
from io_scene_gltf2.blender.exp.gltf2_blender_gather_tree import VExportNode
from .gltf2_blender_gather_keyframes import Keyframe
import numpy as np


# TODOANIM : Warning : If you change some parameter here, need to be changed in cache system
@bonecache 
def get_bone_matrix(
        armature_uuid: str,
        bone: str,
        channel,
        action_name,
        range_start: int, #TODOANIM
        range_end: int,   #TODOANIM
        current_frame: int,
        step: int,
        export_settings
    ): 

    data = {}

    # Always using bake_range, because some bones may need to be baked,
    # even if user didn't request it

    start_frame = range_start
    end_frame = range_end


    frame = start_frame
    while frame <= end_frame:
        data[frame] = {}
        bpy.context.scene.frame_set(int(frame))
        bones = export_settings['vtree'].get_all_bones(armature_uuid)

        for bone_uuid in bones:
            blender_bone = export_settings['vtree'].nodes[bone_uuid].blender_bone

            if export_settings['vtree'].nodes[bone_uuid].parent_uuid is not None and export_settings['vtree'].nodes[export_settings['vtree'].nodes[bone_uuid].parent_uuid].blender_type == VExportNode.BONE:
                blender_bone_parent = export_settings['vtree'].nodes[export_settings['vtree'].nodes[bone_uuid].parent_uuid].blender_bone
                rest_mat = blender_bone_parent.bone.matrix_local.inverted_safe() @ blender_bone.bone.matrix_local
                matrix = rest_mat.inverted_safe() @ blender_bone_parent.matrix.inverted_safe() @ blender_bone.matrix
            else:
                if blender_bone.parent is None:
                    matrix = blender_bone.bone.matrix_local.inverted_safe() @ blender_bone.matrix
                else:
                    # Bone has a parent, but in export, after filter, is at root of armature
                    matrix = blender_bone.matrix.copy()

            data[frame][blender_bone.name] = matrix

        # TODOANIM need to have a way to cache/bake anything needed

        # If some drivers must be evaluated, do it here, to avoid to have to change frame by frame later
        drivers_to_manage = get_sk_drivers(armature_uuid, export_settings)
        for dr_obj_uuid, dr_fcurves in drivers_to_manage:
            vals = get_sk_driver_values(dr_obj_uuid, frame, dr_fcurves, export_settings)

        frame += step

    return data

@cached
def gather_bone_sampled_keyframes(
        armature_uuid: str,
        bone: str,
        channel: str,
        action_name: str,
        node_channel_is_animated: bool,
        export_settings
        ) -> typing.List[Keyframe]:

    #TODOANIM manage frame range!!!
    start_frame = 1 #TODOANIM
    end_frame = 50  #TODOANIM

    keyframes = []

    frame = start_frame
    step = export_settings['gltf_frame_step'] #TODOANIM

    while frame <= end_frame:
        key = Keyframe(None, frame, channel) #TODOANIM first parameter not needed ... cf refactor of class Keyframe?

        mat = get_bone_matrix(
            armature_uuid,
            bone,
            channel,
            action_name,
            start_frame, #TODOANIM : manage in export_settings to avoid passing as parameter ?
            end_frame,   #TODOANIM : manage in export_settings to avoid passing as parameter ?
            frame,
            step,
            export_settings
        )
        trans, rot, scale = mat.decompose()

        key.value = {
            "location": trans,
            "rotation_quaternion": rot,
            "scale": scale
            }[channel]

        keyframes.append(key)
        frame += step

    if not export_settings['gltf_optimize_animation']:
        return keyframes

    # For armatures
    # Check if all values are the same
    # In that case, if there is no real keyframe on this channel for this given bone,
    # We can ignore these keyframes
    # if there are some fcurve, we can keep only 2 keyframes, first and last
    cst = fcurve_is_constant(keyframes)

    if node_channel_is_animated is True: # fcurve on this bone for this property
            # Keep animation, but keep only 2 keyframes if data are not changing
            return [keyframes[0], keyframes[-1]] if cst is True and len(keyframes) >= 2 else keyframes
    else: # bone is not animated (no fcurve)
        # Not keeping if not changing property if user decided to not keep
        if export_settings['gltf_optimize_animation_keep_armature'] is False:
            return None if cst is True else keyframes
        else:
            # Keep at least 2 keyframes if data are not changing
            return [keyframes[0], keyframes[-1]] if cst is True and len(keyframes) >= 2 else keyframes

def fcurve_is_constant(keyframes):
    return all([j < 0.0001 for j in np.ptp([[k.value[i] for i in range(len(keyframes[0].value))] for k in keyframes], axis=0)])