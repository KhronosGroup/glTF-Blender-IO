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
import mathutils
import typing

from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached
from io_scene_gltf2.blender.com import gltf2_blender_math
from . import gltf2_blender_export_keys
from io_scene_gltf2.io.com import gltf2_io_debug


class Keyframe:
    def __init__(self, channels: typing.Tuple[bpy.types.FCurve], time: float):
        self.seconds = time / bpy.context.scene.render.fps
        self.__target = channels[0].data_path.split('.')[-1]
        self.__indices = [c.array_index for c in channels]

        # Data holders for virtual properties
        self.__value = None
        self.__in_tangent = None
        self.__out_tangent = None

    def __get_target_len(self):
        length = {
            "delta_location": 3,
            "delta_rotation_euler": 3,
            "location": 3,
            "rotation_axis_angle": 4,
            "rotation_euler": 3,
            "rotation_quaternion": 4,
            "scale": 3,
            "value": 1
        }.get(self.__target)

        if length is None:
            raise RuntimeError("Animations with target type '{}' are not supported.".format(self.__target))

        return length

    def __set_indexed(self, value):
        # 'value' targets don't use keyframe.array_index
        if self.__target == "value":
            return value
        # Sometimes blender animations only reference a subset of components of a data target. Keyframe should always
        # contain a complete Vector/ Quaternion --> use the array_index value of the keyframe to set components in such
        # structures
        result = [0.0] * self.__get_target_len()
        for i, v in zip(self.__indices, value):
            result[i] = v
        result = gltf2_blender_math.list_to_mathutils(result, self.__target)
        return result

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
def gather_keyframes(channels: typing.Tuple[bpy.types.FCurve], export_settings) \
        -> typing.List[Keyframe]:
    """Convert the blender action groups' fcurves to keyframes for use in glTF."""
    # Find the start and end of the whole action group
    ranges = [channel.range() for channel in channels]

    start = min([channel.range()[0] for channel in channels])
    end = max([channel.range()[1] for channel in channels])

    keyframes = []
    if needs_baking(channels, export_settings):
        # Bake the animation, by evaluating it at a high frequency
        # TODO: maybe baking can also be done with FCurve.convert_to_samples
        time = start
        # TODO: make user controllable
        step = 1.0 / bpy.context.scene.render.fps
        while time <= end:
            key = Keyframe(channels, time)
            key.value = [c.evaluate(time) for c in channels]
            keyframes.append(key)
            time += step
    else:
        # Just use the keyframes as they are specified in blender
        times = [keyframe.co[0] for keyframe in channels[0].keyframe_points]
        for i, time in enumerate(times):
            key = Keyframe(channels, time)
            # key.value = [c.keyframe_points[i].co[0] for c in action_group.channels]
            key.value = [c.evaluate(time) for c in channels]

            # compute tangents for cubic spline interpolation
            if channels[0].keyframe_points[0].interpolation == "BEZIER":
                # Construct the in tangent
                if time == times[0]:
                    # start in-tangent should become all zero
                    key.in_tangent = key.value
                else:
                    # otherwise construct an in tangent coordinate from the keyframes control points. We intermediately
                    # use a point at t-1 to define the tangent. This allows the tangent control point to be transformed
                    # normally
                    key.in_tangent = [
                        c.keyframe_points[i].co[1] + ((c.keyframe_points[i].co[1] - c.keyframe_points[i].handle_left[1]
                                                       ) / (time - times[i - 1]))
                        for c in channels
                    ]
                # Construct the out tangent
                if time == times[-1]:
                    # end out-tangent should become all zero
                    key.out_tangent = key.value
                else:
                    # otherwise construct an in tangent coordinate from the keyframes control points. We intermediately
                    # use a point at t+1 to define the tangent. This allows the tangent control point to be transformed
                    # normally
                    key.out_tangent = [
                        c.keyframe_points[i].co[1] + ((c.keyframe_points[i].handle_right[1] - c.keyframe_points[i].co[1]
                                                       ) / (times[i + 1] - time))
                        for c in channels
                    ]

            keyframes.append(key)

    return keyframes


def needs_baking(channels: typing.Tuple[bpy.types.FCurve],
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

    if not all(all_equal(key_times) for key_times in zip([[k.co[0] for k in c.keyframe_points] for c in channels])):
        # The channels have differently located keyframes
        gltf2_io_debug.print_console("WARNING",
                                     "Baking animation because of differently located keyframes in one channel")
        return True

    return False
