# Copyright 2018-2019 The glTF-Blender-IO authors.
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
from mathutils import Vector
from ..com.gltf2_blender_extras import set_extras
from .gltf2_blender_mesh import BlenderMesh
from .gltf2_blender_camera import BlenderCamera
from .gltf2_blender_light import BlenderLight
from .gltf2_blender_vnode import VNode

class BlenderNode():
    """Blender Node."""
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("%s should not be instantiated" % cls)

    @staticmethod
    def create_vnode(gltf, vnode_id):
        """Create VNode and all its descendants."""
        vnode = gltf.vnodes[vnode_id]
        name = vnode.name

        if vnode.type == VNode.Object:
            BlenderNode.create_object(gltf, vnode_id)

        elif vnode.type == VNode.Bone:
            BlenderNode.create_bone(gltf, vnode_id)

        elif vnode.type == VNode.DummyRoot:
            # Don't actually create this
            vnode.blender_object = None

        for child in vnode.children:
            BlenderNode.create_vnode(gltf, child)

    @staticmethod
    def create_object(gltf, vnode_id):
        vnode = gltf.vnodes[vnode_id]

        if vnode.mesh_node_idx is not None:
            pynode = gltf.data.nodes[vnode.mesh_node_idx]
            obj = BlenderNode.create_mesh_object(gltf, pynode, name=vnode.name)
        elif vnode.camera_node_idx is not None:
            pynode = gltf.data.nodes[vnode.camera_node_idx]
            obj = BlenderCamera.create(gltf, pynode.camera)
        elif vnode.light_node_idx is not None:
            pynode = gltf.data.nodes[vnode.light_node_idx]
            obj = BlenderLight.create(gltf, pynode.extensions['KHR_lights_punctual']['light'])
        elif vnode.is_arma:
            armature = bpy.data.armatures.new(vnode.arma_name)
            obj = bpy.data.objects.new(vnode.name, armature)
        else:
            obj = bpy.data.objects.new(vnode.name, None)

        vnode.blender_object = obj

        # Set extras (if came from a glTF node)
        if isinstance(vnode_id, int):
            pynode = gltf.data.nodes[vnode_id]
            set_extras(obj, pynode.extras)

        # Set transform
        trans, rot, scale = vnode.trs
        obj.location = trans
        obj.rotation_mode = 'QUATERNION'
        obj.rotation_quaternion = rot
        obj.scale = scale

        # Set parent
        if vnode.parent is not None:
            parent_vnode = gltf.vnodes[vnode.parent]
            if parent_vnode.type == VNode.Object:
                obj.parent = parent_vnode.blender_object
            elif parent_vnode.type == VNode.Bone:
                arma_vnode = gltf.vnodes[parent_vnode.bone_arma]
                obj.parent = arma_vnode.blender_object
                obj.parent_type = 'BONE'
                obj.parent_bone = parent_vnode.blender_bone_name

                # Nodes with a bone parent need to be translated
                # backwards by their bone length (always 1 currently)
                obj.location += Vector((0, -1, 0))

        if bpy.app.version < (2, 80, 0):
            bpy.data.scenes[gltf.blender_scene].objects.link(obj)
        else:
            bpy.data.scenes[gltf.blender_scene].collection.objects.link(obj)

        return obj

    @staticmethod
    def create_bone(gltf, vnode_id):
        vnode = gltf.vnodes[vnode_id]
        blender_arma = gltf.vnodes[vnode.bone_arma].blender_object
        armature = blender_arma.data

        # Switch into edit mode to create edit bone
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        if bpy.app.version < (2, 80, 0):
            bpy.context.screen.scene = bpy.data.scenes[gltf.blender_scene]
            bpy.data.scenes[gltf.blender_scene].objects.active = blender_arma
        else:
            bpy.context.window.scene = bpy.data.scenes[gltf.blender_scene]
            bpy.context.view_layer.objects.active = blender_arma
        bpy.ops.object.mode_set(mode="EDIT")
        editbone = armature.edit_bones.new(vnode.name)
        vnode.blender_bone_name = editbone.name

        # Set extras (if came from a glTF node)
        if isinstance(vnode_id, int):
            pynode = gltf.data.nodes[vnode_id]
            set_extras(editbone, pynode.extras)

        # TODO
        editbone.use_connect = False

        # Give the position of the bone in armature space
        arma_mat = vnode.bone_arma_mat
        if bpy.app.version < (2, 80, 0):
            editbone.head = arma_mat * Vector((0, 0, 0))
            editbone.tail = arma_mat * Vector((0, 1, 0))
            editbone.align_roll(arma_mat * Vector((0, 0, 1)) - editbone.head)
        else:
            editbone.head = arma_mat @ Vector((0, 0, 0))
            editbone.tail = arma_mat @ Vector((0, 1, 0))
            editbone.align_roll(arma_mat @ Vector((0, 0, 1)) - editbone.head)

        # Set parent
        parent_vnode = gltf.vnodes[vnode.parent]
        if parent_vnode.type == VNode.Bone:
            editbone.parent = armature.edit_bones[parent_vnode.blender_bone_name]

        bpy.ops.object.mode_set(mode="OBJECT")
        pose_bone = blender_arma.pose.bones[vnode.blender_bone_name]

        # Put scale on the pose bone (can't go on the edit bone)
        _, _, s = vnode.trs
        pose_bone.scale = s

        if isinstance(vnode_id, int):
            pynode = gltf.data.nodes[vnode_id]
            set_extras(pose_bone, pynode.extras)

    @staticmethod
    def create_mesh_object(gltf, pynode, name):
        instance = False
        if gltf.data.meshes[pynode.mesh].blender_name.get(pynode.skin) is not None:
            # Mesh is already created, only create instance
            # Except is current node is animated with path weight
            # Or if previous instance is animation at node level
            if pynode.weight_animation is True:
                instance = False
            else:
                if gltf.data.meshes[pynode.mesh].is_weight_animated is True:
                    instance = False
                else:
                    instance = True
                    mesh = bpy.data.meshes[gltf.data.meshes[pynode.mesh].blender_name[pynode.skin]]

        if instance is False:
            if pynode.name:
                gltf.log.info("Blender create Mesh node " + pynode.name)
            else:
                gltf.log.info("Blender create Mesh node")

            mesh = BlenderMesh.create(gltf, pynode.mesh, pynode.skin)

        if pynode.weight_animation is True:
            # flag this mesh instance as created only for this node, because of weight animation
            gltf.data.meshes[pynode.mesh].is_weight_animated = True

        mesh_name = gltf.data.meshes[pynode.mesh].name
        if not name and mesh_name:
            name = mesh_name

        obj = bpy.data.objects.new(name, mesh)
        set_extras(obj, pynode.extras)
        obj.rotation_mode = 'QUATERNION'

        if instance == False:
            BlenderMesh.set_mesh(gltf, gltf.data.meshes[pynode.mesh], obj)

        return obj
