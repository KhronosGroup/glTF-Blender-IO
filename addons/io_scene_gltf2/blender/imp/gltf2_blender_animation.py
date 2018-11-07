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

from .gltf2_blender_animation_bone import *
from .gltf2_blender_animation_node import *


class BlenderAnimation():

    @staticmethod
    def anim(gltf, anim_idx, node_idx):
        if gltf.data.nodes[node_idx].is_joint:
            BlenderBoneAnim.anim(gltf, anim_idx, node_idx)
        else:
            BlenderNodeAnim.anim(gltf, anim_idx, node_idx)

        if gltf.data.nodes[node_idx].children:
            for child in gltf.data.nodes[node_idx].children:
                BlenderAnimation.anim(gltf, anim_idx, child)
