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
import mathutils
from .gltf2_blender_gather_keyframes import Keyframe
from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached, objectcache
from io_scene_gltf2.blender.exp.gltf2_blender_gather_tree import VExportNode
import numpy as np

# TODOANIM : Warning : If you change some parameter here, need to be changed in cache system
@objectcache
def get_object_matrix(blender_obj_uuid: str,
                      action_name: str,
                      bake_range_start: int, #TODOANIM
                      bake_range_end: int,   #TODOANIM
                      current_frame: int,
                      step: int,
                      export_settings,
                      only_gather_provided=False
                    ):

    data = {}

    # TODOANIM : bake_range_start & bake_range_end are no more needed here
    # Because we bake, we don't know exactly the frame range,
    # So using min / max of all actions

    start_frame = bake_range_start
    end_frame = bake_range_end

    if only_gather_provided:
        obj_uuids = [blender_obj_uuid]
    else:
        obj_uuids = [uid for (uid, n) in export_settings['vtree'].nodes.items() if n.blender_type not in [VExportNode.BONE]]

    frame = start_frame
    while frame <= end_frame:
        bpy.context.scene.frame_set(int(frame))

        for obj_uuid in obj_uuids:
            blender_obj = export_settings['vtree'].nodes[obj_uuid].blender_object

            # if this object is not animated, do not skip :
            # We need this object too in case of bake
            # TODOANIM : only when bake is enabled. If not, no need to keep not animated objects?

            # calculate local matrix
            if export_settings['vtree'].nodes[obj_uuid].parent_uuid is None:
                parent_mat = mathutils.Matrix.Identity(4).freeze()
            else:
                if export_settings['vtree'].nodes[export_settings['vtree'].nodes[obj_uuid].parent_uuid].blender_type not in [VExportNode.BONE]:
                    parent_mat = export_settings['vtree'].nodes[export_settings['vtree'].nodes[obj_uuid].parent_uuid].blender_object.matrix_world
                else:
                    # Object animated is parented to a bone
                    blender_bone = export_settings['vtree'].nodes[export_settings['vtree'].nodes[obj_uuid].parent_bone_uuid].blender_bone
                    armature_object = export_settings['vtree'].nodes[export_settings['vtree'].nodes[export_settings['vtree'].nodes[obj_uuid].parent_bone_uuid].armature].blender_object
                    axis_basis_change = mathutils.Matrix(
                        ((1.0, 0.0, 0.0, 0.0), (0.0, 0.0, 1.0, 0.0), (0.0, -1.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0)))

                    parent_mat = armature_object.matrix_world @ blender_bone.matrix @ axis_basis_change

            #For object inside collection (at root), matrix world is already expressed regarding collection parent
            if export_settings['vtree'].nodes[obj_uuid].parent_uuid is not None and export_settings['vtree'].nodes[export_settings['vtree'].nodes[obj_uuid].parent_uuid].blender_type == VExportNode.COLLECTION:
                parent_mat = mathutils.Matrix.Identity(4).freeze()

            mat = parent_mat.inverted_safe() @ blender_obj.matrix_world

            if obj_uuid not in data.keys():
                data[obj_uuid] = {}

            if blender_obj.animation_data and blender_obj.animation_data.action:
                if blender_obj.animation_data.action.name not in data[obj_uuid].keys():
                    data[obj_uuid][blender_obj.animation_data.action.name] = {}
                data[obj_uuid][blender_obj.animation_data.action.name][frame] = mat
            else:
                # case of baking selected object.
                # There is no animation, so use uuid of object as key
                # TODOANIM : only when bake is enabled. If not, no need to keep not animated objects?
                if obj_uuid not in data[obj_uuid].keys():
                    data[obj_uuid][obj_uuid] = {}
                data[obj_uuid][obj_uuid][frame] = mat

        frame += step
    return data

@cached
def gather_object_baked_keyframes(
        obj_uuid: str,
        channel: str,
        action_name: str,
        node_channel_is_animated: bool,
        export_settings
        ):

    #TODOANIM manage frame range!!!
    start_frame = 1 #TODOANIM
    end_frame = 50  #TODOANIM

    keyframes = []

    frame = start_frame
    step = export_settings['gltf_frame_step'] #TODOANIM

    while frame <= end_frame:
        key = Keyframe(None, frame, channel)

        mat = get_object_matrix(obj_uuid,
            action_name,
            start_frame, #TODOANIM
            end_frame,   #TODOANIM
            frame,
            step,
            export_settings)

        trans, rot, sca = mat.decompose()
        key.value_total = {
            "location": trans,
            "rotation_quaternion": rot,
            "scale": sca,
        }[channel]

        keyframes.append(key)
        frame += step

    if not export_settings['gltf_optimize_animation']:
        return keyframes

    # For objects, if all values are the same, we keep only first and last
    cst = fcurve_is_constant(keyframes)
    if node_channel_is_animated is True:
        return [keyframes[0], keyframes[-1]] if cst is True and len(keyframes) >= 2 else keyframes
    else:
        # baked object
        # Not keeping if not changing property if user decided to not keep
        if export_settings['gltf_optimize_animation_keep_object'] is False:
            return None if cst is True else keyframes
        else:
            # Keep at least 2 keyframes if data are not changing
            return [keyframes[0], keyframes[-1]] if cst is True and len(keyframes) >= 2 else keyframes

def fcurve_is_constant(keyframes):
    return all([j < 0.0001 for j in np.ptp([[k.value[i] for i in range(len(keyframes[0].value))] for k in keyframes], axis=0)])
    