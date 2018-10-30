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
import typing
import math
from mathutils import Matrix, Vector, Quaternion, Euler

def multiply(a, b):
    if bpy.app.version < (2, 80, 0):
        return a * b
    else:
        return a @ b

def list_to_mathutils(values: typing.List[float], data_path: str) -> typing.Union[Vector, Quaternion, Euler]:
    target = datapath_to_target(data_path)

    if target == 'location':
        return Vector(values)
    if target == 'rotation_axis_angle':
        angle = values[0]
        axis = values[1:]
        return Quaternion(axis, math.radians(angle))
    if target == 'rotation_euler':
        return Euler(values).to_quaternion()
    if target == 'rotation_quaternion':
        return Quaternion(values)
    if target == 'scale':
        return Vector(values)
    if target == 'value':
        return values

    return values


def datapath_to_target(data_path: str) -> str:
    return data_path.split('.')[-1]


def mathutils_to_gltf(x: typing.Union[Vector, Quaternion]) -> typing.List[float]:
    if isinstance(x, Vector):
        return list(x)
    if isinstance(x, Quaternion):
        # Blender has w-first quaternion notation
        return [x[1], x[2], x[3], x[0]]
    else:
        return list(x)


def to_yup() -> Matrix:
    yup = Matrix.Identity(4)
    # Flip y axis and move to z
    yup[1][1] = 0
    yup[1][2] = -1
    # Move z axis to y
    yup[2][2] = 0
    yup[2][1] = 1
    return yup


def swizzle_yup(v: typing.Union[Vector, Quaternion], data_path: str) -> typing.Union[Vector, Quaternion]:
    target = datapath_to_target(data_path)
    swizzle_func = {
        "location": swizzle_yup_location,
        "rotation_axis_angle": swizzle_yup_rotation,
        "rotation_euler": swizzle_yup_rotation,
        "rotation_quaternion": swizzle_yup_rotation,
        "scale": swizzle_yup_scale,
        "value": swizzle_yup_value
    }.get(target)

    if swizzle_func is None:
        raise RuntimeError("Cannot transform values at {}".format(data_path))

    return swizzle_func(v)


def swizzle_yup_location(loc: Vector) -> Vector:
    return Vector((loc[0], loc[2], -loc[1]))


def swizzle_yup_rotation(rot: Quaternion) -> Quaternion:
    return Quaternion((rot[0], rot[1], rot[3], -rot[2]))


def swizzle_yup_scale(scale: Vector) -> Vector:
    return Vector((scale[0], scale[2], scale[1]))


def swizzle_yup_value(value: typing.Any) -> typing.Any:
    return value


def transform(v: typing.Union[Vector, Quaternion], data_path: str, transform: Matrix = Matrix.Identity(4)) -> typing.Union[Vector, Quaternion]:
    target = datapath_to_target(data_path)
    transform_func = {
        "location": transform_location,
        "rotation_axis_angle": transform_rotation,
        "rotation_euler": transform_rotation,
        "rotation_quaternion": transform_rotation,
        "scale": transform_scale,
        "value": transform_value
    }.get(target)

    if transform_func is None:
        raise RuntimeError("Cannot transform values at {}".format(data_path))

    return transform_func(v, transform)


def transform_location(location: Vector, transform: Matrix = Matrix.Identity(4)) -> Vector:
    m = Matrix.Translation(location)
    m = multiply(transform, m)
    return m.to_translation()


def transform_rotation(rotation: Quaternion, transform: Matrix = Matrix.Identity(4)) -> Quaternion:
    m = rotation.to_matrix().to_4x4()
    m = multiply(transform, m)
    return m.to_quaternion()


def transform_scale(scale: Vector, transform: Matrix = Matrix.Identity(4)) -> Vector:
    m = Matrix.Identity(4)
    m[0][0] = scale.x
    m[1][1] = scale.y
    m[2][2] = scale.z
    m = multiply(transform, m)

    return m.to_scale()


def transform_value(value: Vector, transform: Matrix = Matrix.Identity(4)) -> Vector:
    return value