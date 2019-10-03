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


class BlenderAnimation():
    """Dispatch Animation to bone or object animation."""
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("%s should not be instantiated" % cls)

    @staticmethod
    def anim(gltf, anim_idx, node_idx):
        """Dispatch Animation to bone or object."""
        if gltf.data.nodes[node_idx].is_joint:
            BlenderBoneAnim.anim(gltf, anim_idx, node_idx)
        else:
            BlenderNodeAnim.anim(gltf, anim_idx, node_idx)
            BlenderWeightAnim.anim(gltf, anim_idx, node_idx)

        if gltf.data.nodes[node_idx].children:
            for child in gltf.data.nodes[node_idx].children:
                BlenderAnimation.anim(gltf, anim_idx, child)

    @staticmethod
    def restore_animation(gltf, node_idx, animation_name):
        """Restores the actions for an animation by its track name on
        the subtree starting at node_idx."""
        node = gltf.data.nodes[node_idx]

        if node.is_joint:
            obj = bpy.data.objects[gltf.data.skins[node.skin_id].blender_armature_name]
        else:
            obj = bpy.data.objects[node.blender_object]

        restore_animation_on_object(obj, animation_name)
        if obj.data and hasattr(obj.data, 'shape_keys'):
            restore_animation_on_object(obj.data.shape_keys, animation_name)

        if gltf.data.nodes[node_idx].children:
            for child in gltf.data.nodes[node_idx].children:
                BlenderAnimation.restore_animation(gltf, child, animation_name)
