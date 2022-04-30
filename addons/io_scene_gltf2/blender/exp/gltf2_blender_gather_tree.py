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
import numpy as np

from . import gltf2_blender_export_keys
from io_scene_gltf2.io.exp.gltf2_io_user_extensions import export_user_extensions
from mathutils import Quaternion, Matrix
from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.io.imp.gltf2_io_binary import BinaryData
from io_scene_gltf2.io.com import gltf2_io_constants
from .gltf2_blender_gather_primitive_attributes import array_to_accessor
from io_scene_gltf2.io.exp import gltf2_io_binary_data
from io_scene_gltf2.blender.exp import gltf2_blender_gather_accessors

class VExportNode:

    OBJECT = 1
    ARMATURE = 2
    BONE = 3
    LIGHT = 4
    CAMERA = 5
    COLLECTION = 6

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

        self.force_as_empty = False # Used for instancer display

        # Only for bone/bone and object parented to bone
        self.parent_bone_uuid = None

        # Only for bones
        self.use_deform = None

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

        self.tree_troncated = False

    def add_node(self, node):
        self.nodes[node.uuid] = node

    def add_children(self, uuid_parent, uuid_child):
        self.nodes[uuid_parent].add_child(uuid_child)

    def construct(self, blender_scene):
        bpy.context.window.scene = blender_scene
        depsgraph = bpy.context.evaluated_depsgraph_get()

        for blender_object in [obj.original for obj in depsgraph.scene_eval.objects if obj.parent is None]:
            self.recursive_node_traverse(blender_object, None, None, Matrix.Identity(4))

    def recursive_node_traverse(self, blender_object, blender_bone, parent_uuid, parent_coll_matrix_world, armature_uuid=None, dupli_world_matrix=None):
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
            node.use_deform = blender_bone.id_data.data.bones[blender_bone.name].use_deform
        elif blender_object.type == "ARMATURE":
            node.blender_type = VExportNode.ARMATURE
        elif blender_object.type == "CAMERA":
            node.blender_type = VExportNode.CAMERA
        elif blender_object.type == "LIGHT":
            node.blender_type = VExportNode.LIGHT
        elif blender_object.instance_type == "COLLECTION":
            node.blender_type = VExportNode.COLLECTION
        else:
            node.blender_type = VExportNode.OBJECT

        # For meshes with armature modifier (parent is armature), keep armature uuid
        if node.blender_type == VExportNode.OBJECT:
            modifiers = {m.type: m for m in blender_object.modifiers}
            if "ARMATURE" in modifiers and modifiers["ARMATURE"].object is not None:
                if parent_uuid is None or not self.nodes[parent_uuid].blender_type == VExportNode.ARMATURE:
                    # correct workflow is to parent skinned mesh to armature, but ...
                    # all users don't use correct workflow
                    print("WARNING: Armature must be the parent of skinned mesh")
                    print("Armature is selected by its name, but may be false in case of instances")
                    # Search an armature by name, and use the first found
                    # This will be done after all objects are setup
                    node.armature_needed = modifiers["ARMATURE"].object.name
                else:
                    node.armature = parent_uuid

        # For bones, store uuid of armature
        if blender_bone is not None:
            node.armature = armature_uuid

        # for bone/bone parenting, store parent, this will help armature tree management
        if parent_uuid is not None and self.nodes[parent_uuid].blender_type == VExportNode.BONE and node.blender_type == VExportNode.BONE:
            node.parent_bone_uuid = parent_uuid


        # Objects parented to bone
        if parent_uuid is not None and self.nodes[parent_uuid].blender_type == VExportNode.BONE and node.blender_type != VExportNode.BONE:
            node.parent_bone_uuid = parent_uuid

        # World Matrix
        # Store World Matrix for objects
        if dupli_world_matrix is not None:
            node.matrix_world = dupli_world_matrix
        elif node.blender_type in [VExportNode.OBJECT, VExportNode.COLLECTION, VExportNode.ARMATURE, VExportNode.CAMERA, VExportNode.LIGHT]:
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
            if self.export_settings['gltf_current_frame'] is True:
                # Use pose bone for TRS
                node.matrix_world = self.nodes[node.armature].matrix_world @ blender_bone.matrix
            else:
                # Use edit bone for TRS --> REST pose will be used
                node.matrix_world = self.nodes[node.armature].matrix_world @ blender_bone.bone.matrix_local
            axis_basis_change = Matrix.Identity(4)
            if self.export_settings[gltf2_blender_export_keys.YUP]:
                axis_basis_change = Matrix(
                    ((1.0, 0.0, 0.0, 0.0), (0.0, 0.0, 1.0, 0.0), (0.0, -1.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0)))
            node.matrix_world = node.matrix_world @ axis_basis_change

        # Force empty ?
        # For duplis, if instancer is not display, we should create an empty
        if blender_object.is_instancer is True and blender_object.show_instancer_for_render is False:
            node.force_as_empty = True

        # Storing this node
        self.add_node(node)

        ###### Manage children ######

        # standard children
        if blender_bone is None and blender_object.is_instancer is False:
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
            for dupli_object in blender_object.instance_collection.all_objects:
                if dupli_object.parent is not None:
                    continue
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

        # Duplis
        if blender_object.is_instancer is True and blender_object.instance_type != 'COLLECTION':
            depsgraph = bpy.context.evaluated_depsgraph_get()
            for (dupl, mat) in [(dup.object.original, dup.matrix_world.copy()) for dup in depsgraph.object_instances if dup.parent and id(dup.parent.original) == id(blender_object)]:
                self.recursive_node_traverse(dupl, None, node.uuid, parent_coll_matrix_world, dupli_world_matrix=mat)

    def get_all_objects(self):
        return [n.uuid for n in self.nodes.values() if n.blender_type != VExportNode.BONE]

    def get_all_bones(self, uuid): #For armatue Only
        if self.nodes[uuid].blender_type == VExportNode.ARMATURE:
            def recursive_get_all_bones(uuid):
                total = []
                if self.nodes[uuid].blender_type == VExportNode.BONE:
                    total.append(uuid)
                    for child_uuid in self.nodes[uuid].children:
                        total.extend(recursive_get_all_bones(child_uuid))

                return total

            tot = []
            for c_uuid in self.nodes[uuid].children:
                tot.extend(recursive_get_all_bones(c_uuid))
            return tot
        else:
            return []

    def get_all_node_of_type(self, node_type):
        return [n.uuid for n in self.nodes.values() if n.blender_type == node_type]

    def display(self, mode):
        if mode == "simple":
            for n in self.roots:
                print("Root", self.nodes[n].blender_object.name, "/", self.nodes[n].blender_bone.name if self.nodes[n].blender_bone else "" )
                self.nodes[n].recursive_display(self, mode)


    def filter_tag(self):
        roots = self.roots.copy()
        for r in roots:
            self.recursive_filter_tag(r, None)

    def filter_perform(self):
        roots = self.roots.copy()
        for r in roots:
            self.recursive_filter(r, None) # Root, so no parent

    def filter(self):
        self.filter_tag()
        export_user_extensions('gather_tree_filter_tag_hook', self.export_settings, self)
        self.filter_perform()


    def recursive_filter_tag(self, uuid, parent_keep_tag):
        # parent_keep_tag is for collection instance
        # some properties (selection, visibility, renderability)
        # are defined at collection level, and we need to use these values
        # for all objects of the collection instance.
        # But some properties (camera, lamp ...) are not defined at collection level
        if parent_keep_tag is None:
            self.nodes[uuid].keep_tag = self.node_filter_not_inheritable_is_kept(uuid) and self.node_filter_inheritable_is_kept(uuid)
        elif parent_keep_tag is True:
            self.nodes[uuid].keep_tag = self.node_filter_not_inheritable_is_kept(uuid)
        elif parent_keep_tag is False:
            self.nodes[uuid].keep_tag = False
        else:
            print("This should not happen!")

        for child in self.nodes[uuid].children:
            if self.nodes[uuid].blender_type == VExportNode.COLLECTION:
                self.recursive_filter_tag(child, self.nodes[uuid].keep_tag)
            else:
                self.recursive_filter_tag(child, parent_keep_tag)

    def recursive_filter(self, uuid, parent_kept_uuid):
        children = self.nodes[uuid].children.copy()

        new_parent_kept_uuid = None
        if self.nodes[uuid].keep_tag is False:
            new_parent_kept_uuid = parent_kept_uuid
            # Need to modify tree
            if self.nodes[uuid].parent_uuid is not None:
                self.nodes[self.nodes[uuid].parent_uuid].children.remove(uuid)
            else:
                # Remove from root
                self.roots.remove(uuid)
        else:
            new_parent_kept_uuid = uuid

            # If parent_uuid is not parent_kept_uuid, we need to modify children list of parent_kept_uuid
            if parent_kept_uuid != self.nodes[uuid].parent_uuid and parent_kept_uuid is not None:
                self.tree_troncated = True
                self.nodes[parent_kept_uuid].children.append(uuid)

            # If parent_kept_uuid is None, and parent_uuid was not, add to root list
            if self.nodes[uuid].parent_uuid is not None and parent_kept_uuid is None:
                self.tree_troncated = True
                self.roots.append(uuid)

            # Modify parent uuid
            self.nodes[uuid].parent_uuid = parent_kept_uuid

        for child in children:
            self.recursive_filter(child, new_parent_kept_uuid)


    def node_filter_not_inheritable_is_kept(self, uuid):
        # Export Camera or not
        if self.nodes[uuid].blender_type == VExportNode.CAMERA:
            if self.export_settings[gltf2_blender_export_keys.CAMERAS] is False:
                return False

        # Export Lamp or not
        if self.nodes[uuid].blender_type == VExportNode.LIGHT:
            if self.export_settings[gltf2_blender_export_keys.LIGHTS] is False:
                return False

        # Export deform bones only
        if self.nodes[uuid].blender_type == VExportNode.BONE:
            if self.export_settings['gltf_def_bones'] is True and self.nodes[uuid].use_deform is False:
                # Check if bone has some objected parented to bone. We need to keep it in that case, even if this is not a def bone
                if len([c for c in self.nodes[uuid].children if self.nodes[c].blender_type != VExportNode.BONE]) != 0:
                    return True
                return False

        return True

    def node_filter_inheritable_is_kept(self, uuid):

        if self.export_settings[gltf2_blender_export_keys.SELECTED] and self.nodes[uuid].blender_object.select_get() is False:
            return False

        if self.export_settings[gltf2_blender_export_keys.VISIBLE]:
            # The eye in outliner (object)
            if self.nodes[uuid].blender_object.visible_get() is False:
                return False

            # The screen in outliner (object)
            if self.nodes[uuid].blender_object.hide_viewport is True:
                return False

            # The screen in outliner (collections)
            if all([c.hide_viewport for c in self.nodes[uuid].blender_object.users_collection]):
                return False

        # The camera in outliner (object)
        if self.export_settings[gltf2_blender_export_keys.RENDERABLE]:
            if self.nodes[uuid].blender_object.hide_render is True:
                return False

            # The camera in outliner (collections)
            if all([c.hide_render for c in self.nodes[uuid].blender_object.users_collection]):
                return False

        if self.export_settings[gltf2_blender_export_keys.ACTIVE_COLLECTION]:
            found = any(x == self.nodes[uuid].blender_object for x in bpy.context.collection.all_objects)
            if not found:
                return False

        return True

    def search_missing_armature(self):
        for n in [n for n in self.nodes.values() if hasattr(n, "armature_needed") is True]:
            candidates = [i for i in self.nodes.values() if i.blender_type == VExportNode.ARMATURE and i.blender_object.name == n.armature_needed]
            if len(candidates) > 0:
                n.armature = candidates[0].uuid
            del n.armature_needed

    def add_neutral_bones(self):
        for n in [n for n in self.nodes.values() if n.armature is not None and n.blender_type == VExportNode.OBJECT and hasattr(self.nodes[n.armature], "need_neutral_bone")]: #all skin meshes objects where neutral bone is needed
            # First add a new node

            axis_basis_change = Matrix.Identity(4)
            if self.export_settings[gltf2_blender_export_keys.YUP]:
                axis_basis_change = Matrix(((1.0, 0.0, 0.0, 0.0), (0.0, 0.0, 1.0, 0.0), (0.0, -1.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0)))

            trans, rot, sca = axis_basis_change.decompose()
            translation, rotation, scale = (None, None, None)
            if trans[0] != 0.0 or trans[1] != 0.0 or trans[2] != 0.0:
                translation = [trans[0], trans[1], trans[2]]
            if rot[0] != 1.0 or rot[1] != 0.0 or rot[2] != 0.0 or rot[3] != 0.0:
                rotation = [rot[1], rot[2], rot[3], rot[0]]
            if sca[0] != 1.0 or sca[1] != 1.0 or sca[2] != 1.0:
                scale = [sca[0], sca[1], sca[2]]
            neutral_bone = gltf2_io.Node(
                            camera=None,
                            children=None,
                            extensions=None,
                            extras=None,
                            matrix=None,
                            mesh=None,
                            name='neutral_bone',
                            rotation=rotation,
                            scale=scale,
                            skin=None,
                            translation=translation,
                            weights=None
                        )
            # Add it to child list of armature
            self.nodes[n.armature].node.children.append(neutral_bone)
            # Add it to joint list
            n.node.skin.joints.append(neutral_bone)

            # Need to add an InverseBindMatrix
            array = BinaryData.decode_accessor_internal(n.node.skin.inverse_bind_matrices)

            axis_basis_change = Matrix.Identity(4)
            if self.export_settings[gltf2_blender_export_keys.YUP]:
                axis_basis_change = Matrix(
                    ((1.0, 0.0, 0.0, 0.0), (0.0, 0.0, 1.0, 0.0), (0.0, -1.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0)))

            inverse_bind_matrix = (
                axis_basis_change @ self.nodes[n.armature].matrix_world_armature).inverted_safe()

            matrix = []
            for column in range(0, 4):
                for row in range(0, 4):
                        matrix.append(inverse_bind_matrix[row][column])

            array = np.append(array, np.array([matrix]), axis=0)
            binary_data = gltf2_io_binary_data.BinaryData.from_list(array.flatten(), gltf2_io_constants.ComponentType.Float)
            n.node.skin.inverse_bind_matrices = gltf2_blender_gather_accessors.gather_accessor(
                binary_data,
                gltf2_io_constants.ComponentType.Float,
                len(array.flatten()) // gltf2_io_constants.DataType.num_elements(gltf2_io_constants.DataType.Mat4),
                None,
                None,
                gltf2_io_constants.DataType.Mat4,
                self.export_settings
            )
    def get_unused_skins(self):
        from .gltf2_blender_gather_skins import gather_skin
        skins = []
        for n in [n for n in self.nodes.values() if n.blender_type == VExportNode.ARMATURE]:
            if len([m for m in self.nodes.values() if m.keep_tag is True and m.blender_type == VExportNode.OBJECT and m.armature == n.uuid]) == 0:
                skin = gather_skin(n.uuid, self.export_settings)
                skins.append(skin)
        return skins
