# Copyright 2018-2021 The glTF-Blender-IO authors.
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

from .gltf2_blender_node import BlenderNode
from .gltf2_blender_animation import BlenderAnimation
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

        BlenderScene.create_animations(gltf)

        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        BlenderScene.select_imported_objects(gltf)
        BlenderScene.set_active_object(gltf)

    @staticmethod
    def create_animations(gltf):
        """Create animations."""
        if gltf.data.animations:
            # NLA tracks are added bottom to top, so create animations in
            # reverse so the first winds up on top
            for anim_idx in reversed(range(len(gltf.data.animations))):
                BlenderAnimation.anim(gltf, anim_idx)

            # Restore first animation
            anim_name = gltf.data.animations[0].track_name
            BlenderAnimation.restore_animation(gltf, anim_name)

    @staticmethod
    def select_imported_objects(gltf):
        """Select all (and only) the imported objects."""
        if bpy.ops.object.select_all.poll():
           bpy.ops.object.select_all(action='DESELECT')

        for vnode in gltf.vnodes.values():
            if vnode.type == VNode.Object:
                vnode.blender_object.select_set(state=True)

    @staticmethod
    def set_active_object(gltf):
        """Make the first root object from the default glTF scene active.
        If no default scene, use the first scene, or just any root object.
        """
        vnode = None

        if gltf.data.scene is not None:
            pyscene = gltf.data.scenes[gltf.data.scene]
            if pyscene.nodes:
                vnode = gltf.vnodes[pyscene.nodes[0]]

        if not vnode:
            for pyscene in gltf.data.scenes or []:
                if pyscene.nodes:
                    vnode = gltf.vnodes[pyscene.nodes[0]]
                    break

        if not vnode:
            vnode = gltf.vnodes['root']
            if vnode.type == VNode.DummyRoot:
                if not vnode.children:
                    return  # no nodes
                vnode = gltf.vnodes[vnode.children[0]]

        if vnode.type == VNode.Bone:
            vnode = gltf.vnodes[vnode.bone_arma]

        bpy.context.view_layer.objects.active = vnode.blender_object
