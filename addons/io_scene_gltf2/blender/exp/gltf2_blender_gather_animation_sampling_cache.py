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

import mathutils
import bpy
from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import objectcache
from io_scene_gltf2.blender.exp.gltf2_blender_gather_tree import VExportNode

# TODOANIM : Warning : If you change some parameter here, need to be changed in cache system
@objectcache
def get_object_cache_data(path: str,
                      blender_obj_uuid: str,
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
                    data[obj_uuid][blender_obj.animation_data.action.name]['matrix'] = {}
                data[obj_uuid][blender_obj.animation_data.action.name]['matrix'][frame] = mat
            else:
                # case of baking selected object.
                # There is no animation, so use uuid of object as key
                # TODOANIM : only when bake is enabled. If not, no need to keep not animated objects?
                if obj_uuid not in data[obj_uuid].keys():
                    data[obj_uuid][obj_uuid] = {}
                    data[obj_uuid][obj_uuid]['matrix'] = {}
                data[obj_uuid][obj_uuid]['matrix'][frame] = mat

            # Check SK animation here, as we are caching data
            # This will avoid to have to do it again when exporting SK animation
            if export_settings['gltf_morph_anim'] and blender_obj.type == "MESH" \
            and blender_obj.data is not None \
            and blender_obj.data.shape_keys is not None \
            and blender_obj.data.shape_keys.animation_data is not None \
            and blender_obj.data.shape_keys.animation_data.action is not None:
                
                if blender_obj.data.shape_keys.animation_data.action.name not in data[obj_uuid].keys():
                    data[obj_uuid][blender_obj.data.shape_keys.animation_data.action.name] = {}
                    data[obj_uuid][blender_obj.data.shape_keys.animation_data.action.name]['sk'] = {}
                data[obj_uuid][blender_obj.data.shape_keys.animation_data.action.name]['sk'][frame] = [k.value if k.mute is False else 0.0 for k in blender_obj.data.shape_keys.key_blocks][1:]
        frame += step
    return data