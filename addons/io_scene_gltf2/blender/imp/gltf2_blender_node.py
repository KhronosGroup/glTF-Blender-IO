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
from .gltf2_blender_mesh import *
from .gltf2_blender_camera import *
from .gltf2_blender_skin import *
from ..com.gltf2_blender_conversion import *

class BlenderNode():

    @staticmethod
    def create(gltf, node_idx, parent):

        pynode = gltf.data.nodes[node_idx]

        # Blender attributes initialization
        pynode.blender_object = ""
        pynode.parent = parent

        if pynode.mesh is not None:
            if pynode.name:
                gltf.log.info("Blender create Mesh node " + pynode.name)
            else:
                gltf.log.info("Blender create Mesh node")

            if pynode.name:
                name = pynode.name
            else:
                # Take mesh name if exist
                if gltf.data.meshes[pynode.mesh].name:
                    name = gltf.data.meshes[pynode.mesh].name
                else:
                    name = "Object_" + str(node_idx)

            mesh = BlenderMesh.create(gltf, pynode.mesh, parent)

            obj = bpy.data.objects.new(name, mesh)
            obj.rotation_mode = 'QUATERNION'
            bpy.data.scenes[gltf.blender_scene].objects.link(obj)

            # Transforms apply only if this mesh is not skinned
            # See implementation node of gltf2 specification
            if not (pynode.mesh and gltf.data.meshes[pynode.mesh].skin is not None):
                BlenderNode.set_transforms(pynode, obj, parent)
            pynode.blender_object = obj.name
            BlenderNode.set_parent(pynode, obj, parent)

            BlenderMesh.set_mesh(gltf, gltf.data.meshes[pynode.mesh], mesh, obj)

            for child_idx in pynode.children:
                BlenderNode.create(gltf, gltf.data.nodes[child], child, node_idx)

            return


        if pynode.camera is not None:
            if pynode.name:
                gltf.log.info("Blender create Camera node " + pynode.name)
            else:
                gltf.log.info("Blender create Camera node")
            obj = BlenderCamera.create(gltf, pynode.camera)
            BlenderNode.set_transforms(pynode, obj, parent) #TODO default rotation of cameras ?
            pynode.blender_object = obj.name
            BlenderNode.set_parent(pynode, obj, parent)

            return


        if pynode.is_joint:
            if pynode.name:
                gltf.log.info("Blender create Bone node " + pynode.name)
            else:
                gltf.log.info("Blender create Bone node")
            # Check if corresponding armature is already created, create it if needed
            if not hasattr(gltf.skins[pynode.skin_id], "blender_armature_name"):
                BlenderSkin.create_armature(gltf, gltf.data.skins[pynode.skin_id], pynode.skin_id, parent)

            BlenderSkin.create_bone(gktf, gltf.skins[pynode.skin_id], pynode, node_idx, parent)

            if pynode.children:
                for child_idx in pynode.children:
                    BlenderNode.create(gltf, gltf.data.nodes[child_idx], child_idx, node_idx)

            return

        # No mesh, no camera. For now, create empty #TODO

        if pynode.name:
            gltf.log.info("Blender create Empty node " + pynode.name)
            obj = bpy.data.objects.new(pynode.name, None)
        else:
            gltf.log.info("Blender create Empty node")
            obj = bpy.data.objects.new("Node", None)
        obj.rotation_mode = 'QUATERNION'
        bpy.data.scenes[gltf.blender_scene].objects.link(obj)
        BlenderNode.set_transforms(pynode, obj, parent)
        pynode.blender_object = obj.name
        BlenderNode.set_parent(pynode, obj, parent)

        if pynode.children:
            for child_idx in pynode.children:
                BlenderNode.create(gltf, gltf.data.nodes[child_idx], child_idx, node_idx)


    @staticmethod
    def set_parent(pynode, obj, parent):

        if parent is None:
            return

        for node_idx, node in enumerate(gltf.data.nodes):
            if node_idx == parent:
                if node.is_joint == True:
                    bpy.ops.object.select_all(action='DESELECT')
                    bpy.data.objects[node.blender_armature_name].select = True
                    bpy.context.scene.objects.active = bpy.data.objects[node.blender_armature_name]
                    bpy.ops.object.mode_set(mode='EDIT')
                    bpy.data.objects[node.blender_armature_name].data.edit_bones.active = bpy.data.objects[node.blender_armature_name].data.edit_bones[node.blender_bone_name]
                    bpy.ops.object.mode_set(mode='OBJECT')
                    bpy.ops.object.select_all(action='DESELECT')
                    obj.select = True
                    bpy.data.objects[node.blender_armature_name].select = True
                    bpy.context.scene.objects.active = bpy.data.objects[node.blender_armature_name]
                    bpy.ops.object.parent_set(type='BONE', keep_transform=True)

                    return
                if node.blender_object:
                    obj.parent = bpy.data.objects[node.blender_object]
                    return

        gltf.log.error("ERROR, parent not found")

    @staticmethod
    def set_transforms(pynode, obj, parent):
        if parent is None:
            obj.matrix_world =  Conversion.matrix_gltf_to_blender(pynode.transform)
            return

        for node in gltf.data.nodes: # TODO if parent is in another scene
            if node.index == parent:
                if node.is_joint == True:
                    obj.matrix_world = Conversion.matrix_gltf_to_blender(pynode.transform)
                    return
                else:
                    obj.matrix_world = Conversion.matrix_gltf_to_blender(pynode.transform)
                    return
