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

from .gltf2_blender_animation_bone import BlenderBoneAnim
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
            if gltf.vnodes[vnode_id].type == VNode.Bone:
                BlenderBoneAnim.anim(gltf, anim_idx, vnode_id)
            elif gltf.vnodes[vnode_id].type == VNode.Object:
                BlenderNodeAnim.anim(gltf, anim_idx, vnode_id)

        BlenderWeightAnim.anim(gltf, anim_idx, vnode_id)

        for child in gltf.vnodes[vnode_id].children:
            BlenderAnimation.anim(gltf, anim_idx, child)

    @staticmethod
    def restore_animation(gltf, animation_name):
        """Restore the actions for an animation by its track name."""
        frame_end = 0

        for vnode in gltf.vnodes.values():
            if vnode.type == VNode.Object:
                obj = vnode.blender_object
            else:
                continue

            action = restore_animation_on_object(obj, animation_name)
            if action is not None:
                frame_end = max(frame_end, action.frame_range[1])

            if obj.data and hasattr(obj.data, 'shape_keys'):
                action = restore_animation_on_object(obj.data.shape_keys, animation_name)
                if action is not None:
                    frame_end = max(frame_end, action.frame_range[1])

        bpy.context.scene.frame_start = 0
        bpy.context.scene.frame_end = frame_end

