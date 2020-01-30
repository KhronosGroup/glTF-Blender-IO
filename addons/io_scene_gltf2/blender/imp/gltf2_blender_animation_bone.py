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
from mathutils import Vector

from ...io.imp.gltf2_io_binary import BinaryData
from .gltf2_blender_animation_utils import simulate_stash, make_fcurve


# In Blender we animate a pose bone. The final TRS of the bone depends on
# both the edit bone and pose bone
#
#     Final = EditBone * PoseBone
#   where
#     Final =    Trans[ft] Rot[fr] Scale[fs]
#     EditBone = Trans[et] Rot[er]                (edit bones have no scale)
#     PoseBone = Trans[pt] Rot[pr] Scale[ps]
#
# Given Final we can solve for the PoseBone we need to use with
#
#     pt = Rot[er^{-1}] (ft - et)
#     pr = er^{-1} fr
#     ps = fs

class BlenderBoneAnim():
    """Blender Bone Animation."""
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("%s should not be instantiated" % cls)

    @staticmethod
    def parse_translation_channel(gltf, vnode, obj, bone, channel, animation):
        """Manage Location animation."""
        blender_path = "pose.bones[" + json.dumps(bone.name) + "].location"
        group_name = bone.name

        keys = BinaryData.get_data_from_accessor(gltf, animation.samplers[channel.sampler].input)
        values = BinaryData.get_data_from_accessor(gltf, animation.samplers[channel.sampler].output)

        if animation.samplers[channel.sampler].interpolation == "CUBICSPLINE":
            # TODO manage tangent?
            translation_keyframes = (
                gltf.loc_gltf_to_blender(values[idx * 3 + 1])
                for idx in range(0, len(keys))
            )
        else:
            translation_keyframes = (gltf.loc_gltf_to_blender(vals) for vals in values)

        # Calculate pose bone trans from final bone trans
        edit_trans, edit_rot = vnode.editbone_trans, vnode.editbone_rot
        edit_rot_inv = edit_rot.conjugated()
        pose_translations = [
            edit_rot_inv @ (trans - edit_trans)
            for trans in translation_keyframes
        ]

        BlenderBoneAnim.fill_fcurves(
            obj.animation_data.action,
            keys,
            pose_translations,
            group_name,
            blender_path,
            animation.samplers[channel.sampler].interpolation
        )

    @staticmethod
    def parse_rotation_channel(gltf, vnode, obj, bone, channel, animation):
        """Manage rotation animation."""
        blender_path = "pose.bones[" + json.dumps(bone.name) + "].rotation_quaternion"
        group_name = bone.name

        keys = BinaryData.get_data_from_accessor(gltf, animation.samplers[channel.sampler].input)
        values = BinaryData.get_data_from_accessor(gltf, animation.samplers[channel.sampler].output)

        if animation.samplers[channel.sampler].interpolation == "CUBICSPLINE":
            # TODO manage tangent?
            quat_keyframes = [
                gltf.quaternion_gltf_to_blender(values[idx * 3 + 1])
                for idx in range(0, len(keys))
            ]
        else:
            quat_keyframes = [gltf.quaternion_gltf_to_blender(vals) for vals in values]

        # Calculate pose bone rotation from final bone rotation
        edit_rot = vnode.editbone_rot
        edit_rot_inv = edit_rot.conjugated()
        pose_rots = [
            edit_rot_inv @ rot
            for rot in quat_keyframes
        ]

        # Manage antipodal quaternions
        for i in range(1, len(pose_rots)):
            if pose_rots[i].dot(pose_rots[i-1]) < 0:
                pose_rots[i] = -pose_rots[i]

        BlenderBoneAnim.fill_fcurves(
            obj.animation_data.action,
            keys,
            pose_rots,
            group_name,
            blender_path,
            animation.samplers[channel.sampler].interpolation
        )

    @staticmethod
    def parse_scale_channel(gltf, vnode, obj, bone, channel, animation):
        """Manage scaling animation."""
        blender_path = "pose.bones[" + json.dumps(bone.name) + "].scale"
        group_name = bone.name

        keys = BinaryData.get_data_from_accessor(gltf, animation.samplers[channel.sampler].input)
        values = BinaryData.get_data_from_accessor(gltf, animation.samplers[channel.sampler].output)

        if animation.samplers[channel.sampler].interpolation == "CUBICSPLINE":
            # TODO manage tangent?
            scale_keyframes = [
                gltf.scale_gltf_to_blender(values[idx * 3 + 1])
                for idx in range(0, len(keys))
            ]
        else:
            scale_keyframes = [gltf.scale_gltf_to_blender(vals) for vals in values]

        BlenderBoneAnim.fill_fcurves(
            obj.animation_data.action,
            keys,
            scale_keyframes,
            group_name,
            blender_path,
            animation.samplers[channel.sampler].interpolation
        )

    @staticmethod
    def fill_fcurves(action, keys, values, group_name, blender_path, interpolation):
        """Create FCurves from the keyframe-value pairs (one per component)."""
        fps = bpy.context.scene.render.fps

        coords = [0] * (2 * len(keys))
        coords[::2] = (key[0] * fps for key in keys)

        for i in range(0, len(values[0])):
            coords[1::2] = (vals[i] for vals in values)
            make_fcurve(
                action,
                coords,
                data_path=blender_path,
                index=i,
                group_name=group_name,
                interpolation=interpolation,
            )

    @staticmethod
    def anim(gltf, anim_idx, node_idx):
        """Manage animation."""
        node = gltf.data.nodes[node_idx]
        vnode = gltf.vnodes[node_idx]
        obj = gltf.vnodes[vnode.bone_arma].blender_object
        bone = obj.pose.bones[vnode.blender_bone_name]

        if anim_idx not in node.animations.keys():
            return

        animation = gltf.data.animations[anim_idx]

        action = gltf.action_cache.get(obj.name)
        if not action:
            name = animation.track_name + "_" + obj.name
            action = bpy.data.actions.new(name)
            gltf.needs_stash.append((obj, animation.track_name, action))
            gltf.action_cache[obj.name] = action

        if not obj.animation_data:
            obj.animation_data_create()
        obj.animation_data.action = action

        for channel_idx in node.animations[anim_idx]:
            channel = animation.channels[channel_idx]

            if channel.target.path == "translation":
                BlenderBoneAnim.parse_translation_channel(gltf, vnode, obj, bone, channel, animation)

            elif channel.target.path == "rotation":
                BlenderBoneAnim.parse_rotation_channel(gltf, vnode, obj, bone, channel, animation)

            elif channel.target.path == "scale":
                BlenderBoneAnim.parse_scale_channel(gltf, vnode, obj, bone, channel, animation)
