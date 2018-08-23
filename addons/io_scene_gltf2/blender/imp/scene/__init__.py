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
from math import sqrt
from mathutils import Quaternion

from ..node import *

class Scene():
    def __init__(self, index, json, gltf):
        self.json = json   # Scene json
        self.gltf = gltf # Reference to global glTF instance
        self.nodes = {}
        self.root_nodes_idx = []

    def read(self):
        if 'name' in self.json.keys():
            self.name = self.json['name']
            self.gltf.log.info("Scene " + self.json['name'])
        else:
            self.name = None
            self.gltf.log.info("Scene...")


        for node_idx in self.json['nodes']:
            node = Node(node_idx, self.gltf.json['nodes'][node_idx], self.gltf, self)
            node.read()
            node.debug_missing()
            self.nodes[node_idx] = node

        for skin in self.gltf.skins.values():
            if skin.root is not None and skin.root != skin.bones[0]:
                # skin.bones.insert(0, skin.root)
                self.nodes[skin.root].is_joint = True
                self.nodes[skin.root].skin_id = skin.index

        # manage root nodes
        parent_detector = {}
        for node in self.nodes:
            for child in self.nodes[node].children:
                parent_detector[child.index] = node

        for node in self.nodes:
            if node not in parent_detector.keys():
                self.root_nodes_idx.append(node)

    def blender_create(self):

        # Create Yup2Zup empty
        obj_rotation = bpy.data.objects.new("Yup2Zup", None)
        obj_rotation.rotation_mode = 'QUATERNION'
        obj_rotation.rotation_quaternion = Quaternion((sqrt(2)/2, sqrt(2)/2,0.0,0.0))


    # Create a new scene only if not already exists in .blend file
    # TODO : put in current scene instead ?
        if self.name not in [scene.name for scene in bpy.data.scenes]:
            if self.name:
                scene = bpy.data.scenes.new(self.name)
            else:
                scene = bpy.context.scene
            scene.render.engine = "CYCLES"

            self.gltf.blender_scene = scene.name
        else:
            self.gltf.blender_scene = self.name

        for node in self.root_nodes_idx:
            self.nodes[node].blender_create(None) # None => No parent

        # Now that all mesh / bones are created, create vertex groups on mesh
        for armature in self.gltf.skins.values():
            armature.create_vertex_groups()

        for armature in self.gltf.skins.values():
            armature.assign_vertex_groups()

        for armature in self.gltf.skins.values():
            armature.create_armature_modifiers()

        for node in self.root_nodes_idx:
                self.nodes[node].animation.blender_anim()


        # Parent root node to rotation object
        bpy.data.scenes[self.gltf.blender_scene].objects.link(obj_rotation)
        for node in self.root_nodes_idx:
            bpy.data.objects[self.nodes[node].blender_object].parent = obj_rotation


    # TODO create blender for other scenes



    def debug_missing(self):
        keys = [
                'nodes',
                'name'
                ]

        for key in self.json.keys():
            if key not in keys:
                self.gltf.log.debug("SCENE MISSING " + key)
