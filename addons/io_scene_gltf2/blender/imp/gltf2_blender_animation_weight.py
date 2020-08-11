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

import json
import bpy
import numpy as np

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

        keys = BinaryData.decode_accessor(gltf, animation.samplers[channel.sampler].input)
        values = BinaryData.decode_accessor(gltf, animation.samplers[channel.sampler].output)
        keys = keys.reshape(len(keys))
        values = values.reshape(len(values))

        # retrieve number of targets
        pymesh = gltf.data.meshes[gltf.data.nodes[node_idx].mesh]
        nb_targets = len(pymesh.shapekey_names)

        if animation.samplers[channel.sampler].interpolation == "CUBICSPLINE":
            # one frame is packed as in,in,in,val,val,val,out,out,out
            offset = nb_targets
            stride = 3 * nb_targets
        else:
            offset = 0
            stride = nb_targets

        coords = np.empty((2 * len(keys)), dtype=np.float32)
        coords[::2] = keys
        coords[::2] *= fps

        for sk in range(nb_targets):
            if pymesh.shapekey_names[sk] is not None: # Do not animate shapekeys not created
                coords[1::2] = values[sk + offset::stride]
                kb_name = pymesh.shapekey_names[sk]
                data_path = "key_blocks[" + json.dumps(kb_name) + "].value"

                make_fcurve(
                    action,
                    coords,
                    data_path=data_path,
                    group_name="ShapeKeys",
                    interpolation=animation.samplers[channel.sampler].interpolation,
                )
