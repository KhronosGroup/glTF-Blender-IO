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
from mathutils import Vector

from ..com.gltf2_blender_conversion import loc_gltf_to_blender, quaternion_gltf_to_blender, scale_gltf_to_blender
from ..com.gltf2_blender_conversion import correction_rotation
from ...io.imp.gltf2_io_binary import BinaryData
from .gltf2_blender_animation_utils import simulate_stash, restore_last_action


class BlenderNodeAnim():
    """Blender Object Animation."""
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("%s should not be instantiated" % cls)

    @staticmethod
    def set_interpolation(interpolation, kf):
        """Manage interpolation."""
        if interpolation == "LINEAR":
            kf.interpolation = 'LINEAR'
        elif interpolation == "STEP":
            kf.interpolation = 'CONSTANT'
        elif interpolation == "CUBICSPLINE":
            kf.interpolation = 'BEZIER'
            kf.handle_right_type = 'AUTO'
            kf.handle_left_type = 'AUTO'
        else:
            kf.interpolation = 'LINEAR'

    @staticmethod
    def stash_action(gltf, anim_idx, node_idx, action_name):
        node = gltf.data.nodes[node_idx]
        obj = bpy.data.objects[node.blender_object]

        if anim_idx not in node.animations.keys():
            return

        if (obj.name, action_name) in gltf.actions_stashed.keys():
            return

        start_frame = bpy.context.scene.frame_start

        simulate_stash(obj, bpy.data.actions[action_name], start_frame)

        gltf.actions_stashed[(obj.name, action_name)] = True

    @staticmethod
    def restore_last_action(gltf, node_idx):
        node = gltf.data.nodes[node_idx]
        obj = bpy.data.objects[node.blender_object]

        restore_last_action(obj)

    @staticmethod
    def anim(gltf, anim_idx, node_idx):
        """Manage animation."""
        node = gltf.data.nodes[node_idx]
        obj = bpy.data.objects[node.blender_object]
        fps = bpy.context.scene.render.fps

        if anim_idx not in node.animations.keys():
            return

        animation = gltf.data.animations[anim_idx]

        if animation.name:
            name = animation.name + "_" + obj.name
        else:
            name = "Animation_" + str(anim_idx) + "_" + obj.name
        if len(name) >= 63:
            # Name is too long to be kept, we are going to keep only animation name for now
            name = animation.name
            if len(name) >= 63:
                # Very long name!
                name = "Animation_" + str(anim_idx)
        action = bpy.data.actions.new(name)
        # Check if this action has some users.
        # If no user (only 1 indeed), that means that this action must be deleted
        # (is an action from a deleted object)
        if action.users == 1:
            bpy.data.actions.remove(action)
            action = bpy.data.actions.new(name)
        if not obj.animation_data:
            obj.animation_data_create()
        obj.animation_data.action = bpy.data.actions[action.name]

        for channel_idx in node.animations[anim_idx]:
            channel = animation.channels[channel_idx]

            keys = BinaryData.get_data_from_accessor(gltf, animation.samplers[channel.sampler].input)
            values = BinaryData.get_data_from_accessor(gltf, animation.samplers[channel.sampler].output)

            if channel.target.path in ['translation', 'rotation', 'scale']:

                # There is an animation on object
                # We can't remove Yup2Zup oject
                gltf.animation_object = True

                if animation.samplers[channel.sampler].interpolation == "CUBICSPLINE":
                    # TODO manage tangent?
                    values = [values[idx * 3 + 1] for idx in range(0, len(keys))]

                if channel.target.path == "translation":
                    blender_path = "location"
                    group_name = "Location"
                    num_components = 3
                    values = [loc_gltf_to_blender(vals) for vals in values]

                elif channel.target.path == "rotation":
                    blender_path = "rotation_quaternion"
                    group_name = "Rotation"
                    num_components = 4
                    if node.correction_needed is True:
                        if bpy.app.version < (2, 80, 0):
                            values = [
                                (quaternion_gltf_to_blender(vals).to_matrix().to_4x4() * correction_rotation()).to_quaternion()
                                for vals in values
                            ]
                        else:
                            values = [
                                (quaternion_gltf_to_blender(vals).to_matrix().to_4x4() @ correction_rotation()).to_quaternion()
                                for vals in values
                            ]
                    else:
                        values = [quaternion_gltf_to_blender(vals) for vals in values]


                    # Manage antipodal quaternions
                    for i in range(1, len(values)):
                        if values[i].dot(values[i-1]) < 0:
                            values[i] = -values[i]

                elif channel.target.path == "scale":
                    blender_path = "scale"
                    group_name = "Scale"
                    num_components = 3
                    values = [scale_gltf_to_blender(vals) for vals in values]

                coords = [0] * (2 * len(keys))
                coords[::2] = (key[0] * fps for key in keys)

                if group_name not in action.groups:
                    action.groups.new(group_name)
                group = action.groups[group_name]

                for i in range(0, num_components):
                    fcurve = action.fcurves.new(data_path=blender_path, index=i)
                    fcurve.group = group

                    fcurve.keyframe_points.add(len(keys))
                    coords[1::2] = (vals[i] for vals in values)
                    fcurve.keyframe_points.foreach_set('co', coords)

                    # Setting interpolation
                    for kf in fcurve.keyframe_points:
                        BlenderNodeAnim.set_interpolation(animation.samplers[channel.sampler].interpolation, kf)
                    fcurve.update() # force updating tangents (this may change when tangent will be managed)

            elif channel.target.path == 'weights':

                # retrieve number of targets
                nb_targets = 0
                for prim in gltf.data.meshes[gltf.data.nodes[node_idx].mesh].primitives:
                    if prim.targets:
                        if len(prim.targets) > nb_targets:
                            nb_targets = len(prim.targets)

                if animation.samplers[channel.sampler].interpolation == "CUBICSPLINE":
                    factor = 3
                    delta = len(keys)
                else:
                    factor = 1
                    delta = 0

                for idx, key in enumerate(keys):
                    for sk in range(nb_targets):
                        if gltf.shapekeys[sk] is not None: # Do not animate shapekeys not created
                            obj.data.shape_keys.key_blocks[gltf.shapekeys[sk]].value = values[idx * nb_targets + sk][0]
                            obj.data.shape_keys.key_blocks[gltf.shapekeys[sk]].keyframe_insert(
                                "value",
                                frame=key[0] * fps,
                                group='ShapeKeys'
                            )

        if action.name not in gltf.current_animation_names.keys():
            gltf.current_animation_names[name] = action.name
