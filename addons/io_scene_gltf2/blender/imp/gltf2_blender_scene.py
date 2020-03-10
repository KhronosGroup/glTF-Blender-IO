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
        if bpy.context.collection.name in bpy.data.collections: # avoid master collection
            gltf.blender_active_collection = bpy.context.collection.name
        if scene.render.engine not in ['CYCLES', 'BLENDER_EEVEE']:
            scene.render.engine = "BLENDER_EEVEE"

        compute_vnodes(gltf)

        gltf.display_current_node = 0  # for debugging
        BlenderNode.create_vnode(gltf, 'root')

        # Now that all mesh / bones are created, create vertex groups on mesh
        if gltf.data.skins:
            BlenderSkin.create_vertex_groups(gltf)
            BlenderSkin.create_armature_modifiers(gltf)

        BlenderScene.create_animations(gltf)

        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        BlenderScene.set_active_object(gltf)

    @staticmethod
    def create_animations(gltf):
        """Create animations."""
        if gltf.data.animations:
            for anim_idx, anim in enumerate(gltf.data.animations):
                # Caches the action for each object (keyed by object name)
                gltf.action_cache = {}
                # Things we need to stash when we're done.
                gltf.needs_stash = []

                BlenderAnimation.anim(gltf, anim_idx, 'root')

                for (obj, anim_name, action) in gltf.needs_stash:
                    simulate_stash(obj, anim_name, action)

            # Restore first animation
            anim_name = gltf.data.animations[0].track_name
            BlenderAnimation.restore_animation(gltf, 'root', anim_name)

    @staticmethod
    def set_active_object(gltf):
        """Make the first root object from the default glTF scene active.
        If no default scene, use the first scene, or just any root object.
        """
        if gltf.data.scenes:
            pyscene = gltf.data.scenes[gltf.data.scene or 0]
            vnode = gltf.vnodes[pyscene.nodes[0]]
            if gltf.vnodes[vnode.parent].type != VNode.DummyRoot:
                vnode = gltf.vnodes[vnode.parent]

        else:
            vnode = gltf.vnodes['root']
            if vnode.type == VNode.DummyRoot:
                if not vnode.children:
                    return  # no nodes
                vnode = gltf.vnodes[vnode.children[0]]

        bpy.context.view_layer.objects.active = vnode.blender_object
