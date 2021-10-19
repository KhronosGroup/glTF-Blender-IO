# Copyright 2021 The glTF-Blender-IO authors.
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
import uuid

from . import gltf2_blender_export_keys
from mathutils import Quaternion, Matrix

class VExportNode:

    OBJECT = 1
    ARMATURE = 2
    BONE = 3
    LIGHT = 4
    CAMERA = 5

    # Parent type, to be set on child regarding its parent
    NO_PARENT = 54
    PARENT_OBJECT = 50
    PARENT_BONE = 51
    PARENT_BONE_RELATIVE = 52
    PARENT_ROOT_BONE = 53
    PARENT_BONE_BONE = 55


    def __init__(self):
        self.children = []
        self.blender_type = None
        self.world_matrix = None
        self.parent_type = None

        self.blender_object = None
        self.blender_bone = None

        # Only for bone/bone
        self.parent_bone_uuid = None

        # Only for armature
        self.bones = {}

        # For deformed object
        self.armature = None # for deformed object and for bone
        self.skin = None

        # glTF
        self.node = None

    def add_child(self, uuid):
        self.children.append(uuid)

    def set_world_matrix(self, matrix):
        self.world_matrix = matrix

    def set_blender_data(self, blender_object, blender_bone):
        self.blender_object = blender_object
        self.blender_bone = blender_bone

    def recursive_display(self, tree, mode):
        if mode == "simple":
            for c in self.children:
                print(self.blender_object.name, "/", self.blender_bone.name if self.blender_bone else "", "-->", tree.nodes[c].blender_object.name, "/", tree.nodes[c].blender_bone.name if tree.nodes[c].blender_bone else "" )
                tree.nodes[c].recursive_display(tree, mode)

class VExportTree:
    def __init__(self, export_settings):
        self.nodes = {}
        self.roots = []

        self.export_settings = export_settings

    def add_node(self, node):
        self.nodes[node.uuid] = node

    def add_children(self, uuid_parent, uuid_child):
        self.nodes[uuid_parent].add_child(uuid_child)

    def construct(self, blender_scene):
        bpy.context.window.scene = blender_scene
        depsgraph = bpy.context.evaluated_depsgraph_get()

        # First retrieve local objects only
        # Because this is only local objects or collection instances, we can use name as key
        for blender_object in [obj.original for obj in depsgraph.objects if obj.parent is None]:
            self.recursive_node_traverse(blender_object, None, None, Matrix.Identity(4))

    def recursive_node_traverse(self, blender_object, blender_bone, parent_uuid, parent_coll_matrix_world, armature_uuid=None):
        node = VExportNode()
        node.uuid = str(uuid.uuid4())
        node.parent_uuid = parent_uuid
        node.set_blender_data(blender_object, blender_bone)

        # add to parent if needed
        if parent_uuid is not None:
            self.add_children(parent_uuid, node.uuid)
        else:
            self.roots.append(node.uuid)

        # Set blender type
        if blender_bone is not None:
            node.blender_type = VExportNode.BONE
            self.nodes[armature_uuid].bones[blender_bone.name] = node.uuid
        elif blender_object.type == "ARMATURE":
            node.blender_type = VExportNode.ARMATURE
        elif blender_object.type == "CAMERA":
            node.blender_type = VExportNode.CAMERA
        elif blender_object.type == "LIGHT":
            node.blender_type = VExportNode.LIGHT
        else:
            node.blender_type = VExportNode.OBJECT

        # For meshes with armature modifier (parent is armature), keep armature uuid
        if node.blender_type == VExportNode.OBJECT:
            modifiers = {m.type: m for m in blender_object.modifiers}
            if "ARMATURE" in modifiers and modifiers["ARMATURE"].object is not None:
                node.armature = parent_uuid
        # TODO: manage when direct parent is not the armature
        # correct workflow is to parent skinned mesh to armature, but ...
        # all users don't use correct workflow


        # For bones, store uuid of armature
        if blender_bone is not None:
            node.armature = armature_uuid

        # for bone/bone parenting, store parent, this will help armature tree management
        if parent_uuid is not None and self.nodes[parent_uuid].blender_type == VExportNode.BONE and node.blender_type == VExportNode.BONE:
            node.parent_bone_uuid = parent_uuid


        # Objects parented to bone
        if parent_uuid is not None and self.nodes[parent_uuid].blender_type == VExportNode.BONE and node.blender_type != VExportNode.BONE:
            node.parent_bone_uuid = parent_uuid

        # Now we know parent and child type, we can set parent_type
        # TODO





        # World Matrix
        # Store World Matrix for objects
        if node.blender_type in [VExportNode.OBJECT, VExportNode.ARMATURE, VExportNode.CAMERA, VExportNode.LIGHT]:
            # Matrix World of object is expressed based on collection instance objects are
            # So real world matrix is collection world_matrix @ "world_matrix" of object
            node.matrix_world = parent_coll_matrix_world @ blender_object.matrix_world.copy()
            if node.blender_type == VExportNode.CAMERA and self.export_settings[gltf2_blender_export_keys.CAMERAS]:
                correction = Quaternion((2**0.5/2, -2**0.5/2, 0.0, 0.0))
                node.matrix_world @= correction.to_matrix().to_4x4()
            elif node.blender_type == VExportNode.LIGHT and self.export_settings[gltf2_blender_export_keys.LIGHTS]:
                correction = Quaternion((2**0.5/2, -2**0.5/2, 0.0, 0.0))
                node.matrix_world @= correction.to_matrix().to_4x4()
        elif node.blender_type == VExportNode.BONE:
            node.matrix_world = self.nodes[node.armature].matrix_world @ blender_bone.matrix
            axis_basis_change = Matrix(
                ((1.0, 0.0, 0.0, 0.0), (0.0, 0.0, 1.0, 0.0), (0.0, -1.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0)))
            node.matrix_world = node.matrix_world @ axis_basis_change

        # Storing this node
        self.add_node(node)

        ###### Manage children ######

        # standard children
        if blender_bone is None:
            for child_object in blender_object.children:
                if child_object.parent_bone:
                    # Object parented to bones
                    # Will be manage later
                    continue
                else:
                    # Classic parenting
                    self.recursive_node_traverse(child_object, None, node.uuid, parent_coll_matrix_world)

        # Collections
        if blender_object.instance_type == 'COLLECTION' and blender_object.instance_collection:
            for dupli_object in blender_object.instance_collection.objects:
                if dupli_object.parent is not None:
                    continue
                if dupli_object.type == "ARMATURE":
                    continue # There is probably a proxy #TODOPROXY remove check ?
                self.recursive_node_traverse(dupli_object, None, node.uuid, node.matrix_world)

        # Armature : children are bones with no parent
        if blender_object.type == "ARMATURE" and blender_bone is None:
            for b in [b for b in blender_object.pose.bones if b.parent is None]:
                self.recursive_node_traverse(blender_object, b, node.uuid, parent_coll_matrix_world, node.uuid)

        # Bones
        if blender_object.type == "ARMATURE" and blender_bone is not None:
            for b in blender_bone.children:
                self.recursive_node_traverse(blender_object, b, node.uuid, parent_coll_matrix_world, armature_uuid)

        # Object parented to bone
        if blender_bone is not None:
            for child_object in [c for c in blender_object.children if c.parent_bone is not None and c.parent_bone == blender_bone.name]:
                self.recursive_node_traverse(child_object, None, node.uuid, parent_coll_matrix_world)

    def get_all_objects(self):
        return [n.uuid for n in self.nodes.values() if n.blender_type != VExportNode.BONE]

    def display(self, mode):
        if mode == "simple":
            for n in self.roots:
                print("Root", self.nodes[n].blender_object.name, "/", self.nodes[n].blender_bone.name if self.nodes[n].blender_bone else "" )
                self.nodes[n].recursive_display(self, mode)
