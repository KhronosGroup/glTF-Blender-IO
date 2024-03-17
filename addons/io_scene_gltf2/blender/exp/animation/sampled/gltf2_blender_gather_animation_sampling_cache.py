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
import typing
from .....blender.com.gltf2_blender_data_path import get_sk_exported
from .....blender.com.gltf2_blender_conversion import inverted_trs_mapping_node, texture_transform_blender_to_gltf, yvof_blender_to_gltf
from ...gltf2_blender_gather_cache import datacache
from ...gltf2_blender_gather_tree import VExportNode
from ..gltf2_blender_gather_drivers import get_sk_drivers

# Warning : If you change some parameter here, need to be changed in cache system
@datacache
def get_cache_data(path: str,
                      blender_obj_uuid: str,
                      bone: typing.Optional[str],
                      action_name: str,
                      current_frame: int,
                      step: int,
                      export_settings,
                      only_gather_provided=False
                    ):

    data = {}

    min_, max_ = get_range(blender_obj_uuid, action_name, export_settings)

    if only_gather_provided:
        obj_uuids = [blender_obj_uuid] if blender_obj_uuid in export_settings['vtree'].nodes.keys() else [] #If object is not in vtree, this is a material or light for pointers
    else:
        obj_uuids = [uid for (uid, n) in export_settings['vtree'].nodes.items() if n.blender_type not in [VExportNode.BONE]]

    # For TRACK mode, we reset cache after each track export, so we don't need to keep others objects
    if export_settings['gltf_animation_mode'] in "NLA_TRACKS":
        obj_uuids = [blender_obj_uuid]  if blender_obj_uuid in export_settings['vtree'].nodes.keys() else [] #If object is not in vtree, this is a material or light for pointers

    # If there is only 1 object to cache, we can disable viewport for other objects (for performance)
    # This can be on these cases:
    # - TRACK mode
    # - Only one object to cache (but here, no really useful for performance)
    # - Action mode, where some object have multiple actions
        # - For this case, on first call, we will cache active action for all objects
        # - On next calls, we will cache only the action of current object, so we can disable viewport for others
    # For armature : We already checked that we can disable viewport (in case of drivers, this is currently not possible)

    need_to_enable_again = False
    if export_settings['gltf_optimize_armature_disable_viewport'] is True and len(obj_uuids) == 1:
        need_to_enable_again = True
        # Before baking, disabling from viewport all meshes
        for obj in [n.blender_object for n in export_settings['vtree'].nodes.values() if n.blender_type in
                    [VExportNode.OBJECT, VExportNode.ARMATURE, VExportNode.COLLECTION]]:
            if obj is None:
                continue
            obj.hide_viewport = True
        export_settings['vtree'].nodes[obj_uuids[0]].blender_object.hide_viewport = False


    depsgraph = bpy.context.evaluated_depsgraph_get()

    frame = min_
    while frame <= max_:
        bpy.context.scene.frame_set(int(frame))
        current_instance = {} # For GN instances, we are going to track instances by their order in instance iterator

        for obj_uuid in obj_uuids:
            blender_obj = export_settings['vtree'].nodes[obj_uuid].blender_object
            if blender_obj is None: #GN instance
                if export_settings['vtree'].nodes[obj_uuid].parent_uuid not in current_instance.keys():
                    current_instance[export_settings['vtree'].nodes[obj_uuid].parent_uuid] = 0

            # TODO: we may want to avoid looping on all objects, but an accurate filter must be found

            # calculate local matrix
            if export_settings['vtree'].nodes[obj_uuid].parent_uuid is None:
                parent_mat = mathutils.Matrix.Identity(4).freeze()
            else:
                if export_settings['vtree'].nodes[export_settings['vtree'].nodes[obj_uuid].parent_uuid].blender_type not in [VExportNode.BONE]:
                    if export_settings['vtree'].nodes[export_settings['vtree'].nodes[obj_uuid].parent_uuid].blender_type != VExportNode.COLLECTION:
                        parent_mat = export_settings['vtree'].nodes[export_settings['vtree'].nodes[obj_uuid].parent_uuid].blender_object.matrix_world
                    else:
                        parent_mat = export_settings['vtree'].nodes[export_settings['vtree'].nodes[obj_uuid].parent_uuid].matrix_world
                else:
                    # Object animated is parented to a bone
                    blender_bone = export_settings['vtree'].nodes[export_settings['vtree'].nodes[obj_uuid].parent_bone_uuid].blender_bone
                    armature_object = export_settings['vtree'].nodes[export_settings['vtree'].nodes[export_settings['vtree'].nodes[obj_uuid].parent_bone_uuid].armature].blender_object
                    axis_basis_change = mathutils.Matrix(
                        ((1.0, 0.0, 0.0, 0.0), (0.0, 0.0, 1.0, 0.0), (0.0, -1.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0)))

                    parent_mat = armature_object.matrix_world @ blender_bone.matrix @ axis_basis_change

            #For object inside collection (at root), matrix world is already expressed regarding collection parent
            if export_settings['vtree'].nodes[obj_uuid].parent_uuid is not None and export_settings['vtree'].nodes[export_settings['vtree'].nodes[obj_uuid].parent_uuid].blender_type == VExportNode.INST_COLLECTION:
                parent_mat = mathutils.Matrix.Identity(4).freeze()

            if blender_obj:
                if export_settings['vtree'].nodes[obj_uuid].blender_type != VExportNode.COLLECTION:
                    mat = parent_mat.inverted_safe() @ blender_obj.matrix_world
                else:
                    mat = parent_mat.inverted_safe()
            else:
                eval = export_settings['vtree'].nodes[export_settings['vtree'].nodes[obj_uuid].parent_uuid].blender_object.evaluated_get(depsgraph)
                cpt_inst = 0
                for inst in depsgraph.object_instances: # use only as iterator
                    if inst.parent == eval:
                        if current_instance[export_settings['vtree'].nodes[obj_uuid].parent_uuid] == cpt_inst:
                            mat = inst.matrix_world.copy()
                            current_instance[export_settings['vtree'].nodes[obj_uuid].parent_uuid] += 1
                            break
                        cpt_inst += 1


            if obj_uuid not in data.keys():
                data[obj_uuid] = {}

            if export_settings['vtree'].nodes[obj_uuid].blender_type != VExportNode.COLLECTION:
                if blender_obj and blender_obj.animation_data and blender_obj.animation_data.action \
                        and export_settings['gltf_animation_mode'] in ["ACTIVE_ACTIONS", "ACTIONS", "BROADCAST"]:
                    if blender_obj.animation_data.action.name not in data[obj_uuid].keys():
                        data[obj_uuid][blender_obj.animation_data.action.name] = {}
                        data[obj_uuid][blender_obj.animation_data.action.name]['matrix'] = {}
                        data[obj_uuid][blender_obj.animation_data.action.name]['matrix'][None] = {}
                    data[obj_uuid][blender_obj.animation_data.action.name]['matrix'][None][frame] = mat
                elif export_settings['gltf_animation_mode'] in ["NLA_TRACKS"]:
                    if action_name not in data[obj_uuid].keys():
                        data[obj_uuid][action_name] = {}
                        data[obj_uuid][action_name]['matrix'] = {}
                        data[obj_uuid][action_name]['matrix'][None] = {}
                    data[obj_uuid][action_name]['matrix'][None][frame] = mat
                else:
                    # case of baking object.
                    # There is no animation, so use uuid of object as key
                    if obj_uuid not in data[obj_uuid].keys():
                        data[obj_uuid][obj_uuid] = {}
                        data[obj_uuid][obj_uuid]['matrix'] = {}
                        data[obj_uuid][obj_uuid]['matrix'][None] = {}
                    data[obj_uuid][obj_uuid]['matrix'][None][frame] = mat
            else:
                if obj_uuid not in data[obj_uuid].keys():
                    data[obj_uuid][obj_uuid] = {}
                    data[obj_uuid][obj_uuid]['matrix'] = {}
                    data[obj_uuid][obj_uuid]['matrix'][None] = {}
                data[obj_uuid][obj_uuid]['matrix'][None][frame] = mat

            # Store data for all bones, if object is an armature
            if blender_obj and blender_obj.type == "ARMATURE":
                bones = export_settings['vtree'].get_all_bones(obj_uuid)
                if blender_obj.animation_data and blender_obj.animation_data.action \
                        and export_settings['gltf_animation_mode'] in ["ACTIVE_ACTIONS", "ACTIONS", "BROADCAST"]:
                    if 'bone' not in data[obj_uuid][blender_obj.animation_data.action.name].keys():
                        data[obj_uuid][blender_obj.animation_data.action.name]['bone'] = {}
                elif blender_obj.animation_data \
                        and export_settings['gltf_animation_mode'] in ["NLA_TRACKS"]:
                    if 'bone' not in data[obj_uuid][action_name].keys():
                        data[obj_uuid][action_name]['bone'] = {}
                else:
                    if 'bone' not in data[obj_uuid][obj_uuid].keys():
                        data[obj_uuid][obj_uuid]['bone'] = {}

                for bone_uuid in [bone for bone in bones if export_settings['vtree'].nodes[bone].leaf_reference is None]:
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

                        # Because there is no armature object, we need to apply the TRS of armature to the root bone
                        if export_settings['gltf_armature_object_remove'] is True:
                            matrix = matrix @ blender_obj.matrix_world

                    if blender_obj.animation_data and blender_obj.animation_data.action \
                            and export_settings['gltf_animation_mode'] in ["ACTIVE_ACTIONS", "ACTIONS", "BROADCAST"]:
                        if blender_bone.name not in data[obj_uuid][blender_obj.animation_data.action.name]['bone'].keys():
                            data[obj_uuid][blender_obj.animation_data.action.name]['bone'][blender_bone.name] = {}
                        data[obj_uuid][blender_obj.animation_data.action.name]['bone'][blender_bone.name][frame] = matrix
                    elif blender_obj.animation_data \
                            and export_settings['gltf_animation_mode'] in ["NLA_TRACKS"]:
                        if blender_bone.name not in data[obj_uuid][action_name]['bone'].keys():
                            data[obj_uuid][action_name]['bone'][blender_bone.name] = {}
                        data[obj_uuid][action_name]['bone'][blender_bone.name][frame] = matrix
                    else:
                        # case of baking object.
                        # There is no animation, so use uuid of object as key
                        if blender_bone.name not in data[obj_uuid][obj_uuid]['bone'].keys():
                            data[obj_uuid][obj_uuid]['bone'][blender_bone.name] = {}
                        data[obj_uuid][obj_uuid]['bone'][blender_bone.name][frame] = matrix

            elif blender_obj is None: # GN instances
                # case of baking object, for GN instances
                # There is no animation, so use uuid of object as key
                if obj_uuid not in data[obj_uuid].keys():
                    data[obj_uuid][obj_uuid] = {}
                    data[obj_uuid][obj_uuid]['matrix'] = {}
                    data[obj_uuid][obj_uuid]['matrix'][None] = {}
                data[obj_uuid][obj_uuid]['matrix'][None][frame] = mat

            # Check SK animation here, as we are caching data
            # This will avoid to have to do it again when exporting SK animation
            if export_settings['gltf_morph_anim'] and blender_obj and blender_obj.type == "MESH" \
            and blender_obj.data is not None \
            and blender_obj.data.shape_keys is not None \
            and blender_obj.data.shape_keys.animation_data is not None \
            and blender_obj.data.shape_keys.animation_data.action is not None \
            and export_settings['gltf_animation_mode'] in ["ACTIVE_ACTIONS", "ACTIONS", "BROADCAST"]:

                if blender_obj.data.shape_keys.animation_data.action.name not in data[obj_uuid].keys():
                    data[obj_uuid][blender_obj.data.shape_keys.animation_data.action.name] = {}
                    data[obj_uuid][blender_obj.data.shape_keys.animation_data.action.name]['sk'] = {}
                    data[obj_uuid][blender_obj.data.shape_keys.animation_data.action.name]['sk'][None] = {}
                data[obj_uuid][blender_obj.data.shape_keys.animation_data.action.name]['sk'][None][frame] = [k.value for k in get_sk_exported(blender_obj.data.shape_keys.key_blocks)]

            elif export_settings['gltf_morph_anim'] and blender_obj and blender_obj.type == "MESH" \
            and blender_obj.data is not None \
            and blender_obj.data.shape_keys is not None \
            and blender_obj.data.shape_keys.animation_data is not None \
            and export_settings['gltf_animation_mode'] in ["NLA_TRACKS"]:

                if action_name not in data[obj_uuid].keys():
                    data[obj_uuid][action_name] = {}
                    data[obj_uuid][action_name]['sk'] = {}
                    data[obj_uuid][action_name]['sk'][None] = {}
                if 'sk' not in data[obj_uuid][action_name].keys():
                    data[obj_uuid][action_name]['sk'] = {}
                    data[obj_uuid][action_name]['sk'][None] = {}
                data[obj_uuid][action_name]['sk'][None][frame] = [k.value for k in get_sk_exported(blender_obj.data.shape_keys.key_blocks)]



            elif export_settings['gltf_morph_anim'] and blender_obj and blender_obj.type == "MESH" \
                    and blender_obj.data is not None \
                    and blender_obj.data.shape_keys is not None:
                if obj_uuid not in data[obj_uuid].keys():
                    data[obj_uuid][obj_uuid] = {}
                    data[obj_uuid][obj_uuid]['sk'] = {}
                    data[obj_uuid][obj_uuid]['sk'][None] = {}
                elif 'sk' not in data[obj_uuid][obj_uuid].keys():
                    data[obj_uuid][obj_uuid]['sk'] = {}
                    data[obj_uuid][obj_uuid]['sk'][None] = {}
                data[obj_uuid][obj_uuid]['sk'][None][frame] = [k.value for k in get_sk_exported(blender_obj.data.shape_keys.key_blocks)]

            # caching driver sk meshes
            # This will avoid to have to do it again when exporting SK animation
            if blender_obj and blender_obj.type == "ARMATURE":
                sk_drivers = get_sk_drivers(obj_uuid, export_settings)
                for dr_obj in sk_drivers:
                    driver_object = export_settings['vtree'].nodes[dr_obj].blender_object
                    if dr_obj not in data.keys():
                        data[dr_obj] = {}
                    if blender_obj.animation_data and blender_obj.animation_data.action \
                            and export_settings['gltf_animation_mode'] in ["ACTIVE_ACTIONS", "ACTIONS", "BROADCAST"]:
                        if obj_uuid + "_" + blender_obj.animation_data.action.name not in data[dr_obj]: # Using uuid of armature + armature animation name as animation name
                            data[dr_obj][obj_uuid + "_" + blender_obj.animation_data.action.name] = {}
                            data[dr_obj][obj_uuid + "_" + blender_obj.animation_data.action.name]['sk'] = {}
                            data[dr_obj][obj_uuid + "_" + blender_obj.animation_data.action.name]['sk'][None] = {}
                        data[dr_obj][obj_uuid + "_" + blender_obj.animation_data.action.name]['sk'][None][frame] = [k.value for k in get_sk_exported(driver_object.data.shape_keys.key_blocks)]
                    if blender_obj.animation_data \
                            and export_settings['gltf_animation_mode'] in ["NLA_TRACKS"]:
                        if obj_uuid + "_" + action_name not in data[dr_obj]:
                            data[dr_obj][obj_uuid + "_" + action_name] = {}
                            data[dr_obj][obj_uuid + "_" + action_name]['sk'] = {}
                            data[dr_obj][obj_uuid + "_" + action_name]['sk'][None] = {}
                        data[dr_obj][obj_uuid + "_" + action_name]['sk'][None][frame] = [k.value for k in get_sk_exported(driver_object.data.shape_keys.key_blocks)]
                    else:
                        if obj_uuid + "_" + obj_uuid not in data[dr_obj]:
                            data[dr_obj][obj_uuid + "_" + obj_uuid] = {}
                            data[dr_obj][obj_uuid + "_" + obj_uuid]['sk'] = {}
                            data[dr_obj][obj_uuid + "_" + obj_uuid]['sk'][None] = {}
                        data[dr_obj][obj_uuid + "_" + obj_uuid]['sk'][None][frame] = [k.value for k in get_sk_exported(driver_object.data.shape_keys.key_blocks)]

        # After caching objects, caching materials, for KHR_animation_pointer
        for mat in export_settings['KHR_animation_pointer']['materials'].keys():
            if len(export_settings['KHR_animation_pointer']['materials'][mat]['paths']) == 0:
                continue

            blender_material = [m for m in bpy.data.materials if id(m) == mat]
            if len(blender_material) == 0:
                # This is not a material from Blender (coming from Geometry Node for example, so no animation on it)
                continue
            else:
                blender_material = blender_material[0]
            if mat not in data.keys():
                data[mat] = {}

            if blender_material.node_tree and blender_material.node_tree.animation_data and blender_material.node_tree.animation_data.action \
                    and export_settings['gltf_animation_mode'] in ["ACTIVE_ACTIONS", "ACTIONS"]:

                if blender_material.node_tree.animation_data.action.name not in data[mat].keys():
                    data[mat][blender_material.node_tree.animation_data.action.name] = {}
                    data[mat][blender_material.node_tree.animation_data.action.name]['value'] = {}
                    for path in export_settings['KHR_animation_pointer']['materials'][mat]['paths'].keys():
                        data[mat][blender_material.node_tree.animation_data.action.name]['value'][path] = {}


                baseColorFactor_alpha_merged_already_done = False
                for path in export_settings['KHR_animation_pointer']['materials'][mat]['paths'].keys():

                    if not path.startswith("node_tree"):
                        continue

                    # Manage special case where we merge baseColorFactor and alpha
                    if export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['path'] == "/materials/XXX/pbrMetallicRoughness/baseColorFactor" \
                            and export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['length'] == 3:
                        if baseColorFactor_alpha_merged_already_done is True:
                            continue
                        val_color = blender_material.path_resolve(path)
                        data_color = list(val_color)[:3]
                        if export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['additional_path'] is not None:
                            val_alpha = blender_material.path_resolve(export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['additional_path'])
                        else:
                            val_alpha = 1.0
                        data[mat][blender_material.node_tree.animation_data.action.name]['value'][path][frame] = data_color + [val_alpha]
                        baseColorFactor_alpha_merged_already_done = True
                    # Manage special case where we merge baseColorFactor and alpha
                    elif export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['path'] == "/materials/XXX/pbrMetallicRoughness/baseColorFactor" \
                            and export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['length'] == 1:
                        if baseColorFactor_alpha_merged_already_done is True:
                            continue
                        val_alpha = blender_material.path_resolve(path)
                        if export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['additional_path'] is not None:
                            val_color = blender_material.path_resolve(export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['additional_path'])
                            data_color = list(val_color)[:3]
                        else:
                            data_color = [1.0, 1.0, 1.0]
                        data[mat][blender_material.node_tree.animation_data.action.name]['value'][path][frame] = data_color + [val_alpha]
                        baseColorFactor_alpha_merged_already_done = True

                    elif "KHR_texture_transform" in export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['path'] \
                            and export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['path'].endswith("offset"):


                        val_offset = blender_material.path_resolve(path)
                        rotation_path = [i for i in export_settings['KHR_animation_pointer']['materials'][mat]['paths'].keys() \
                                                if export_settings['KHR_animation_pointer']['materials'][mat]['paths'][i]['path'].rsplit("/", 1)[0] == export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['path'].rsplit("/", 1)[0] \
                                                    and export_settings['KHR_animation_pointer']['materials'][mat]['paths'][i]['path'].rsplit("/", 1)[1] == "rotation"][0]
                        val_rotation = blender_material.path_resolve(rotation_path)
                        scale_path = [i for i in export_settings['KHR_animation_pointer']['materials'][mat]['paths'].keys() \
                                                if export_settings['KHR_animation_pointer']['materials'][mat]['paths'][i]['path'].rsplit("/", 1)[0] == export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['path'].rsplit("/", 1)[0] \
                                                    and export_settings['KHR_animation_pointer']['materials'][mat]['paths'][i]['path'].rsplit("/", 1)[1] == "scale"][0]
                        val_scale = blender_material.path_resolve(scale_path)

                        mapping_transform = {}
                        mapping_transform["offset"] = [val_offset[0], val_offset[1]]
                        mapping_transform["rotation"] = val_rotation
                        mapping_transform["scale"] = [val_scale[0], val_scale[1]]

                        if export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['vector_type'] == "TEXTURE":
                            mapping_transform = inverted_trs_mapping_node(mapping_transform)
                            if mapping_transform is None:
                                # Can not be converted to TRS, so ... keeping default values
                                export_settings['log'].warning("Can not convert texture transform to TRS. Keeping default values.")
                                mapping_transform = {}
                                mapping_transform["offset"] = [0.0, 0.0]
                                mapping_transform["rotation"] = 0.0
                                mapping_transform["scale"] = [1.0, 1.0]
                        elif export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['vector_type'] == "VECTOR":
                            # Vectors don't get translated
                            mapping_transform["offset"] = [0, 0]

                        texture_transform = texture_transform_blender_to_gltf(mapping_transform)


                        data[mat][blender_material.node_tree.animation_data.action.name]['value'][path][frame] = texture_transform['offset']
                        data[mat][blender_material.node_tree.animation_data.action.name]['value'][rotation_path][frame] = texture_transform['rotation']
                        data[mat][blender_material.node_tree.animation_data.action.name]['value'][scale_path][frame] = texture_transform['scale']
                    elif "KHR_texture_transform" in export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['path'] \
                            and export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['path'].endswith("rotation"):
                        if export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['vector_type'] != "VECTOR":
                            # Already handled by offset
                            continue
                        else:
                            val = blender_material.path_resolve(path)
                            mapping_transform = {}
                            mapping_transform["offset"] = [0,0] # Placeholder, not needed
                            mapping_transform["rotation"] = val
                            mapping_transform["scale"] = [1, 1] # Placeholder, not needed
                            texture_transform = texture_transform_blender_to_gltf(mapping_transform)
                            data[mat][blender_material.node_tree.animation_data.action.name]['value'][path][frame] = texture_transform['rotation']
                    elif "KHR_texture_transform" in export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['path'] \
                            and export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['path'].endswith("scale"):
                        if export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['vector_type'] != "VECTOR":
                            # Already handled by offset
                            continue
                        else:
                            val = blender_material.path_resolve(path)
                            mapping_transform = {}
                            mapping_transform["offset"] = [0,0] # Placeholder, not needed
                            mapping_transform["rotation"] = 0.0 # Placeholder, not needed
                            mapping_transform["scale"] = [val[0], val[1]]
                            texture_transform = texture_transform_blender_to_gltf(mapping_transform)
                            data[mat][blender_material.node_tree.animation_data.action.name]['value'][path][frame] = texture_transform['rotation']

                    # Manage special cases for specularFactor & specularColorFactor
                    elif export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['path'] == "/materials/XXX/extensions/KHR_materials_specular/specularFactor":
                        val = blender_material.path_resolve(path)
                        val = val * 2.0
                        if val > 1.0:
                            fac = val
                            val = 1.0
                        else:
                            fac = 1.0

                        data[mat][blender_material.node_tree.animation_data.action.name]['value'][path][frame] = val

                        # Retrieve specularColorFactor
                        colorfactor_path = [i for i in export_settings['KHR_animation_pointer']['materials'][mat]['paths'].keys() \
                                                if export_settings['KHR_animation_pointer']['materials'][mat]['paths'][i]['path'].rsplit("/", 1)[0] == export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['path'].rsplit("/", 1)[0] \
                                                    and export_settings['KHR_animation_pointer']['materials'][mat]['paths'][i]['path'].rsplit("/", 1)[1] == "specularColorFactor"][0]
                        val_colorfactor = blender_material.path_resolve(colorfactor_path)
                        if fac > 1.0:
                            val_colorfactor = [i * fac for i in val_colorfactor]
                        data[mat][blender_material.node_tree.animation_data.action.name]['value'][colorfactor_path][frame] = val_colorfactor
                    elif export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['path'] == "/materials/XXX/extensions/KHR_materials_specular/specularColorFactor":
                        # Already handled by specularFactor
                        continue


                    # Classic case
                    else:
                        val = blender_material.path_resolve(path)
                        if type(val).__name__ == "float":
                            data[mat][blender_material.node_tree.animation_data.action.name]['value'][path][frame] = val
                        else:
                            data[mat][blender_material.node_tree.animation_data.action.name]['value'][path][frame] = list(val)

            elif export_settings['gltf_animation_mode'] in ["NLA_TRACKS"]:
                if action_name not in data[mat].keys():
                    data[mat][action_name] = {}
                    data[mat][action_name]['value'] = {}
                    for path in export_settings['KHR_animation_pointer']['materials'][mat]['paths'].keys():
                        data[mat][action_name]['value'][path] = {}

                baseColorFactor_alpha_merged_already_done = False
                for path in export_settings['KHR_animation_pointer']['materials'][mat]['paths'].keys():

                    if not path.startswith("node_tree"):
                        continue

                    # Manage special case where we merge baseColorFactor and alpha
                    if export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['path'] == "/materials/XXX/pbrMetallicRoughness/baseColorFactor" \
                            and export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['length'] == 3:
                        if baseColorFactor_alpha_merged_already_done is True:
                            continue
                        val_color = blender_material.path_resolve(path)
                        data_color = list(val_color)[:3]
                        if export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['additional_path'] is not None:
                            val_alpha = blender_material.path_resolve(export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['additional_path'])
                        else:
                            val_alpha = 1.0
                        data[mat][action_name]['value'][path][frame] = data_color + [val_alpha]
                        baseColorFactor_alpha_merged_already_done = True
                    # Manage special case where we merge baseColorFactor and alpha
                    elif export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['path'] == "/materials/XXX/pbrMetallicRoughness/baseColorFactor" \
                            and export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['length'] == 1:
                        if baseColorFactor_alpha_merged_already_done is True:
                            continue
                        val_alpha = blender_material.path_resolve(path)
                        if export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['additional_path'] is not None:
                            val_color = blender_material.path_resolve(export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['additional_path'])
                            data_color = list(val_color)[:export_settings['KHR_animation_pointer']['materials'][mat]['paths']['additional_path']['length']]
                        else:
                            data_color = [1.0, 1.0, 1.0]
                        data[mat][action_name]['value'][path][frame] = data_color + [val_alpha]
                        baseColorFactor_alpha_merged_already_done = True

                    elif "KHR_texture_transform" in export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['path'] \
                            and export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['path'].endswith("offset"):


                        val_offset = blender_material.path_resolve(path)
                        rotation_path = [i for i in export_settings['KHR_animation_pointer']['materials'][mat]['paths'].keys() \
                                                if export_settings['KHR_animation_pointer']['materials'][mat]['paths'][i]['path'].rsplit("/", 1)[0] == export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['path'].rsplit("/", 1)[0] \
                                                    and export_settings['KHR_animation_pointer']['materials'][mat]['paths'][i]['path'].rsplit("/", 1)[1] == "rotation"][0]
                        val_rotation = blender_material.path_resolve(rotation_path)
                        scale_path = [i for i in export_settings['KHR_animation_pointer']['materials'][mat]['paths'].keys() \
                                                if export_settings['KHR_animation_pointer']['materials'][mat]['paths'][i]['path'].rsplit("/", 1)[0] == export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['path'].rsplit("/", 1)[0] \
                                                    and export_settings['KHR_animation_pointer']['materials'][mat]['paths'][i]['path'].rsplit("/", 1)[1] == "scale"][0]
                        val_scale = blender_material.path_resolve(scale_path)

                        mapping_transform = {}
                        mapping_transform["offset"] = [val_offset[0], val_offset[1]]
                        mapping_transform["rotation"] = val_rotation
                        mapping_transform["scale"] = [val_scale[0], val_scale[1]]

                        if export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['vector_type'] == "TEXTURE":
                            mapping_transform = inverted_trs_mapping_node(mapping_transform)
                            if mapping_transform is None:
                                # Can not be converted to TRS, so ... keeping default values
                                export_settings['log'].warning("Can not convert texture transform to TRS. Keeping default values.")
                                mapping_transform = {}
                                mapping_transform["offset"] = [0.0, 0.0]
                                mapping_transform["rotation"] = 0.0
                                mapping_transform["scale"] = [1.0, 1.0]
                        elif export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['vector_type'] == "VECTOR":
                            # Vectors don't get translated
                            mapping_transform["offset"] = [0, 0]

                        texture_transform = texture_transform_blender_to_gltf(mapping_transform)


                        data[mat][action_name]['value'][path][frame] = texture_transform['offset']
                        data[mat][action_name]['value'][rotation_path][frame] = texture_transform['rotation']
                        data[mat][action_name]['value'][scale_path][frame] = texture_transform['scale']
                    elif "KHR_texture_transform" in export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['path'] \
                            and export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['path'].endswith("rotation"):
                        if export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['vector_type'] != "VECTOR":
                            # Already handled by offset
                            continue
                        else:
                            val = blender_material.path_resolve(path)
                            mapping_transform = {}
                            mapping_transform["offset"] = [0,0] # Placeholder, not needed
                            mapping_transform["rotation"] = val
                            mapping_transform["scale"] = [1, 1] # Placeholder, not needed
                            texture_transform = texture_transform_blender_to_gltf(mapping_transform)
                            data[mat][action_name]['value'][path][frame] = texture_transform['rotation']
                    elif "KHR_texture_transform" in export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['path'] \
                            and export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['path'].endswith("scale"):
                        if export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['vector_type'] != "VECTOR":
                            # Already handled by offset
                            continue
                        else:
                            val = blender_material.path_resolve(path)
                            mapping_transform = {}
                            mapping_transform["offset"] = [0,0] # Placeholder, not needed
                            mapping_transform["rotation"] = 0.0 # Placeholder, not needed
                            mapping_transform["scale"] = [val[0], val[1]]
                            texture_transform = texture_transform_blender_to_gltf(mapping_transform)
                            data[mat][action_name]['value'][path][frame] = texture_transform['rotation']

                    # Manage special cases for specularFactor & specularColorFactor
                    elif export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['path'] == "/materials/XXX/extensions/KHR_materials_specular/specularFactor":
                        val = blender_material.path_resolve(path)
                        val = val * 2.0
                        if val > 1.0:
                            fac = val
                            val = 1.0
                        else:
                            fac = 1.0

                        data[mat][action_name]['value'][path][frame] = val

                        # Retrieve specularColorFactor
                        colorfactor_path = [i for i in export_settings['KHR_animation_pointer']['materials'][mat]['paths'].keys() \
                                                if export_settings['KHR_animation_pointer']['materials'][mat]['paths'][i]['path'].rsplit("/", 1)[0] == export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['path'].rsplit("/", 1)[0] \
                                                    and export_settings['KHR_animation_pointer']['materials'][mat]['paths'][i]['path'].rsplit("/", 1)[1] == "specularColorFactor"][0]
                        val_colorfactor = blender_material.path_resolve(colorfactor_path)
                        if fac > 1.0:
                            val_colorfactor = [i * fac for i in val_colorfactor]
                        data[mat][action_name]['value'][colorfactor_path][frame] = val_colorfactor
                    elif export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['path'] == "/materials/XXX/extensions/KHR_materials_specular/specularColorFactor":
                        # Already handled by specularFactor
                        continue

                    # Classic case
                    else:
                        val = blender_material.path_resolve(path)
                        if type(val).__name__ == "float":
                            data[mat][action_name]['value'][path][frame] = val
                        else:
                            data[mat][action_name]['value'][path][frame] = list(val)
            else:
                # case of baking materials (scene export).
                # There is no animation, so use id as key
                if mat not in data[mat].keys():
                    data[mat][mat] = {}
                    data[mat][mat]['value'] = {}
                    for path in export_settings['KHR_animation_pointer']['materials'][mat]['paths'].keys():
                        data[mat][mat]['value'][path] = {}

                baseColorFactor_alpha_merged_already_done = False
                for path in export_settings['KHR_animation_pointer']['materials'][mat]['paths'].keys():

                    if not path.startswith("node_tree"):
                        continue

                    # Manage special case where we merge baseColorFactor and alpha
                    if export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['path'] == "/materials/XXX/pbrMetallicRoughness/baseColorFactor" \
                            and export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['length'] == 3:
                        if baseColorFactor_alpha_merged_already_done is True:
                            continue
                        val_color = blender_material.path_resolve(path)
                        data_color = list(val_color)[:export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['length']]
                        if export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['additional_path'] is not None:
                            val_alpha = blender_material.path_resolve(export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['additional_path'])
                        else:
                            val_alpha = 1.0
                        data[mat][mat]['value'][path][frame] = data_color + [val_alpha]
                        baseColorFactor_alpha_merged_already_done = True
                    # Manage special case where we merge baseColorFactor and alpha
                    elif export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['path'] == "/materials/XXX/pbrMetallicRoughness/baseColorFactor" \
                            and export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['length'] == 1:
                        if baseColorFactor_alpha_merged_already_done is True:
                            continue
                        val_alpha = blender_material.path_resolve(path)
                        if export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['additional_path'] is not None:
                            val_color = blender_material.path_resolve(export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['additional_path'])
                            data_color = list(val_color)[:export_settings['KHR_animation_pointer']['materials'][mat]['paths']['additional_path']['length']]
                        else:
                            data_color = [1.0, 1.0, 1.0]
                        data[mat][mat]['value'][path][frame] = data_color + [val_alpha]
                        baseColorFactor_alpha_merged_already_done = True

                    # Manage special case for KHR_texture_transform offset, that needs rotation and scale too (and not only translation)
                    elif "KHR_texture_transform" in export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['path'] \
                            and export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['path'].endswith("offset"):

                        val_offset = blender_material.path_resolve(path)
                        rotation_path = [i for i in export_settings['KHR_animation_pointer']['materials'][mat]['paths'].keys() \
                                                if export_settings['KHR_animation_pointer']['materials'][mat]['paths'][i]['path'].rsplit("/", 1)[0] == export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['path'].rsplit("/", 1)[0] \
                                                    and export_settings['KHR_animation_pointer']['materials'][mat]['paths'][i]['path'].rsplit("/", 1)[1] == "rotation"][0]
                        val_rotation = blender_material.path_resolve(rotation_path)
                        scale_path = [i for i in export_settings['KHR_animation_pointer']['materials'][mat]['paths'].keys() \
                                                if export_settings['KHR_animation_pointer']['materials'][mat]['paths'][i]['path'].rsplit("/", 1)[0] == export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['path'].rsplit("/", 1)[0] \
                                                    and export_settings['KHR_animation_pointer']['materials'][mat]['paths'][i]['path'].rsplit("/", 1)[1] == "scale"][0]
                        val_scale = blender_material.path_resolve(scale_path)

                        mapping_transform = {}
                        mapping_transform["offset"] = [val_offset[0], val_offset[1]]
                        mapping_transform["rotation"] = val_rotation
                        mapping_transform["scale"] = [val_scale[0], val_scale[1]]

                        if export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['vector_type'] == "TEXTURE":
                            mapping_transform = inverted_trs_mapping_node(mapping_transform)
                            if mapping_transform is None:
                                # Can not be converted to TRS, so ... keeping default values
                                export_settings['log'].warning("Can not convert texture transform to TRS. Keeping default values.")
                                mapping_transform = {}
                                mapping_transform["offset"] = [0.0, 0.0]
                                mapping_transform["rotation"] = 0.0
                                mapping_transform["scale"] = [1.0, 1.0]
                        elif export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['vector_type'] == "VECTOR":
                            # Vectors don't get translated
                            mapping_transform["offset"] = [0, 0]

                        texture_transform = texture_transform_blender_to_gltf(mapping_transform)


                        data[mat][mat]['value'][path][frame] = texture_transform['offset']
                        data[mat][mat]['value'][rotation_path][frame] = texture_transform['rotation']
                        data[mat][mat]['value'][scale_path][frame] = texture_transform['scale']
                        if export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['vector_type'] != "VECTOR":
                            # Already handled by offset
                            continue
                        else:
                            val = blender_material.path_resolve(path)
                            mapping_transform = {}
                            mapping_transform["offset"] = [0,0] # Placeholder, not needed
                            mapping_transform["rotation"] = val
                            mapping_transform["scale"] = [1, 1] # Placeholder, not needed
                            texture_transform = texture_transform_blender_to_gltf(mapping_transform)
                            data[mat][mat]['value'][path][frame] = texture_transform['rotation']
                    elif "KHR_texture_transform" in export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['path'] \
                            and export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['path'].endswith("scale"):
                        if export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['vector_type'] != "VECTOR":
                            # Already handled by offset
                            continue
                        else:
                            val = blender_material.path_resolve(path)
                            mapping_transform = {}
                            mapping_transform["offset"] = [0,0] # Placeholder, not needed
                            mapping_transform["rotation"] = 0.0 # Placeholder, not needed
                            mapping_transform["scale"] = [val[0], val[1]]
                            texture_transform = texture_transform_blender_to_gltf(mapping_transform)
                            data[mat][mat]['value'][path][frame] = texture_transform['rotation']

                    # Manage special cases for specularFactor & specularColorFactor
                    elif export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['path'] == "/materials/XXX/extensions/KHR_materials_specular/specularFactor":
                        val = blender_material.path_resolve(path)
                        val = val * 2.0
                        if val > 1.0:
                            fac = val
                            val = 1.0
                        else:
                            fac = 1.0

                        data[mat][mat]['value'][path][frame] = val

                        # Retrieve specularColorFactor
                        colorfactor_path = [i for i in export_settings['KHR_animation_pointer']['materials'][mat]['paths'].keys() \
                                                if export_settings['KHR_animation_pointer']['materials'][mat]['paths'][i]['path'].rsplit("/", 1)[0] == export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['path'].rsplit("/", 1)[0] \
                                                    and export_settings['KHR_animation_pointer']['materials'][mat]['paths'][i]['path'].rsplit("/", 1)[1] == "specularColorFactor"][0]
                        val_colorfactor = blender_material.path_resolve(colorfactor_path)
                        if fac > 1.0:
                            val_colorfactor = [i * fac for i in val_colorfactor]
                        data[mat][mat]['value'][colorfactor_path][frame] = val_colorfactor
                    elif export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['path'] == "/materials/XXX/extensions/KHR_materials_specular/specularColorFactor":
                        # Already handled by specularFactor
                        continue

                    # Classic case
                    else:
                        val = blender_material.path_resolve(path)
                        if type(val).__name__ == "float":
                            data[mat][mat]['value'][path][frame] = val
                        else:
                            data[mat][mat]['value'][path][frame] = list(val)[:export_settings['KHR_animation_pointer']['materials'][mat]['paths'][path]['length']]


            if blender_material and blender_material.animation_data and blender_material.animation_data.action \
                    and export_settings['gltf_animation_mode'] in ["ACTIVE_ACTIONS", "ACTIONS"]:
                if blender_material.animation_data.action.name not in data[mat].keys():
                    data[mat][blender_material.animation_data.action.name] = {}
                    data[mat][blender_material.animation_data.action.name]['value'] = {}
                    for path in export_settings['KHR_animation_pointer']['materials'][mat]['paths'].keys():
                        data[mat][blender_material.animation_data.action.name]['value'][path] = {}

                for path in export_settings['KHR_animation_pointer']['materials'][mat]['paths'].keys():

                    if path.startswith("node_tree"):
                        continue

                    val = blender_material.path_resolve(path)
                    if type(val).__name__ == "float":
                        data[mat][blender_material.animation_data.action.name]['value'][path][frame] = val
                    else:
                        data[mat][blender_material.animation_data.action.name]['value'][path][frame] = list(val)

            elif export_settings['gltf_animation_mode'] in ["NLA_TRACKS"]:
                if action_name not in data[mat].keys():
                    data[mat][action_name] = {}
                    data[mat][action_name]['value'] = {}
                    for path in export_settings['KHR_animation_pointer']['materials'][mat]['paths'].keys():
                        data[mat][action_name]['value'][path] = {}

                for path in export_settings['KHR_animation_pointer']['materials'][mat]['paths'].keys():

                    if path.startswith("node_tree"):
                        continue

                    val = blender_material.path_resolve(path)
                    if type(val).__name__ == "float":
                        data[mat][action_name]['value'][path][frame] = val
                    else:
                        data[mat][action_name]['value'][path][frame] = list(val)


            else:
                if mat not in data[mat].keys():
                    data[mat][mat] = {}
                    data[mat][mat]['value'] = {}
                    for path in export_settings['KHR_animation_pointer']['materials'][mat]['paths'].keys():
                        data[mat][mat]['value'][path] = {}

                for path in export_settings['KHR_animation_pointer']['materials'][mat]['paths'].keys():

                    if path.startswith("node_tree"):
                        continue

                    val = blender_material.path_resolve(path)
                    if type(val).__name__ == "float":
                        data[mat][mat]['value'][path][frame] = val
                    else:
                        data[mat][mat]['value'][path][frame] = list(val)


        # After caching materials, caching lights, for KHR_animation_pointer
        for light in export_settings['KHR_animation_pointer']['lights'].keys():
            if len(export_settings['KHR_animation_pointer']['lights'][light]['paths']) == 0:
                continue

            blender_light = [m for m in bpy.data.lights if id(m) == light][0]
            if light not in data.keys():
                data[light] = {}

            if blender_light.node_tree and blender_light.node_tree.animation_data and blender_light.node_tree.animation_data.action \
                    and export_settings['gltf_animation_mode'] in ["ACTIVE_ACTIONS", "ACTIONS"]:

                if blender_light.node_tree.animation_data.action.name not in data[light].keys():
                    data[light][blender_light.node_tree.animation_data.action.name] = {}
                    data[light][blender_light.node_tree.animation_data.action.name]['value'] = {}
                    for path in export_settings['KHR_animation_pointer']['lights'][light]['paths'].keys():
                        data[light][blender_light.node_tree.animation_data.action.name]['value'][path] = {}

                for path in export_settings['KHR_animation_pointer']['lights'][light]['paths'].keys():
                    val = blender_light.path_resolve(path)
                    if type(val).__name__ == "float":
                        data[light][blender_light.node_tree.animation_data.action.name]['value'][path][frame] = val
                    else:
                        data[light][blender_light.node_tree.animation_data.action.name]['value'][path][frame] = list(val)

            elif export_settings['gltf_animation_mode'] in ["NLA_TRACKS"]:
                if action_name not in data[light].keys():
                    data[light][action_name] = {}
                    data[light][action_name]['value'] = {}
                    for path in export_settings['KHR_animation_pointer']['lights'][light]['paths'].keys():
                        data[light][action_name]['value'][path] = {}

                for path in export_settings['KHR_animation_pointer']['lights'][light]['paths'].keys():
                    val = blender_light.path_resolve(path)
                    if type(val).__name__ == "float":
                        data[light][action_name]['value'][path][frame] = val
                    else:
                        data[light][action_name]['value'][path][frame] = list(val)
            else:
                # case of baking materials (scene export).
                # There is no animation, so use id as key

                if light not in data[light].keys():
                    data[light][light] = {}
                    data[light][light]['value'] = {}
                    for path in export_settings['KHR_animation_pointer']['lights'][light]['paths'].keys():
                        data[light][light]['value'][path] = {}

                for path in export_settings['KHR_animation_pointer']['lights'][light]['paths'].keys():
                    val = blender_light.path_resolve(path)
                    if type(val).__name__ == "float":
                        data[light][light]['value'][path][frame] = val
                    else:
                        data[light][light]['value'][path][frame] = list(val)

            if blender_light and blender_light.animation_data and blender_light.animation_data.action \
                    and export_settings['gltf_animation_mode'] in ["ACTIVE_ACTIONS", "ACTIONS"]:
                if blender_light.animation_data.action.name not in data[light].keys():
                    data[light][blender_light.animation_data.action.name] = {}
                    data[light][blender_light.animation_data.action.name]['value'] = {}
                    for path in export_settings['KHR_animation_pointer']['lights'][light]['paths'].keys():
                        data[light][blender_light.animation_data.action.name]['value'][path] = {}

                for path in export_settings['KHR_animation_pointer']['lights'][light]['paths'].keys():
                    # Manage special case for innerConeAngle because it requires spot_size & spot_blend
                    if export_settings['KHR_animation_pointer']['lights'][light]['paths'][path]['path'] == "/extensions/KHR_lights_punctual/lights/XXX/spot.innerConeAngle":
                        val = blender_light.path_resolve(path)
                        val_size = blender_light.path_resolve(export_settings['KHR_animation_pointer']['lights'][light]['paths'][path]['additional_path'])
                        data[light][blender_light.animation_data.action.name]['value'][path][frame] = (val_size * 0.5) - ((val_size * 0.5) * val)
                    else:
                        # classic case
                        val = blender_light.path_resolve(path)
                        if type(val).__name__ == "float":
                            data[light][blender_light.animation_data.action.name]['value'][path][frame] = val
                        else:
                            # When color is coming from a node, it is 4 values (RGBA), so need to convert it to 3 values (RGB)
                            if export_settings['KHR_animation_pointer']['lights'][light]['paths'][path]['length'] == 3 and len(val) == 4:
                                val = val[:3]
                            data[light][blender_light.animation_data.action.name]['value'][path][frame] = list(val)

            elif export_settings['gltf_animation_mode'] in ["NLA_TRACKS"]:
                if action_name not in data[light].keys():
                    data[light][action_name] = {}
                    data[light][action_name]['value'] = {}
                    for path in export_settings['KHR_animation_pointer']['lights'][light]['paths'].keys():
                        data[light][action_name]['value'][path] = {}

                for path in export_settings['KHR_animation_pointer']['lights'][light]['paths'].keys():
                    # Manage special case for innerConeAngle because it requires spot_size & spot_blend
                    if export_settings['KHR_animation_pointer']['lights'][light]['paths'][path]['path'] == "/extensions/KHR_lights_punctual/lights/XXX/spot.innerConeAngle":
                        val = blender_light.path_resolve(path)
                        val_size = blender_light.path_resolve(export_settings['KHR_animation_pointer']['lights'][light]['paths'][path]['additional_path'])
                        data[light][action_name]['value'][path][frame] = (val_size * 0.5) - ((val_size * 0.5) * val)
                    else:
                        # classic case
                        val = blender_light.path_resolve(path)
                        if type(val).__name__ == "float":
                            data[light][action_name]['value'][path][frame] = val
                        else:
                            # When color is coming from a node, it is 4 values (RGBA), so need to convert it to 3 values (RGB)
                            if export_settings['KHR_animation_pointer']['lights'][light]['paths'][path]['length'] == 3 and len(val) == 4:
                                val = val[:3]
                            data[light][action_name]['value'][path][frame] = list(val)

            else:
                if light not in data[light].keys():
                    data[light][light] = {}
                    data[light][light]['value'] = {}
                    for path in export_settings['KHR_animation_pointer']['lights'][light]['paths'].keys():
                        data[light][light]['value'][path] = {}

                for path in export_settings['KHR_animation_pointer']['lights'][light]['paths'].keys():
                    # Manage special case for innerConeAngle because it requires spot_size & spot_blend
                    if export_settings['KHR_animation_pointer']['lights'][light]['paths'][path]['path'] == "/extensions/KHR_lights_punctual/lights/XXX/spot.innerConeAngle":
                        val = blender_light.path_resolve(path)
                        val_size = blender_light.path_resolve(export_settings['KHR_animation_pointer']['lights'][light]['paths'][path]['additional_path'])
                        data[light][light]['value'][path][frame] = (val_size * 0.5) - ((val_size * 0.5) * val)
                    else:
                        # classic case
                        val = blender_light.path_resolve(path)
                        if type(val).__name__ == "float":
                            data[light][light]['value'][path][frame] = val
                        else:
                            # When color is coming from a node, it is 4 values (RGBA), so need to convert it to 3 values (RGB)
                            if export_settings['KHR_animation_pointer']['lights'][light]['paths'][path]['length'] == 3 and len(val) == 4:
                                val = val[:3]
                            data[light][light]['value'][path][frame] = list(val)

        # After caching lights, caching cameras, for KHR_animation_pointer
        for cam in export_settings['KHR_animation_pointer']['cameras'].keys():
            if len(export_settings['KHR_animation_pointer']['cameras'][cam]['paths']) == 0:
                continue

            blender_camera = [m for m in bpy.data.cameras if id(m) == cam][0]
            if cam not in data.keys():
                data[cam] = {}

            if blender_camera and blender_camera.animation_data and blender_camera.animation_data.action \
                    and export_settings['gltf_animation_mode'] in ["ACTIVE_ACTIONS", "ACTIONS"]:
                if blender_camera.animation_data.action.name not in data[cam].keys():
                    data[cam][blender_camera.animation_data.action.name] = {}
                    data[cam][blender_camera.animation_data.action.name]['value'] = {}
                    for path in export_settings['KHR_animation_pointer']['cameras'][cam]['paths'].keys():
                        data[cam][blender_camera.animation_data.action.name]['value'][path] = {}

                for path in export_settings['KHR_animation_pointer']['cameras'][cam]['paths'].keys():
                    _render = bpy.context.scene.render
                    width = _render.pixel_aspect_x * _render.resolution_x
                    height = _render.pixel_aspect_y * _render.resolution_y
                    del _render
                    # Manage special case for yvof because it requires sensor_fit, aspect ratio, angle
                    if export_settings['KHR_animation_pointer']['cameras'][cam]['paths'][path]['path'] == "/cameras/XXX/perspective/yfov":
                        val = yvof_blender_to_gltf(blender_camera.angle, width, height, blender_camera.sensor_fit)
                        data[cam][blender_camera.animation_data.action.name]['value'][path][frame] = val
                    # Manage special case for xmag because it requires ortho_scale & scene data
                    elif export_settings['KHR_animation_pointer']['cameras'][cam]['paths'][path]['path'] == "/cameras/XXX/orthographic/xmag":
                        val = blender_camera.ortho_scale
                        data[cam][blender_camera.animation_data.action.name]['value'][path][frame] = val * (width / max(width, height)) / 2.0
                    # Manage special case for ymag because it requires ortho_scale  & scene data
                    elif export_settings['KHR_animation_pointer']['cameras'][cam]['paths'][path]['path'] == "/cameras/XXX/orthographic/ymag":
                        val = blender_camera.ortho_scale
                        data[cam][blender_camera.animation_data.action.name]['value'][path][frame] = val * (height / max(width, height)) / 2.0
                    else:
                        # classic case
                        val = blender_camera.path_resolve(path)
                        if type(val).__name__ == "float":
                            data[cam][blender_camera.animation_data.action.name]['value'][path][frame] = val
                        else:
                            data[cam][blender_camera.animation_data.action.name]['value'][path][frame] = list(val)

            elif export_settings['gltf_animation_mode'] in ["NLA_TRACKS"]:
                if action_name not in data[cam].keys():
                    data[cam][action_name] = {}
                    data[cam][action_name]['value'] = {}
                    for path in export_settings['KHR_animation_pointer']['cameras'][cam]['paths'].keys():
                        data[cam][action_name]['value'][path] = {}

                for path in export_settings['KHR_animation_pointer']['cameras'][cam]['paths'].keys():
                    _render = bpy.context.scene.render
                    width = _render.pixel_aspect_x * _render.resolution_x
                    height = _render.pixel_aspect_y * _render.resolution_y
                    del _render
                    # Manage special case for yvof because it requires sensor_fit, aspect ratio, angle
                    if export_settings['KHR_animation_pointer']['cameras'][cam]['paths'][path]['path'] == "/cameras/XXX/perspective/yfov":
                        val = yvof_blender_to_gltf(blender_camera.angle, width, height, blender_camera.sensor_fit)
                        data[cam][action_name]['value'][path][frame] = val
                    # Manage special case for xmag because it requires ortho_scale & scene data
                    elif export_settings['KHR_animation_pointer']['cameras'][cam]['paths'][path]['path'] == "/cameras/XXX/orthographic/xmag":
                        val = blender_camera.ortho_scale
                        data[cam][action_name]['value'][path][frame] = val * (width / max(width, height)) / 2.0
                    # Manage special case for ymag because it requires ortho_scale  & scene data
                    elif export_settings['KHR_animation_pointer']['cameras'][cam]['paths'][path]['path'] == "/cameras/XXX/orthographic/ymag":
                        val = blender_camera.ortho_scale
                        data[cam][action_name]['value'][path][frame] = val * (height / max(width, height)) / 2.0
                    else:
                        # classic case
                        val = blender_camera.path_resolve(path)
                        if type(val).__name__ == "float":
                            data[cam][action_name]['value'][path][frame] = val
                        else:
                            data[cam][action_name]['value'][path][frame] = list(val)

            else:
                if cam not in data[cam].keys():
                    data[cam][cam] = {}
                    data[cam][cam]['value'] = {}
                    for path in export_settings['KHR_animation_pointer']['cameras'][cam]['paths'].keys():
                        data[cam][cam]['value'][path] = {}

                for path in export_settings['KHR_animation_pointer']['cameras'][cam]['paths'].keys():
                    _render = bpy.context.scene.render
                    width = _render.pixel_aspect_x * _render.resolution_x
                    height = _render.pixel_aspect_y * _render.resolution_y
                    del _render
                    # Manage special case for yvof because it requires sensor_fit, aspect ratio, angle
                    if export_settings['KHR_animation_pointer']['cameras'][cam]['paths'][path]['path'] == "/cameras/XXX/perspective/yfov":
                        val = yvof_blender_to_gltf(blender_camera.angle, width, height, blender_camera.sensor_fit)
                        data[cam][cam]['value'][path][frame] = val
                    # Manage special case for xmag because it requires ortho_scale & scene data
                    elif export_settings['KHR_animation_pointer']['cameras'][cam]['paths'][path]['path'] == "/cameras/XXX/orthographic/xmag":
                        val = blender_camera.ortho_scale
                        data[cam][cam]['value'][path][frame] = val * (width / max(width, height)) / 2.0
                    # Manage special case for ymag because it requires ortho_scale  & scene data
                    elif export_settings['KHR_animation_pointer']['cameras'][cam]['paths'][path]['path'] == "/cameras/XXX/orthographic/ymag":
                        val = blender_camera.ortho_scale
                        data[cam][cam]['value'][path][frame] = val * (height / max(width, height)) / 2.0
                    else:
                        # classic case
                        val = blender_camera.path_resolve(path)
                        if type(val).__name__ == "float":
                            data[cam][cam]['value'][path][frame] = val
                        else:
                            data[cam][cam]['value'][path][frame] = list(val)

        frame += step

    # And now, restoring meshes in viewport
    for node, obj in [(n, n.blender_object) for n in export_settings['vtree'].nodes.values() if n.blender_type in
                [VExportNode.OBJECT, VExportNode.ARMATURE, VExportNode.COLLECTION]]:
        obj.hide_viewport = node.default_hide_viewport
    export_settings['vtree'].nodes[obj_uuids[0]].blender_object.hide_viewport = export_settings['vtree'].nodes[obj_uuids[0]].default_hide_viewport


    return data

# For perf, we may be more precise, and get a list of ranges to be exported that include all needed frames
def get_range(obj_uuid, key, export_settings):
    if export_settings['gltf_animation_mode'] in ["NLA_TRACKS"]:
        return export_settings['ranges'][obj_uuid][key]['start'], export_settings['ranges'][obj_uuid][key]['end']
    else:
        min_ = None
        max_ = None
        for obj in export_settings['ranges'].keys():
            for anim in export_settings['ranges'][obj].keys():
                if min_ is None or min_ > export_settings['ranges'][obj][anim]['start']:
                    min_ = export_settings['ranges'][obj][anim]['start']
                if max_ is None or max_ < export_settings['ranges'][obj][anim]['end']:
                    max_ = export_settings['ranges'][obj][anim]['end']
    return min_, max_
