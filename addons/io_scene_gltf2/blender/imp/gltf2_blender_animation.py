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

from .gltf2_blender_animation_node import BlenderNodeAnim
from .gltf2_blender_animation_weight import BlenderWeightAnim
from .gltf2_blender_animation_utils import restore_animation_on_object
from .gltf2_blender_vnode import VNode


class BlenderAnimation():
    """Dispatch Animation to bone or object animation."""
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("%s should not be instantiated" % cls)

    @staticmethod
    def anim(gltf, anim_idx, vnode_id):
        """Dispatch Animation to bone or object."""
        if isinstance(vnode_id, int):
            BlenderNodeAnim.anim(gltf, anim_idx, vnode_id)

        BlenderWeightAnim.anim(gltf, anim_idx, vnode_id)

        for child in gltf.vnodes[vnode_id].children:
            BlenderAnimation.anim(gltf, anim_idx, child)

    @staticmethod
    def restore_animation(gltf, vnode_id, animation_name):
        """Restores the actions for an animation by its track name on
        the subtree starting at node_idx."""
        vnode = gltf.vnodes[vnode_id]

        obj = None
        if vnode.type == VNode.Bone:
            obj = gltf.vnodes[vnode.bone_arma].blender_object
        elif vnode.type == VNode.Object:
            obj = vnode.blender_object

        if obj is not None:
            restore_animation_on_object(obj, animation_name)
            if obj.data and hasattr(obj.data, 'shape_keys'):
                restore_animation_on_object(obj.data.shape_keys, animation_name)

        for child in gltf.vnodes[vnode_id].children:
            BlenderAnimation.restore_animation(gltf, child, animation_name)
