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
 * This development is done in strong collaboration with Airbus Defence & Space
 """

import bpy

from mathutils import Matrix, Vector, Quaternion

from ..mesh import *
from ..camera import *
from ..animation import *

class Node():
    def __init__(self, index, json, gltf, scene):
        self.index = index
        self.json = json   # Node json
        self.gltf = gltf # Reference to global glTF instance
        self.scene = scene # Reference to scene
        self.mesh = None
        self.camera = None
        self.children = []
        self.blender_object = ""
        self.animation = AnimationData(self, self.gltf)
        self.is_joint = False
        self.parent = None

    def read(self):
        if 'name' in self.json.keys():
            self.name = self.json['name']
            self.gltf.log.info("Node " + self.json['name'])
        else:
            self.name = None
            self.gltf.log.info("Node index " + str(self.index))

        self.transform = self.get_transforms()

        if 'mesh' in self.json.keys():
            if self.json['mesh'] not in self.gltf.meshes.keys():
                self.gltf.meshes[self.json['mesh']] = Mesh(self.json['mesh'], self.gltf.json['meshes'][self.json['mesh']], self.gltf)
                self.mesh = self.gltf.meshes[self.json['mesh']]
                self.mesh.read()
                self.mesh.debug_missing()
            else:
                self.mesh = self.gltf.meshes[self.json['mesh']]

            if 'skin' in self.json.keys():
                self.mesh.rig(self.json['skin'], self.index)

        if 'camera' in self.json.keys():
            self.camera = Camera(self.json['camera'], self.name, self.gltf.json['cameras'][self.json['camera']], self.gltf)
            self.camera.read()
            self.camera.debug_missing()


        if not 'children' in self.json.keys():
            return

        for child in self.json['children']:
            child = Node(child, self.gltf.json['nodes'][child], self.gltf, self.scene)
            child.read()
            child.debug_missing()
            self.children.append(child)
            self.scene.nodes[child.index] = child

    def get_transforms(self):

        if 'matrix' in self.json.keys():
            return self.gltf.convert.matrix(self.json['matrix'])

        mat = Matrix()


        if 'scale' in self.json.keys():
            s = self.json['scale']
            mat = Matrix([
                [s[0], 0, 0, 0],
                [0, s[1], 0, 0],
                [0, 0, s[2], 0],
                [0, 0, 0, 1]
            ])


        if 'rotation' in self.json.keys():
            q = self.gltf.convert.quaternion(self.json['rotation'])
            mat = q.to_matrix().to_4x4() * mat

        if 'translation' in self.json.keys():
            mat = Matrix.Translation(Vector(self.gltf.convert.location(self.json['translation']))) * mat

        return mat


    def set_transforms(self, obj, parent):
        if parent is None:
            obj.matrix_world =  self.transform
            return

        for node in self.gltf.scene.nodes.values(): # TODO if parent is in another scene
            if node.index == parent:
                if node.is_joint == True:
                    obj.matrix_world = self.transform
                    return
                else:
                    obj.matrix_world = self.transform
                    return



    def set_blender_parent(self, obj, parent):

        if parent is None:
            return

        for node in self.gltf.scene.nodes.values(): # TODO if parent is in another scene
            if node.index == parent:
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

        self.gltf.log.error("ERROR, parent not found")

    def blender_create(self, parent):
        self.parent = parent
        if self.mesh:
            if self.name:
                self.gltf.log.info("Blender create Mesh node " + self.name)
            else:
                self.gltf.log.info("Blender create Mesh node")

            if self.name:
                name = self.name
            else:
                # Take mesh name if exist
                if self.mesh.name:
                    name = self.mesh.name
                else:
                    name = "Object_" + str(self.index)

            mesh = self.mesh.blender_create(parent)

            obj = bpy.data.objects.new(name, mesh)
            obj.rotation_mode = 'QUATERNION'
            bpy.data.scenes[self.gltf.blender_scene].objects.link(obj)

            # Transforms apply only if this mesh is not skinned
            # See implementation node of gltf2 specification
            if not (self.mesh and self.mesh.skin is not None):
                self.set_transforms(obj, parent)
            self.blender_object = obj.name
            self.set_blender_parent(obj, parent)

            self.mesh.blender_set_mesh(mesh, obj)

            for child in self.children:
                child.blender_create(self.index)

            return

        if self.camera:
            if self.name:
                self.gltf.log.info("Blender create Camera node " + self.name)
            else:
                self.gltf.log.info("Blender create Camera node")
            obj = self.camera.create_blender()
            self.set_transforms(obj, parent) #TODO default rotation of cameras ?
            self.blender_object = obj.name
            self.set_blender_parent(obj, parent)

            return


        if self.is_joint:
            if self.name:
                self.gltf.log.info("Blender create Bone node " + self.name)
            else:
                self.gltf.log.info("Blender create Bone node")
            # Check if corresponding armature is already created, create it if needed
            if self.gltf.skins[self.skin_id].blender_armature_name is None:
                self.gltf.skins[self.skin_id].create_blender_armature(parent)

            self.gltf.skins[self.skin_id].create_bone(self, parent)

            for child in self.children:
                child.blender_create(self.index)

            return

        # No mesh, no camera. For now, create empty #TODO

        if self.name:
            self.gltf.log.info("Blender create Empty node " + self.name)
            obj = bpy.data.objects.new(self.name, None)
        else:
            self.gltf.log.info("Blender create Empty node")
            obj = bpy.data.objects.new("Node", None)
        obj.rotation_mode = 'QUATERNION'
        bpy.data.scenes[self.gltf.blender_scene].objects.link(obj)
        self.set_transforms(obj, parent)
        self.blender_object = obj.name
        self.set_blender_parent(obj, parent)

        for child in self.children:
            child.blender_create(self.index)

    def debug_missing(self):
        keys = [
                'name',
                'mesh',
                'matrix',
                'translation',
                'rotation',
                'scale',
                'children',
                'camera',
                'skin'
                ]

        for key in self.json.keys():
            if key not in keys:
                self.gltf.log.debug("NODE MISSING " + key)
