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

from ...io.imp.gltf2_io_binary import BinaryData
from .gltf2_blender_animation_utils import make_fcurve


class BlenderWeightAnim():
    """Blender ShapeKey Animation."""
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("%s should not be instantiated" % cls)

    @staticmethod
    def anim(gltf, anim_idx, vnode_id):
        """Manage animation."""
        vnode = gltf.vnodes[vnode_id]

        node_idx = vnode.mesh_node_idx
        if node_idx is None:
            return

        node = gltf.data.nodes[node_idx]
        obj = vnode.blender_object
        fps = bpy.context.scene.render.fps

        animation = gltf.data.animations[anim_idx]

        if anim_idx not in node.animations.keys():
            return

        for channel_idx in node.animations[anim_idx]:
            channel = animation.channels[channel_idx]
            if channel.target.path == "weights":
                break
        else:
            return

        name = animation.track_name + "_" + obj.name
        action = bpy.data.actions.new(name)
        action.id_root = "KEY"
        gltf.needs_stash.append((obj.data.shape_keys, action))

        keys = BinaryData.get_data_from_accessor(gltf, animation.samplers[channel.sampler].input)
        values = BinaryData.get_data_from_accessor(gltf, animation.samplers[channel.sampler].output)

        # retrieve number of targets
        pymesh = gltf.data.meshes[gltf.data.nodes[node_idx].mesh]
        nb_targets = len(pymesh.shapekey_names)

        if animation.samplers[channel.sampler].interpolation == "CUBICSPLINE":
            offset = nb_targets
            stride = 3 * nb_targets
        else:
            offset = 0
            stride = nb_targets

        coords = [0] * (2 * len(keys))
        coords[::2] = (key[0] * fps for key in keys)

        for sk in range(nb_targets):
            if pymesh.shapekey_names[sk] is not None: # Do not animate shapekeys not created
                coords[1::2] = (values[offset + stride * i + sk][0] for i in range(len(keys)))
                kb_name = pymesh.shapekey_names[sk]
                data_path = 'key_blocks["%s"].value' % bpy.utils.escape_identifier(kb_name)

                make_fcurve(
                    action,
                    coords,
                    data_path=data_path,
                    group_name="ShapeKeys",
                    interpolation=animation.samplers[channel.sampler].interpolation,
                )

                # Expand weight range if needed
                kb = obj.data.shape_keys.key_blocks[kb_name]
                min_weight = min(coords[1:2])
                max_weight = max(coords[1:2])
                if min_weight < kb.slider_min: kb.slider_min = min_weight
                if max_weight > kb.slider_max: kb.slider_max = max_weight
