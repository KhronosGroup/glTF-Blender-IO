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
from math import sqrt
from mathutils import Quaternion
from .gltf2_blender_node import BlenderNode
from .gltf2_blender_skin import BlenderSkin
from .gltf2_blender_animation import BlenderAnimation


class BlenderScene():
    """Blender Scene."""
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("%s should not be instantiated" % cls)

    @staticmethod
    def create(gltf, scene_idx):
        """Scene creation."""
        pyscene = gltf.data.scenes[scene_idx]

    # Create a new scene only if not already exists in .blend file
    # TODO : put in current scene instead ?
        if pyscene.name not in [scene.name for scene in bpy.data.scenes]:
            # TODO: There is a bug in 2.8 alpha that break CLEAR_KEEP_TRANSFORM
            # if we are creating a new scene
            if bpy.app.version < (2, 80, 0):
                if pyscene.name:
                    scene = bpy.data.scenes.new(pyscene.name)
                else:
                    scene = bpy.context.scene
            else:
                scene = bpy.context.scene
            if bpy.app.version < (2, 80, 0):
                scene.render.engine = "CYCLES"
            else:
                scene.render.engine = "BLENDER_EEVEE"

            gltf.blender_scene = scene.name
        else:
            gltf.blender_scene = pyscene.name

        # Create Yup2Zup empty
        obj_rotation = bpy.data.objects.new("Yup2Zup", None)
        obj_rotation.rotation_mode = 'QUATERNION'
        obj_rotation.rotation_quaternion = Quaternion((sqrt(2) / 2, sqrt(2) / 2, 0.0, 0.0))

        if bpy.app.version < (2, 80, 0):
            bpy.data.scenes[gltf.blender_scene].objects.link(obj_rotation)
        else:
            bpy.data.scenes[gltf.blender_scene].collection.objects.link(obj_rotation)

        if pyscene.nodes is not None:
            for node_idx in pyscene.nodes:
                BlenderNode.create(gltf, node_idx, None)  # None => No parent

        # Now that all mesh / bones are created, create vertex groups on mesh
        if gltf.data.skins:
            for skin_id, skin in enumerate(gltf.data.skins):
                if hasattr(skin, "node_ids"):
                    BlenderSkin.create_vertex_groups(gltf, skin_id)

            for skin_id, skin in enumerate(gltf.data.skins):
                if hasattr(skin, "node_ids"):
                    BlenderSkin.assign_vertex_groups(gltf, skin_id)

            for skin_id, skin in enumerate(gltf.data.skins):
                if hasattr(skin, "node_ids"):
                    BlenderSkin.create_armature_modifiers(gltf, skin_id)

        if gltf.data.animations:
            for anim_idx, anim in enumerate(gltf.data.animations):
                for node_idx in pyscene.nodes:
                    BlenderAnimation.anim(gltf, anim_idx, node_idx)

        # Parent root node to rotation object
        if pyscene.nodes is not None:
            for node_idx in pyscene.nodes:
                bpy.data.objects[gltf.data.nodes[node_idx].blender_object].parent = obj_rotation

            if gltf.animation_object is False:

                if bpy.app.version < (2, 80, 0):
                    for node_idx in pyscene.nodes:
                        for obj_ in bpy.context.scene.objects:
                            obj_.select = False
                        bpy.data.objects[gltf.data.nodes[node_idx].blender_object].select = True
                        bpy.context.scene.objects.active = bpy.data.objects[gltf.data.nodes[node_idx].blender_object]
                        bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')

                    # remove object
                    bpy.context.scene.objects.unlink(obj_rotation)
                    bpy.data.objects.remove(obj_rotation)
                else:
                    for node_idx in pyscene.nodes:
                        for obj_ in bpy.context.scene.objects:
                            obj_.select_set(False)
                        bpy.data.objects[gltf.data.nodes[node_idx].blender_object].select_set(True)
                        bpy.context.view_layer.objects.active = bpy.data.objects[gltf.data.nodes[node_idx].blender_object]

                        bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')

                    # remove object
                    bpy.context.scene.collection.objects.unlink(obj_rotation)
                    bpy.data.objects.remove(obj_rotation)
