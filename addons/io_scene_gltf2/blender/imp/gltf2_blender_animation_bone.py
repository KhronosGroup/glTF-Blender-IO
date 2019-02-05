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

import json
import bpy
from mathutils import Matrix

from ..com.gltf2_blender_conversion import loc_gltf_to_blender, quaternion_gltf_to_blender, scale_to_matrix
from ...io.imp.gltf2_io_binary import BinaryData


class BlenderBoneAnim():
    """Blender Bone Animation."""
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("%s should not be instantiated" % cls)

    @staticmethod
    def set_interpolation(interpolation, kf):
        """Set interpolation."""
        if interpolation == "LINEAR":
            kf.interpolation = 'LINEAR'
        elif interpolation == "STEP":
            kf.interpolation = 'CONSTANT'
        elif interpolation == "CUBICSPLINE":
            kf.interpolation = 'BEZIER'
        else:
            kf.interpolation = 'LINEAR'

    @staticmethod
    def parse_translation_channel(gltf, node, obj, bone, channel, animation):
        """Manage Location animation."""
        blender_path = "pose.bones[" + json.dumps(bone.name) + "].location"
        group_name = bone.name

        keys = BinaryData.get_data_from_accessor(gltf, animation.samplers[channel.sampler].input)
        values = BinaryData.get_data_from_accessor(gltf, animation.samplers[channel.sampler].output)
        if bpy.app.version < (2, 80, 0):
            inv_bind_matrix = node.blender_bone_matrix.to_quaternion().to_matrix().to_4x4().inverted() \
                * Matrix.Translation(node.blender_bone_matrix.to_translation()).inverted()
        else:
            inv_bind_matrix = node.blender_bone_matrix.to_quaternion().to_matrix().to_4x4().inverted() \
                @ Matrix.Translation(node.blender_bone_matrix.to_translation()).inverted()

        if animation.samplers[channel.sampler].interpolation == "CUBICSPLINE":
            # TODO manage tangent?
            translation_keyframes = (
                loc_gltf_to_blender(values[idx * 3 + 1])
                for idx in range(0, len(keys))
            )
        else:
            translation_keyframes = (loc_gltf_to_blender(vals) for vals in values)
        if node.parent is None:
            parent_mat = Matrix()
        else:
            if not gltf.data.nodes[node.parent].is_joint:
                parent_mat = Matrix()
            else:
                parent_mat = gltf.data.nodes[node.parent].blender_bone_matrix

        # Pose is in object (armature) space and it's value if the offset from the bind pose
        # (which is also in object space)
        # Scale is not taken into account
        if bpy.app.version < (2, 80, 0):
            final_translations = [
                inv_bind_matrix * (parent_mat * Matrix.Translation(translation_keyframe)).to_translation()
                for translation_keyframe in translation_keyframes
            ]
        else:
            final_translations = [
                inv_bind_matrix @ (parent_mat @ Matrix.Translation(translation_keyframe)).to_translation()
                for translation_keyframe in translation_keyframes
            ]

        BlenderBoneAnim.fill_fcurves(
            obj.animation_data.action,
            keys,
            final_translations,
            group_name,
            blender_path,
            animation.samplers[channel.sampler].interpolation
        )

    @staticmethod
    def parse_rotation_channel(gltf, node, obj, bone, channel, animation):
        """Manage rotation animation."""
        # Note: some operations lead to issue with quaternions. Converting to matrix and then back to quaternions breaks
        # quaternion continuity
        # (see antipodal quaternions). Blender interpolates between two antipodal quaternions, which causes glitches in
        # animation.
        # Converting to euler and then back to quaternion is a dirty fix preventing this issue in animation, until a
        # better solution is found
        # This fix is skipped when parent matrix is identity
        blender_path = "pose.bones[" + json.dumps(bone.name) + "].rotation_quaternion"
        group_name = bone.name

        keys = BinaryData.get_data_from_accessor(gltf, animation.samplers[channel.sampler].input)
        values = BinaryData.get_data_from_accessor(gltf, animation.samplers[channel.sampler].output)
        bind_rotation = node.blender_bone_matrix.to_quaternion()

        if animation.samplers[channel.sampler].interpolation == "CUBICSPLINE":
            # TODO manage tangent?
            quat_keyframes = [
                quaternion_gltf_to_blender(values[idx * 3 + 1])
                for idx in range(0, len(keys))
            ]
        else:
            quat_keyframes = [quaternion_gltf_to_blender(vals) for vals in values]

        # Manage antipodal quaternions
        # (but is not suffisant, we also convert quaternion --> euler --> quaternion)
        for i in range(1, len(quat_keyframes)):
            if quat_keyframes[i].dot(quat_keyframes[i-1]) < 0:
                quat_keyframes[i] = -quat_keyframes[i]


        if not node.parent:
            if bpy.app.version < (2, 80, 0):
                final_rots = [
                    bind_rotation.inverted() * quat_keyframe
                    for quat_keyframe in quat_keyframes
                ]
            else:
                final_rots = [
                    bind_rotation.inverted() @ quat_keyframe
                    for quat_keyframe in quat_keyframes
                ]
        else:
            if not gltf.data.nodes[node.parent].is_joint:
                parent_mat = Matrix()
            else:
                parent_mat = gltf.data.nodes[node.parent].blender_bone_matrix

            if parent_mat != parent_mat.inverted():
                if bpy.app.version < (2, 80, 0):
                    final_rots = [
                        bind_rotation.rotation_difference(
                            (parent_mat * quat_keyframe.to_matrix().to_4x4()).to_quaternion()
                        ).to_euler().to_quaternion()
                        for quat_keyframe in quat_keyframes
                    ]
                else:
                    final_rots = [
                        bind_rotation.rotation_difference(
                            (parent_mat @ quat_keyframe.to_matrix().to_4x4()).to_quaternion()
                        ).to_euler().to_quaternion()
                        for quat_keyframe in quat_keyframes
                    ]
            else:
                final_rots = [
                    bind_rotation.rotation_difference(quat_keyframe).to_euler().to_quaternion()
                    for quat_keyframe in quat_keyframes
                ]

        BlenderBoneAnim.fill_fcurves(
            obj.animation_data.action,
            keys,
            final_rots,
            group_name,
            blender_path,
            animation.samplers[channel.sampler].interpolation
        )

    @staticmethod
    def parse_scale_channel(gltf, node, obj, bone, channel, animation):
        """Manage scaling animation."""
        blender_path = "pose.bones[" + json.dumps(bone.name) + "].scale"
        group_name = bone.name

        keys = BinaryData.get_data_from_accessor(gltf, animation.samplers[channel.sampler].input)
        values = BinaryData.get_data_from_accessor(gltf, animation.samplers[channel.sampler].output)
        bind_scale = scale_to_matrix(node.blender_bone_matrix.to_scale())

        if animation.samplers[channel.sampler].interpolation == "CUBICSPLINE":
            # TODO manage tangent?
            scale_mats = (
                scale_to_matrix(loc_gltf_to_blender(values[idx * 3 + 1]))
                for idx in range(0, len(keys))
            )
        else:
            scale_mats = (scale_to_matrix(loc_gltf_to_blender(vals)) for vals in values)
        if not node.parent:
            if bpy.app.version < (2, 80, 0):
                final_scales = [
                    (bind_scale.inverted() * scale_mat).to_scale()
                    for scale_mat in scale_mats
                ]
            else:
                final_scales = [
                    (bind_scale.inverted() @ scale_mat).to_scale()
                    for scale_mat in scale_mats
                ]
        else:
            if not gltf.data.nodes[node.parent].is_joint:
                parent_mat = Matrix()
            else:
                parent_mat = gltf.data.nodes[node.parent].blender_bone_matrix

            if bpy.app.version < (2, 80, 0):
                final_scales = [
                    (bind_scale.inverted() * scale_to_matrix(parent_mat.to_scale()) * scale_mat).to_scale()
                    for scale_mat in scale_mats
                ]
            else:
                final_scales = [
                    (bind_scale.inverted() @ scale_to_matrix(parent_mat.to_scale()) @ scale_mat).to_scale()
                    for scale_mat in scale_mats
                ]

        BlenderBoneAnim.fill_fcurves(
            obj.animation_data.action,
            keys,
            final_scales,
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

        if group_name not in action.groups:
            action.groups.new(group_name)
        group = action.groups[group_name]

        for i in range(0, len(values[0])):
            fcurve = action.fcurves.new(data_path=blender_path, index=i)
            fcurve.group = group

            fcurve.keyframe_points.add(len(keys))
            coords[1::2] = (vals[i] for vals in values)
            fcurve.keyframe_points.foreach_set('co', coords)

            # Setting interpolation
            for kf in fcurve.keyframe_points:
                BlenderBoneAnim.set_interpolation(interpolation, kf)

    @staticmethod
    def anim(gltf, anim_idx, node_idx):
        """Manage animation."""
        node = gltf.data.nodes[node_idx]
        obj = bpy.data.objects[gltf.data.skins[node.skin_id].blender_armature_name]
        bone = obj.pose.bones[node.blender_bone_name]

        if anim_idx not in node.animations.keys():
            return

        animation = gltf.data.animations[anim_idx]

        if animation.name:
            name = animation.name + "_" + obj.name
        else:
            name = "Animation_" + str(anim_idx) + "_" + obj.name
        if name not in bpy.data.actions:
            action = bpy.data.actions.new(name)
        else:
            if name in gltf.animation_managed:
                # multiple animation with same name in glTF file
                # Create a new action with new name if needed
                if name in gltf.current_animation_names.keys():
                    action = bpy.data.actions[gltf.current_animation_names[name]]
                    name = gltf.current_animation_names[name]
                else:
                    action = bpy.data.actions.new(name)
            else:
                action = bpy.data.actions[name]
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

            if channel.target.path == "translation":
                BlenderBoneAnim.parse_translation_channel(gltf, node, obj, bone, channel, animation)

            elif channel.target.path == "rotation":
                BlenderBoneAnim.parse_rotation_channel(gltf, node, obj, bone, channel, animation)

            elif channel.target.path == "scale":
                BlenderBoneAnim.parse_scale_channel(gltf, node, obj, bone, channel, animation)

        if action.name not in gltf.current_animation_names.keys():
            gltf.current_animation_names[name] = action.name
