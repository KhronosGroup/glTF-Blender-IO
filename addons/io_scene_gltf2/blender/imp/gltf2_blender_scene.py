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
from math import sqrt
from mathutils import Quaternion
from .gltf2_blender_node import BlenderNode
from .gltf2_blender_skin import BlenderSkin
from .gltf2_blender_animation import BlenderAnimation
from .gltf2_blender_animation_utils import simulate_stash
from .gltf2_blender_vnode import VNode, compute_vnodes


class BlenderScene():
    """Blender Scene."""
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("%s should not be instantiated" % cls)

    @staticmethod
    def create(gltf):
        """Scene creation."""
        scene = bpy.context.scene
        gltf.blender_scene = scene.name
        if bpy.app.version < (2, 80, 0):
            pass
        else:
            if bpy.context.collection.name in bpy.data.collections: # avoid master collection
                gltf.blender_active_collection = bpy.context.collection.name

        compute_vnodes(gltf)

        BlenderNode.create_vnode(gltf, 'root')

        # Now that all mesh / bones are created, create vertex groups on mesh
        if gltf.data.skins:
            BlenderSkin.create_vertex_groups(gltf)
            BlenderSkin.create_armature_modifiers(gltf)

        BlenderScene.create_animations(gltf)

        if bpy.app.debug_value != 100:
            # TODO: get rid of this by applying the conversions when we read from the glTF
            BlenderScene.add_yup2zup(gltf)

        if bpy.app.version < (2, 80, 0):
            scene.render.engine = "CYCLES"
        else:
            if scene.render.engine not in ['CYCLES', 'BLENDER_EEVEE']:
                scene.render.engine = "BLENDER_EEVEE"

    @staticmethod
    def create_animations(gltf):
        """Create animations."""
        if gltf.data.animations:
            for anim_idx, anim in enumerate(gltf.data.animations):
                # Blender armature name -> action all its bones should use
                gltf.arma_cache = {}
                # Things we need to stash when we're done.
                gltf.needs_stash = []

                BlenderAnimation.anim(gltf, anim_idx, 'root')

                for (obj, anim_name, action) in gltf.needs_stash:
                    simulate_stash(obj, anim_name, action)

            # Restore first animation
            anim_name = gltf.data.animations[0].track_name
            BlenderAnimation.restore_animation(gltf, 'root', anim_name)

    @staticmethod
    def add_yup2zup(gltf):
        # Create Yup2Zup empty
        obj_rotation = bpy.data.objects.new("Yup2Zup", None)
        obj_rotation.rotation_mode = 'QUATERNION'
        obj_rotation.rotation_quaternion = Quaternion((sqrt(2) / 2, sqrt(2) / 2, 0.0, 0.0))

        if bpy.app.version < (2, 80, 0):
            bpy.data.scenes[gltf.blender_scene].objects.link(obj_rotation)
        else:
            bpy.data.scenes[gltf.blender_scene].collection.objects.link(obj_rotation)

        if gltf.vnodes['root'].type == VNode.DummyRoot:
            for child in gltf.vnodes['root'].children:
                gltf.vnodes[child].blender_object.parent = obj_rotation
        else:
            gltf.vnodes['root'].blender_object.parent = obj_rotation
