"""
 * ***** BEGIN GPL LICENSE BLOCK *****
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License
 * as published by the Free Software Foundation; either version 2
 * of the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software Foundation,
 * Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
 *
 * Contributor(s): Julien Duroure.
 *
 * ***** END GPL LICENSE BLOCK *****
 """


import bpy
from mathutils import Vector, Matrix, Quaternion
from ..com.gltf2_blender_conversion import *

class BlenderSkin():

    @staticmethod
    def create_armature(pyskin, parent):

        pyskin.blender_armature_name = None

        if pyskin.name is not None:
            name = pyskin.name
        else:
            name = "Armature_" + str(pyskin.index)

        armature = bpy.data.armatures.new(name)
        obj = bpy.data.objects.new(name, armature)
        bpy.data.scenes[pyskin.gltf.blender_scene].objects.link(obj)
        pyskin.blender_armature_name = obj.name
        if parent:
            obj.parent = bpy.data.objects[pyskin.gltf.scene.nodes[parent].blender_object]

    @staticmethod
    def set_bone_transforms(pyskin, bone, node, parent):
        obj   = bpy.data.objects[pyskin.blender_armature_name]

        mat = Matrix()
        if parent is None:
            transform = Conversion.matrix_gltf_to_blender(node.transform)
            mat = transform
        else:
            if not pyskin.gltf.scene.nodes[parent].is_joint: # TODO if Node in another scene
                transform  = Conversion.matrix_gltf_to_blender(node.transform)
                mat = transform
            else:
                transform = Conversion.matrix_gltf_to_blender(node.transform)
                parent_mat = obj.data.edit_bones[pyskin.gltf.scene.nodes[parent].blender_bone_name].matrix # Node in another scene

                mat = (parent_mat.to_quaternion() * transform.to_quaternion()).to_matrix().to_4x4()
                mat = Matrix.Translation(parent_mat.to_translation() + ( parent_mat.to_quaternion() * transform.to_translation() )) * mat
                #TODO scaling of bones ?

        bone.matrix = mat
        return bone.matrix

    @staticmethod
    def create_bone(pyskin, node, parent):
        scene = bpy.data.scenes[pyskin.gltf.blender_scene]
        obj   = bpy.data.objects[pyskin.blender_armature_name]

        bpy.context.screen.scene = scene
        scene.objects.active = obj
        bpy.ops.object.mode_set(mode="EDIT")

        if node.name:
            name = node.name
        else:
            name = "Bone_" + str(node.index)

        bone = obj.data.edit_bones.new(name)
        node.blender_bone_name = bone.name
        node.blender_armature_name = pyskin.blender_armature_name
        bone.tail = Vector((0.0,1.0,0.0)) # Needed to keep bone alive
        mat = BlenderSkin.set_bone_transforms(pyskin, bone, node, parent)
        node.blender_bone_matrix = mat

        # Set parent
        if parent is not None and hasattr(pyskin.gltf.scene.nodes[parent], "blender_bone_name"):
            bone.parent = obj.data.edit_bones[pyskin.gltf.scene.nodes[parent].blender_bone_name] #TODO if in another scene

        bpy.ops.object.mode_set(mode="OBJECT")

    @staticmethod
    def create_vertex_groups(pyskin):
        obj = bpy.data.objects[pyskin.gltf.scene.nodes[pyskin.mesh_id].blender_object]
        for bone in pyskin.bones:
            obj.vertex_groups.new(pyskin.gltf.scene.nodes[bone].blender_bone_name)

    @staticmethod
    def assign_vertex_groups(pyskin):
        node = pyskin.gltf.scene.nodes[pyskin.mesh_id]
        obj = bpy.data.objects[node.blender_object]

        offset = 0
        for prim in node.mesh.primitives:
            idx_already_done = {}

            if 'JOINTS_0' in prim.attributes.keys() and 'WEIGHTS_0' in prim.attributes.keys():
                joint_ = prim.attributes['JOINTS_0']['result']
                weight_ = prim.attributes['WEIGHTS_0']['result']

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
                                                        # for bone index 0, if there is always 4 indices in joint_ tuple
                                    group = obj.vertex_groups[pyskin.gltf.scene.nodes[pyskin.bones[joint_idx]].blender_bone_name]
                                    group.add([vert_idx], weight_val, 'REPLACE')
                                cpt += 1
            else:
                pyskin.gltf.log.error("No Skinning ?????") #TODO


            offset = offset + prim.vertices_length

    @staticmethod
    def create_armature_modifiers(pyskin):
        node = pyskin.gltf.scene.nodes[pyskin.mesh_id]
        obj = bpy.data.objects[node.blender_object]

        for obj_sel in bpy.context.scene.objects:
            obj_sel.select = False
        obj.select = True
        bpy.context.scene.objects.active = obj

        #bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
        #obj.parent = bpy.data.objects[pyskin.blender_armature_name]
        arma = obj.modifiers.new(name="Armature", type="ARMATURE")
        arma.object = bpy.data.objects[pyskin.blender_armature_name]
