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
from .gltf2_blender_mesh import BlenderMesh
from .gltf2_blender_camera import BlenderCamera
from .gltf2_blender_skin import BlenderSkin
from .gltf2_blender_light import BlenderLight
from ..com.gltf2_blender_conversion import scale_to_matrix, matrix_gltf_to_blender, correction_rotation


class BlenderNode():
    """Blender Node."""
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("%s should not be instantiated" % cls)

    @staticmethod
    def create(gltf, node_idx, parent):
        """Node creation."""
        pynode = gltf.data.nodes[node_idx]

        # Blender attributes initialization
        pynode.blender_object = ""
        pynode.parent = parent

        gltf.display_current_node += 1
        if bpy.app.debug_value == 101:
            gltf.log.critical("Node " + str(gltf.display_current_node) + " of " + str(gltf.display_total_nodes) + " (idx " + str(node_idx) + ")")

        if pynode.mesh is not None:

            instance = False
            if gltf.data.meshes[pynode.mesh].blender_name is not None:
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
                        mesh = bpy.data.meshes[gltf.data.meshes[pynode.mesh].blender_name]

            if instance is False:
                if pynode.name:
                    gltf.log.info("Blender create Mesh node " + pynode.name)
                else:
                    gltf.log.info("Blender create Mesh node")

                mesh = BlenderMesh.create(gltf, pynode.mesh, node_idx, parent)

            if pynode.weight_animation is True:
                # flag this mesh instance as created only for this node, because of weight animation
                gltf.data.meshes[pynode.mesh].is_weight_animated = True

            if pynode.name:
                name = pynode.name
            else:
                # Take mesh name if exist
                if gltf.data.meshes[pynode.mesh].name:
                    name = gltf.data.meshes[pynode.mesh].name
                else:
                    name = "Object_" + str(node_idx)

            obj = bpy.data.objects.new(name, mesh)
            obj.rotation_mode = 'QUATERNION'
            if bpy.app.version < (2, 80, 0):
                bpy.data.scenes[gltf.blender_scene].objects.link(obj)
            else:
                if gltf.blender_active_collection is not None:
                    bpy.data.collections[gltf.blender_active_collection].objects.link(obj)
                else:
                    bpy.data.scenes[gltf.blender_scene].collection.objects.link(obj)

            # Transforms apply only if this mesh is not skinned
            # See implementation node of gltf2 specification
            if not (pynode.mesh is not None and pynode.skin is not None):
                BlenderNode.set_transforms(gltf, node_idx, pynode, obj, parent)
            pynode.blender_object = obj.name
            BlenderNode.set_parent(gltf, obj, parent)

            if instance == False:
                BlenderMesh.set_mesh(gltf, gltf.data.meshes[pynode.mesh], mesh, obj)

            if pynode.children:
                for child_idx in pynode.children:
                    BlenderNode.create(gltf, child_idx, node_idx)

            return

        if pynode.camera is not None:
            if pynode.name:
                gltf.log.info("Blender create Camera node " + pynode.name)
            else:
                gltf.log.info("Blender create Camera node")
            obj = BlenderCamera.create(gltf, pynode.camera)
            BlenderNode.set_transforms(gltf, node_idx, pynode, obj, parent)  # TODO default rotation of cameras ?
            pynode.blender_object = obj.name
            BlenderNode.set_parent(gltf, obj, parent)

            if pynode.children:
                for child_idx in pynode.children:
                    BlenderNode.create(gltf, child_idx, node_idx)

            return

        if pynode.is_joint:
            if pynode.name:
                gltf.log.info("Blender create Bone node " + pynode.name)
            else:
                gltf.log.info("Blender create Bone node")
            # Check if corresponding armature is already created, create it if needed
            if gltf.data.skins[pynode.skin_id].blender_armature_name is None:
                BlenderSkin.create_armature(gltf, pynode.skin_id, parent)

            BlenderSkin.create_bone(gltf, pynode.skin_id, node_idx, parent)

            if pynode.children:
                for child_idx in pynode.children:
                    BlenderNode.create(gltf, child_idx, node_idx)

            return

        if pynode.extensions is not None:
            if 'KHR_lights_punctual' in pynode.extensions.keys():
                obj = BlenderLight.create(gltf, pynode.extensions['KHR_lights_punctual']['light'])
                obj.rotation_mode = 'QUATERNION'
                BlenderNode.set_transforms(gltf, node_idx, pynode, obj, parent, correction=True)
                pynode.blender_object = obj.name
                pynode.correction_needed = True
                BlenderNode.set_parent(gltf, obj, parent)

                if pynode.children:
                    for child_idx in pynode.children:
                        BlenderNode.create(gltf, child_idx, node_idx)

                return

        # No mesh, no camera, no light. For now, create empty #TODO

        if pynode.name:
            gltf.log.info("Blender create Empty node " + pynode.name)
            obj = bpy.data.objects.new(pynode.name, None)
        else:
            gltf.log.info("Blender create Empty node")
            obj = bpy.data.objects.new("Node", None)
        obj.rotation_mode = 'QUATERNION'
        if bpy.app.version < (2, 80, 0):
            bpy.data.scenes[gltf.blender_scene].objects.link(obj)
        else:
            if gltf.blender_active_collection is not None:
                bpy.data.collections[gltf.blender_active_collection].objects.link(obj)
            else:
                bpy.data.scenes[gltf.blender_scene].collection.objects.link(obj)

        BlenderNode.set_transforms(gltf, node_idx, pynode, obj, parent)
        pynode.blender_object = obj.name
        BlenderNode.set_parent(gltf, obj, parent)

        if pynode.children:
            for child_idx in pynode.children:
                BlenderNode.create(gltf, child_idx, node_idx)

    @staticmethod
    def set_parent(gltf, obj, parent):
        """Set parent."""
        if parent is None:
            return

        for node_idx, node in enumerate(gltf.data.nodes):
            if node_idx == parent:
                if node.is_joint is True:
                    bpy.ops.object.select_all(action='DESELECT')
                    if bpy.app.version < (2, 80, 0):
                        bpy.data.objects[node.blender_armature_name].select = True
                        bpy.context.scene.objects.active = bpy.data.objects[node.blender_armature_name]
                    else:
                        bpy.data.objects[node.blender_armature_name].select_set(True)
                        bpy.context.view_layer.objects.active = bpy.data.objects[node.blender_armature_name]

                    bpy.ops.object.mode_set(mode='EDIT')
                    bpy.data.objects[node.blender_armature_name].data.edit_bones.active = \
                        bpy.data.objects[node.blender_armature_name].data.edit_bones[node.blender_bone_name]
                    bpy.ops.object.mode_set(mode='OBJECT')
                    bpy.ops.object.select_all(action='DESELECT')
                    if bpy.app.version < (2, 80, 0):
                        obj.select = True
                        bpy.data.objects[node.blender_armature_name].select = True
                        bpy.context.scene.objects.active = bpy.data.objects[node.blender_armature_name]
                    else:
                        obj.select_set(True)
                        bpy.data.objects[node.blender_armature_name].select_set(True)
                        bpy.context.view_layer.objects.active = bpy.data.objects[node.blender_armature_name]
                    bpy.context.view_layer.update()
                    bpy.ops.object.parent_set(type='BONE_RELATIVE', keep_transform=True)
                    # From world transform to local (-armature transform -bone transform)
                    bone_trans = bpy.data.objects[node.blender_armature_name] \
                        .pose.bones[node.blender_bone_name].matrix.to_translation().copy()
                    bone_rot = bpy.data.objects[node.blender_armature_name] \
                        .pose.bones[node.blender_bone_name].matrix.to_quaternion().copy()
                    bone_scale_mat = scale_to_matrix(node.blender_bone_matrix.to_scale())
                    if bpy.app.version < (2, 80, 0):
                        obj.location = bone_scale_mat * obj.location
                        obj.location = bone_rot * obj.location
                        obj.location += bone_trans
                        obj.location = bpy.data.objects[node.blender_armature_name].matrix_world.to_quaternion() \
                            * obj.location
                        obj.rotation_quaternion = obj.rotation_quaternion \
                            * bpy.data.objects[node.blender_armature_name].matrix_world.to_quaternion()
                        obj.scale = bone_scale_mat * obj.scale
                    else:
                        obj.location = bone_scale_mat @ obj.location
                        obj.location = bone_rot @ obj.location
                        obj.location += bone_trans
                        obj.location = bpy.data.objects[node.blender_armature_name].matrix_world.to_quaternion() \
                            @ obj.location
                        obj.rotation_quaternion = obj.rotation_quaternion \
                            @ bpy.data.objects[node.blender_armature_name].matrix_world.to_quaternion()
                        obj.scale = bone_scale_mat @ obj.scale

                    return
                if node.blender_object:
                    obj.parent = bpy.data.objects[node.blender_object]
                    return

        gltf.log.error("ERROR, parent not found")

    @staticmethod
    def set_transforms(gltf, node_idx, pynode, obj, parent, correction=False):
        """Set transforms."""
        if parent is None:
            obj.matrix_world = matrix_gltf_to_blender(pynode.transform)
            if correction is True:
                if bpy.app.version < (2, 80, 0):
                    obj.matrix_world = obj.matrix_world * correction_rotation()
                else:
                    obj.matrix_world = obj.matrix_world @ correction_rotation()
            return

        for idx, node in enumerate(gltf.data.nodes):
            if idx == parent:
                if node.is_joint is True:
                    obj.matrix_world = matrix_gltf_to_blender(pynode.transform)
                    if correction is True:
                        if bpy.app.version < (2, 80, 0):
                            obj.matrix_world = obj.matrix_world * correction_rotation()
                        else:
                            obj.matrix_world = obj.matrix_world @ correction_rotation()
                    return
                else:
                    if correction is True:
                        if bpy.app.version < (2, 80, 0):
                            obj.matrix_world = obj.matrix_world * correction_rotation()
                        else:
                            obj.matrix_world = obj.matrix_world @ correction_rotation()
                    obj.matrix_world = matrix_gltf_to_blender(pynode.transform)
                    return
