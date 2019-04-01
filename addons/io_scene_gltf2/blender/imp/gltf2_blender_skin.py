# Copyright 2018 The glTF-Blender-IO authors.
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
from mathutils import Vector, Matrix
from ..com.gltf2_blender_conversion import matrix_gltf_to_blender, scale_to_matrix
from ...io.imp.gltf2_io_binary import BinaryData


class BlenderSkin():
    """Blender Skinning / Armature."""
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("%s should not be instantiated" % cls)

    @staticmethod
    def create_armature(gltf, skin_id, parent):
        """Armature creation."""
        pyskin = gltf.data.skins[skin_id]

        if pyskin.name is not None:
            name = pyskin.name
        else:
            name = "Armature_" + str(skin_id)

        armature = bpy.data.armatures.new(name)
        obj = bpy.data.objects.new(name, armature)
        if bpy.app.version < (2, 80, 0):
            bpy.data.scenes[gltf.blender_scene].objects.link(obj)
        else:
            if gltf.blender_active_collection is not None:
                bpy.data.collections[gltf.blender_active_collection].objects.link(obj)
            else:
                bpy.data.scenes[gltf.blender_scene].collection.objects.link(obj)
                
        pyskin.blender_armature_name = obj.name
        if parent is not None:
            obj.parent = bpy.data.objects[gltf.data.nodes[parent].blender_object]

    @staticmethod
    def set_bone_transforms(gltf, skin_id, bone, node_id, parent):
        """Set bone transformations."""
        pyskin = gltf.data.skins[skin_id]
        pynode = gltf.data.nodes[node_id]

        obj = bpy.data.objects[pyskin.blender_armature_name]

        # Set bone bind_pose by inverting bindpose matrix
        if node_id in pyskin.joints:
            index_in_skel = pyskin.joints.index(node_id)
            if pyskin.inverse_bind_matrices is not None:
                inverse_bind_matrices = BinaryData.get_data_from_accessor(gltf, pyskin.inverse_bind_matrices)
                # Needed to keep scale in matrix, as bone.matrix seems to drop it
                if index_in_skel < len(inverse_bind_matrices):
                    pynode.blender_bone_matrix = matrix_gltf_to_blender(
                        inverse_bind_matrices[index_in_skel]
                    ).inverted()
                    bone.matrix = pynode.blender_bone_matrix
                else:
                    gltf.log.error("Error with inverseBindMatrix for skin " + pyskin)
            else:
                pynode.blender_bone_matrix = Matrix() # 4x4 identity matrix
        else:
            print('No invBindMatrix for bone ' + str(node_id))
            pynode.blender_bone_matrix = Matrix()

        # Parent the bone
        if parent is not None and hasattr(gltf.data.nodes[parent], "blender_bone_name"):
            bone.parent = obj.data.edit_bones[gltf.data.nodes[parent].blender_bone_name]  # TODO if in another scene

        # Switch to Pose mode
        bpy.ops.object.mode_set(mode="POSE")
        obj.data.pose_position = 'POSE'

        # Set posebone location/rotation/scale (in armature space)
        # location is actual bone location minus it's original (bind) location
        bind_location = Matrix.Translation(pynode.blender_bone_matrix.to_translation())
        bind_rotation = pynode.blender_bone_matrix.to_quaternion()
        bind_scale = scale_to_matrix(pynode.blender_bone_matrix.to_scale())

        location, rotation, scale = matrix_gltf_to_blender(pynode.transform).decompose()
        if parent is not None and hasattr(gltf.data.nodes[parent], "blender_bone_matrix"):
            parent_mat = gltf.data.nodes[parent].blender_bone_matrix

            # Get armature space location (bindpose + pose)
            # Then, remove original bind location from armspace location, and bind rotation
            if bpy.app.version < (2, 80, 0):
                final_location = (bind_location.inverted() * parent_mat * Matrix.Translation(location)).to_translation()
                obj.pose.bones[pynode.blender_bone_name].location = \
                    bind_rotation.inverted().to_matrix().to_4x4() * final_location
            else:
                final_location = (bind_location.inverted() @ parent_mat @ Matrix.Translation(location)).to_translation()
                obj.pose.bones[pynode.blender_bone_name].location = \
                    bind_rotation.inverted().to_matrix().to_4x4() @ final_location

            # Do the same for rotation
            if bpy.app.version < (2, 80, 0):
                obj.pose.bones[pynode.blender_bone_name].rotation_quaternion = \
                    (bind_rotation.
                        to_matrix().to_4x4().inverted() * parent_mat * rotation.to_matrix().to_4x4()).to_quaternion()
                obj.pose.bones[pynode.blender_bone_name].scale = \
                    (bind_scale.inverted() * parent_mat * scale_to_matrix(scale)).to_scale()
            else:
                obj.pose.bones[pynode.blender_bone_name].rotation_quaternion = \
                    (bind_rotation.to_matrix().to_4x4().inverted() @ parent_mat @
                        rotation.to_matrix().to_4x4()).to_quaternion()
                obj.pose.bones[pynode.blender_bone_name].scale = \
                    (bind_scale.inverted() @ parent_mat @ scale_to_matrix(scale)).to_scale()

        else:
            if bpy.app.version < (2, 80, 0):
                obj.pose.bones[pynode.blender_bone_name].location = bind_location.inverted() * location
                obj.pose.bones[pynode.blender_bone_name].rotation_quaternion = bind_rotation.inverted() * rotation
                obj.pose.bones[pynode.blender_bone_name].scale = bind_scale.inverted() * scale
            else:
                obj.pose.bones[pynode.blender_bone_name].location = bind_location.inverted() @ location
                obj.pose.bones[pynode.blender_bone_name].rotation_quaternion = bind_rotation.inverted() @ rotation
                obj.pose.bones[pynode.blender_bone_name].scale = bind_scale.inverted() @ scale

    @staticmethod
    def create_bone(gltf, skin_id, node_id, parent):
        """Bone creation."""
        pyskin = gltf.data.skins[skin_id]
        pynode = gltf.data.nodes[node_id]

        scene = bpy.data.scenes[gltf.blender_scene]
        obj = bpy.data.objects[pyskin.blender_armature_name]

        if bpy.app.version < (2, 80, 0):
            bpy.context.screen.scene = scene
            scene.objects.active = obj
        else:
            bpy.context.window.scene = scene
            bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode="EDIT")

        if pynode.name:
            name = pynode.name
        else:
            name = "Bone_" + str(node_id)

        bone = obj.data.edit_bones.new(name)
        pynode.blender_bone_name = bone.name
        pynode.blender_armature_name = pyskin.blender_armature_name
        bone.tail = Vector((0.0, 1.0, 0.0))  # Needed to keep bone alive

        # set bind and pose transforms
        BlenderSkin.set_bone_transforms(gltf, skin_id, bone, node_id, parent)
        bpy.ops.object.mode_set(mode="OBJECT")

    @staticmethod
    def create_vertex_groups(gltf, skin_id):
        """Vertex Group creation."""
        pyskin = gltf.data.skins[skin_id]
        for node_id in pyskin.node_ids:
            obj = bpy.data.objects[gltf.data.nodes[node_id].blender_object]
            for bone in pyskin.joints:
                obj.vertex_groups.new(name=gltf.data.nodes[bone].blender_bone_name)

    @staticmethod
    def assign_vertex_groups(gltf, skin_id):
        """Assign vertex groups to vertices."""
        pyskin = gltf.data.skins[skin_id]
        for node_id in pyskin.node_ids:
            node = gltf.data.nodes[node_id]
            obj = bpy.data.objects[node.blender_object]

            offset = 0
            for prim in gltf.data.meshes[node.mesh].primitives:
                idx_already_done = {}

                if 'JOINTS_0' in prim.attributes.keys() and 'WEIGHTS_0' in prim.attributes.keys():
                    original_joint_ = BinaryData.get_data_from_accessor(gltf, prim.attributes['JOINTS_0'])
                    original_weight_ = BinaryData.get_data_from_accessor(gltf, prim.attributes['WEIGHTS_0'])

                    tmp_indices = {}
                    tmp_idx = 0
                    weight_ = []
                    for i in prim.tmp_indices:
                        if i[0] not in tmp_indices.keys():
                            tmp_indices[i[0]] = tmp_idx
                            tmp_idx += 1
                            weight_.append(original_weight_[i[0]])

                    tmp_indices = {}
                    tmp_idx = 0
                    joint_ = []
                    for i in prim.tmp_indices:
                        if i[0] not in tmp_indices.keys():
                            tmp_indices[i[0]] = tmp_idx
                            tmp_idx += 1
                            joint_.append(original_joint_[i[0]])


                    for poly in obj.data.polygons:
                        for loop_idx in range(poly.loop_start, poly.loop_start + poly.loop_total):
                            vert_idx = obj.data.loops[loop_idx].vertex_index

                            if vert_idx in idx_already_done.keys():
                                continue
                            idx_already_done[vert_idx] = True

                            if vert_idx in range(offset, offset + prim.vertices_length):

                                tab_index = vert_idx - offset
                                cpt = 0
                                for joint_idx in joint_[tab_index]:
                                    weight_val = weight_[tab_index][cpt]
                                    if weight_val != 0.0:   # It can be a problem to assign weights of 0
                                                            # for bone index 0, if there is always 4 indices in joint_
                                                            # tuple
                                        group = obj.vertex_groups[gltf.data.nodes[
                                            pyskin.joints[joint_idx]
                                        ].blender_bone_name]
                                        group.add([vert_idx], weight_val, 'REPLACE')
                                    cpt += 1
                else:
                    gltf.log.error("No Skinning ?????")  # TODO

                offset = offset + prim.vertices_length

    @staticmethod
    def create_armature_modifiers(gltf, skin_id):
        """Create Armature modifier."""
        pyskin = gltf.data.skins[skin_id]

        if pyskin.blender_armature_name is None:
            # TODO seems something is wrong
            # For example, some joints are in skin 0, and are in another skin too
            # Not sure this is glTF compliant, will check it
            return

        for node_id in pyskin.node_ids:
            node = gltf.data.nodes[node_id]
            obj = bpy.data.objects[node.blender_object]

            if bpy.app.version < (2, 80, 0):
                for obj_sel in bpy.context.scene.objects:
                    obj_sel.select = False
                obj.select = True
                bpy.context.scene.objects.active = obj
            else:
                for obj_sel in bpy.context.scene.objects:
                    obj_sel.select_set(False)
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj

            # bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
            # Reparent skinned mesh to it's armature to avoid breaking
            # skinning with interleaved transforms
            obj.parent = bpy.data.objects[pyskin.blender_armature_name]
            arma = obj.modifiers.new(name="Armature", type="ARMATURE")
            arma.object = bpy.data.objects[pyskin.blender_armature_name]
