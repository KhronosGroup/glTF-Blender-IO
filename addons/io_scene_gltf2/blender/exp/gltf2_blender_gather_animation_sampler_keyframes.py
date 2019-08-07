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
import mathutils
import typing

from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached
from io_scene_gltf2.blender.com import gltf2_blender_math
from io_scene_gltf2.blender.exp import gltf2_blender_get
from io_scene_gltf2.blender.exp import gltf2_blender_extract
from . import gltf2_blender_export_keys
from io_scene_gltf2.io.com import gltf2_io_debug


class Keyframe:
    def __init__(self, channels: typing.Tuple[bpy.types.FCurve], frame: float, bake_channel: typing.Union[str, None]):
        self.seconds = frame / bpy.context.scene.render.fps
        self.frame = frame
        self.fps = bpy.context.scene.render.fps
        if bake_channel is None:
            self.target = channels[0].data_path.split('.')[-1]
            self.__indices = [c.array_index for c in channels]
        else:
            self.target = bake_channel
            self.__indices = []
            for i in range(self.get_target_len()):
                self.__indices.append(i)


        # Data holders for virtual properties
        self.__value = None
        self.__in_tangent = None
        self.__out_tangent = None

    def get_target_len(self):
        length = {
            "delta_location": 3,
            "delta_rotation_euler": 3,
            "location": 3,
            "rotation_axis_angle": 4,
            "rotation_euler": 3,
            "rotation_quaternion": 4,
            "scale": 3,
            "value": 1
        }.get(self.target)

        if length is None:
            raise RuntimeError("Animations with target type '{}' are not supported.".format(self.target))

        return length

    def __set_indexed(self, value):
        # 'value' targets don't use keyframe.array_index
        if self.target == "value":
            return value
        # Sometimes blender animations only reference a subset of components of a data target. Keyframe should always
        # contain a complete Vector/ Quaternion --> use the array_index value of the keyframe to set components in such
        # structures
        result = [0.0] * self.get_target_len()
        for i, v in zip(self.__indices, value):
            result[i] = v
        result = gltf2_blender_math.list_to_mathutils(result, self.target)
        return result

    def get_indices(self):
        return self.__indices

    def set_value_index(self, idx, val):
        self.__value[idx] = val

    def set_first_tangent(self):
        self.__in_tangent = self.__value

    def set_last_tangent(self):
        self.__out_tangent = self.__value

    @property
    def value(self) -> typing.Union[mathutils.Vector, mathutils.Euler, mathutils.Quaternion, typing.List[float]]:
        return self.__value

    @value.setter
    def value(self, value: typing.List[float]):
        self.__value = self.__set_indexed(value)

    @property
    def in_tangent(self) -> typing.Union[mathutils.Vector, mathutils.Euler, mathutils.Quaternion, typing.List[float]]:
        return self.__in_tangent

    @in_tangent.setter
    def in_tangent(self, value: typing.List[float]):
        self.__in_tangent = self.__set_indexed(value)

    @property
    def out_tangent(self) -> typing.Union[mathutils.Vector, mathutils.Euler, mathutils.Quaternion, typing.List[float]]:
        return self.__in_tangent

    @out_tangent.setter
    def out_tangent(self, value: typing.List[float]):
        self.__out_tangent = self.__set_indexed(value)


# cache for performance reasons
@cached
def gather_keyframes(blender_object_if_armature: typing.Optional[bpy.types.Object],
                     channels: typing.Tuple[bpy.types.FCurve],
                     non_keyed_values: typing.Tuple[typing.Optional[float]],
                     bake_bone: typing.Union[str, None],
                     bake_channel: typing.Union[str, None],
                     bake_range_start,
                     bake_range_end,
                     action_name: str,
                     export_settings
                     ) -> typing.List[Keyframe]:
    """Convert the blender action groups' fcurves to keyframes for use in glTF."""
    if bake_bone is None:
        # Find the start and end of the whole action group
        ranges = [channel.range() for channel in channels]

        start_frame = min([channel.range()[0] for channel in channels])
        end_frame = max([channel.range()[1] for channel in channels])
    else:
        start_frame = bake_range_start
        end_frame = bake_range_end

    keyframes = []
    if needs_baking(blender_object_if_armature, channels, export_settings):
        # Bake the animation, by evaluating the animation for all frames
        # TODO: maybe baking can also be done with FCurve.convert_to_samples

        if blender_object_if_armature is not None:
            if bake_bone is None:
                pose_bone_if_armature = gltf2_blender_get.get_object_from_datapath(blender_object_if_armature,
                                                                               channels[0].data_path)
            else:
                pose_bone_if_armature = blender_object_if_armature.pose.bones[bake_bone]
        else:
            pose_bone_if_armature = None

        # sample all frames
        frame = start_frame
        step = export_settings['gltf_frame_step']
        while frame <= end_frame:
            key = Keyframe(channels, frame, bake_channel)
            if isinstance(pose_bone_if_armature, bpy.types.PoseBone):
                # we need to bake in the constraints
                bpy.context.scene.frame_set(frame)
                if bake_bone is None:
                    trans, rot, scale = pose_bone_if_armature.matrix_basis.decompose()
                else:
                    matrix = pose_bone_if_armature.matrix
                    if bpy.app.version < (2, 80, 0):
                        new_matrix = blender_object_if_armature.convert_space(pose_bone_if_armature, matrix, 'POSE', 'LOCAL')
                    else:
                        new_matrix = blender_object_if_armature.convert_space(pose_bone=pose_bone_if_armature, matrix=matrix, from_space='POSE', to_space='LOCAL')
                    trans, rot, scale = new_matrix.decompose()
                if bake_channel is None:
                    target_property = channels[0].data_path.split('.')[-1]
                else:
                    target_property = bake_channel
                key.value = {
                    "location": trans,
                    "rotation_axis_angle": rot,
                    "rotation_euler": rot,
                    "rotation_quaternion": rot,
                    "scale": scale
                }[target_property]
            else:
                key.value = [c.evaluate(frame) for c in channels]
                complete_key(key, non_keyed_values)
            keyframes.append(key)
            frame += step
    else:
        # Just use the keyframes as they are specified in blender
        frames = [keyframe.co[0] for keyframe in channels[0].keyframe_points]
        # some weird files have duplicate frame at same time, removed them
        frames = sorted(set(frames))
        for i, frame in enumerate(frames):
            key = Keyframe(channels, frame, bake_channel)
            # key.value = [c.keyframe_points[i].co[0] for c in action_group.channels]
            key.value = [c.evaluate(frame) for c in channels]
            # Complete key with non keyed values, if needed
            if len(channels) != key.get_target_len():
                complete_key(key, non_keyed_values)

            # compute tangents for cubic spline interpolation
            if channels[0].keyframe_points[0].interpolation == "BEZIER":
                # Construct the in tangent
                if frame == frames[0]:
                    # start in-tangent should become all zero
                    key.set_first_tangent()
                else:
                    # otherwise construct an in tangent coordinate from the keyframes control points. We intermediately
                    # use a point at t-1 to define the tangent. This allows the tangent control point to be transformed
                    # normally
                    key.in_tangent = [
                        c.keyframe_points[i].co[1] + ((c.keyframe_points[i].co[1] - c.keyframe_points[i].handle_left[1]
                                                       ) / (frame - frames[i - 1]))
                        for c in channels
                    ]
                # Construct the out tangent
                if frame == frames[-1]:
                    # end out-tangent should become all zero
                    key.set_last_tangent()
                else:
                    # otherwise construct an in tangent coordinate from the keyframes control points. We intermediately
                    # use a point at t+1 to define the tangent. This allows the tangent control point to be transformed
                    # normally
                    key.out_tangent = [
                        c.keyframe_points[i].co[1] + ((c.keyframe_points[i].handle_right[1] - c.keyframe_points[i].co[1]
                                                       ) / (frames[i + 1] - frame))
                        for c in channels
                    ]

            keyframes.append(key)

    return keyframes


def complete_key(key: Keyframe, non_keyed_values: typing.Tuple[typing.Optional[float]]):
    """
    Complete keyframe with non keyed values
    """

    if key.target == "value":
        return # No array_index
    for i in range(0, key.get_target_len()):
        if i in key.get_indices():
            continue # this is a keyed array_index
        key.set_value_index(i, non_keyed_values[i])

def needs_baking(blender_object_if_armature: typing.Optional[bpy.types.Object],
                 channels: typing.Tuple[bpy.types.FCurve],
                 export_settings
                 ) -> bool:
    """
    Check if baking is needed.

    Some blender animations need to be baked as they can not directly be expressed in glTF.
    """
    def all_equal(lst):
        return lst[1:] == lst[:-1]

    # Sampling is forced
    if export_settings[gltf2_blender_export_keys.FORCE_SAMPLING]:
        return True

    # Sampling due to unsupported interpolation
    interpolation = channels[0].keyframe_points[0].interpolation
    if interpolation not in ["BEZIER", "LINEAR", "CONSTANT"]:
        gltf2_io_debug.print_console("WARNING",
                                     "Baking animation because of an unsupported interpolation method: {}".format(
                                         interpolation)
                                     )
        return True

    if any(any(k.interpolation != interpolation for k in c.keyframe_points) for c in channels):
        # There are different interpolation methods in one action group
        gltf2_io_debug.print_console("WARNING",
                                     "Baking animation because there are keyframes with different "
                                     "interpolation methods in one channel"
                                     )
        return True

    if not all_equal([len(c.keyframe_points) for c in channels]):
        gltf2_io_debug.print_console("WARNING",
                                     "Baking animation because the number of keyframes is not "
                                     "equal for all channel tracks")
        return True

    if len(channels[0].keyframe_points) <= 1:
        # we need to bake to 'STEP', as at least two keyframes are required to interpolate
        return True

    if not all_equal(list(zip([[k.co[0] for k in c.keyframe_points] for c in channels]))):
        # The channels have differently located keyframes
        gltf2_io_debug.print_console("WARNING",
                                     "Baking animation because of differently located keyframes in one channel")
        return True

    if blender_object_if_armature is not None:
        animation_target = gltf2_blender_get.get_object_from_datapath(blender_object_if_armature, channels[0].data_path)
        if isinstance(animation_target, bpy.types.PoseBone):
            if len(animation_target.constraints) != 0:
                # Constraints such as IK act on the bone -> can not be represented in glTF atm
                gltf2_io_debug.print_console("WARNING",
                                             "Baking animation because of unsupported constraints acting on the bone")
                return True

    return False
