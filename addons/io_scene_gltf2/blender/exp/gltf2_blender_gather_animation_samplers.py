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

from . import gltf2_blender_export_keys
from mathutils import Matrix
from io_scene_gltf2.blender.com.gltf2_blender_data_path import get_target_property_name, get_target_object_path
from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached
from io_scene_gltf2.io.exp import gltf2_io_binary_data
from io_scene_gltf2.io.com import gltf2_io_constants
from io_scene_gltf2.blender.com import gltf2_blender_math


@cached
def gather_animation_sampler(channels: typing.Tuple[bpy.types.FCurve],
                             blender_object: bpy.types.Object,
                             export_settings
                             ) -> gltf2_io.AnimationSampler:
    return gltf2_io.AnimationSampler(
        extensions=__gather_extensions(channels, blender_object, export_settings),
        extras=__gather_extras(channels, blender_object, export_settings),
        input=__gather_input(channels, blender_object, export_settings),
        interpolation=__gather_interpolation(channels, blender_object, export_settings),
        output=__gather_output(channels, blender_object, export_settings)
    )


def __gather_extensions(channels: typing.Tuple[bpy.types.FCurve],
                        blender_object: bpy.types.Object,
                        export_settings
                        ) -> typing.Any:
    return None


def __gather_extras(channels: typing.Tuple[bpy.types.FCurve],
                    blender_object: bpy.types.Object,
                    export_settings
                    ) -> typing.Any:
    return None


def __gather_input(channels: typing.Tuple[bpy.types.FCurve],
                   blender_object: bpy.types.Object,
                   export_settings
                   ) -> gltf2_io.Accessor:
    """Gather the key time codes."""
    keyframes = __gather_keyframes(channels, export_settings)
    times = [k.seconds for k in keyframes]

    return gltf2_io.Accessor(
        buffer_view=gltf2_io_binary_data.BinaryData.from_list(times, gltf2_io_constants.ComponentType.Float),
        byte_offset=None,
        component_type=gltf2_io_constants.ComponentType.Float,
        count=len(times),
        extensions=None,
        extras=None,
        max=[max(times)],
        min=[min(times)],
        name=None,
        normalized=None,
        sparse=None,
        type=gltf2_io_constants.DataType.Scalar
    )


def __gather_interpolation(channels: typing.Tuple[bpy.types.FCurve],
                           blender_object: bpy.types.Object,
                           export_settings
                           ) -> str:
    if __needs_baking(channels, export_settings):
        return 'STEP'

    blender_keyframe = channels[0].keyframe_points[0]

    # Select the interpolation method. Any unsupported method will fallback to STEP
    return {
        "BEZIER": "CUBICSPLINE",
        "LINEAR": "LINEAR",
        "CONSTANT": "STEP"
    }[blender_keyframe.interpolation]


def __gather_output(channels: typing.Tuple[bpy.types.FCurve],
                    blender_object: bpy.types.Object,
                    export_settings
                    ) -> gltf2_io.Accessor:
    """Gather the data of the keyframes."""
    keyframes = __gather_keyframes(channels, export_settings)

    target_datapath = channels[0].data_path

    transform = Matrix.Identity(4)

    if blender_object.type == "ARMATURE":
        bone = blender_object.path_resolve(get_target_object_path(target_datapath))
        if isinstance(bone, bpy.types.PoseBone):
            axis_basis_change = mathutils.Matrix.Identity(4)
            # if export_settings[gltf2_blender_export_keys.YUP]:
            #     axis_basis_change = mathutils.Matrix(
            #         ((1.0, 0.0, 0.0, 0.0), (0.0, 0.0, 1.0, 0.0), (0.0, -1.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0)))

            transform = bone.bone.matrix_local
            #transform = gltf2_blender_math.multiply(transform, axis_basis_change)
            if bone.parent is not None:
                parent_transform = gltf2_blender_math.multiply(axis_basis_change, bone.parent.bone.matrix_local)
                transform = gltf2_blender_math.multiply(parent_transform.inverted(), transform)

    values = []
    for keyframe in keyframes:
        # Transform the data and extract
        value = gltf2_blender_math.transform(keyframe.value, target_datapath, transform)
        if export_settings[gltf2_blender_export_keys.YUP] and not blender_object.type == "ARMATURE":
            value = gltf2_blender_math.swizzle_yup(value, target_datapath)
        keyframe_value = gltf2_blender_math.mathutils_to_gltf(value)
        if keyframe.in_tangent is not None:
            in_tangent = gltf2_blender_math.transform(keyframe.in_tangent, target_datapath, transform)
            if export_settings[gltf2_blender_export_keys.YUP] and not blender_object.type == "ARMATURE":
                in_tangent = gltf2_blender_math.swizzle_yup(in_tangent, target_datapath)
            keyframe_value = gltf2_blender_math.mathutils_to_gltf(in_tangent) + keyframe_value
        if keyframe.out_tangent is not None:
            out_tangent = gltf2_blender_math.transform(keyframe.out_tangent, target_datapath, transform)
            if export_settings[gltf2_blender_export_keys.YUP] and not blender_object.type == "ARMATURE":
                out_tangent = gltf2_blender_math.swizzle_yup(out_tangent, target_datapath)
            keyframe_value = keyframe_value + gltf2_blender_math.mathutils_to_gltf(out_tangent)
        values += keyframe_value

    component_type = gltf2_io_constants.ComponentType.Float
    if get_target_property_name(target_datapath) == "value":
        # channels with 'weight' targets must have scalar accessors
        data_type = gltf2_io_constants.DataType.Scalar
    else:
        data_type = gltf2_io_constants.DataType.vec_type_from_num(len(keyframes[0].value))

    return gltf2_io.Accessor(
        buffer_view=gltf2_io_binary_data.BinaryData.from_list(values, component_type),
        byte_offset=None,
        component_type=component_type,
        count=len(values) // gltf2_io_constants.DataType.num_elements(data_type),
        extensions=None,
        extras=None,
        max=None,
        min=None,
        name=None,
        normalized=None,
        sparse=None,
        type=data_type
    )


def __needs_baking(channels: typing.Tuple[bpy.types.FCurve],
                   export_settings
                   ) -> bool:
    """
    Check if baking is needed.

    Some blender animations need to be baked as they can not directly be expressed in glTF.
    """
    # if blender_object.type == "ARMATURE":
    #     return True

    if export_settings[gltf2_blender_export_keys.FORCE_SAMPLING]:
        return True

    interpolation = channels[0].keyframe_points[0].interpolation
    if interpolation not in ["BEZIER", "LINEAR", "CONSTANT"]:
        return True

    if any(any(k.interpolation != interpolation for k in c.keyframe_points) for c in channels):
        # There are different interpolation methods in one action group
        return True

    def all_equal(lst):
        return lst[1:] == lst[:-1]

    if not all(all_equal(key_times) for key_times in zip([[k.co[0] for k in c.keyframe_points] for c in channels])):
        # The channels have differently located keyframes
        return True

    return False


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
            "location": 3,
            "rotation_axis_angle": 4,
            "rotation_euler": 3,
            "rotation_quaternion": 4,
            "scale": 3,
            "value": 1
        }.get(self.__target)

        if length is None:
            raise RuntimeError("Unknown target type {}".format(self.__target))

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
def __gather_keyframes(channels: typing.Tuple[bpy.types.FCurve], export_settings) \
        -> typing.List[Keyframe]:
    """Convert the blender action groups' fcurves to keyframes for use in glTF."""
    # Find the start and end of the whole action group
    start = min([channel.range()[0] for channel in channels])
    end = max([channel.range()[1] for channel in channels])

    keyframes = []
    if __needs_baking(channels, export_settings):
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
                if time == start:
                    # start in-tangent has zero length
                    key.in_tangent = [0.0 for _ in channels]
                else:
                    # otherwise construct a in tangent from the keyframes control points
                    key.in_tangent = [
                        3.0 * (c.keyframe_points[i].co[1] - c.keyframe_points[i].handle_left[1]
                               ) / (time - times[i - 1])
                        for c in channels
                    ]
                # Construct the out tangent
                if time == end:
                    # end out-tangent has zero length
                    key.out_tangent = [0.0 for _ in channels]
                else:
                    # otherwise construct a in tangent from the keyframes control points
                    key.out_tangent = [
                        3.0 * (c.keyframe_points[i].handle_right[1] - c.keyframe_points[i].co[1]
                               ) / (times[i + 1] - time)
                        for c in channels
                    ]
            keyframes.append(key)

    return keyframes
