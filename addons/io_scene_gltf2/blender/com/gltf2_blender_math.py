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

from io_scene_gltf2.blender.com.gltf2_blender_data_path import get_target_property_name


def multiply(a, b):
    """Multiplication."""
    if bpy.app.version < (2, 80, 0):
        return a * b
    else:
        return a @ b


def list_to_mathutils(values: typing.List[float], data_path: str) -> typing.Union[Vector, Quaternion, Euler]:
    """Transform a list to blender py object."""
    target = get_target_property_name(data_path)

    if target == 'delta_location':
        return Vector(values)  # TODO Should be Vector(values) - Vector(something)?
    elif target == 'delta_rotation_euler':
        return Euler(values).to_quaternion()  # TODO Should be multiply(Euler(values).to_quaternion(), something)?
    elif target == 'location':
        return Vector(values)
    elif target == 'rotation_axis_angle':
        angle = values[0]
        axis = values[1:]
        return Quaternion(axis, math.radians(angle))
    elif target == 'rotation_euler':
        return Euler(values).to_quaternion()
    elif target == 'rotation_quaternion':
        return Quaternion(values)
    elif target == 'scale':
        return Vector(values)
    elif target == 'value':
        return values

    return values


def mathutils_to_gltf(x: typing.Union[Vector, Quaternion]) -> typing.List[float]:
    """Transform a py object to glTF list."""
    if isinstance(x, Vector):
        return list(x)
    if isinstance(x, Quaternion):
        # Blender has w-first quaternion notation
        return [x[1], x[2], x[3], x[0]]
    else:
        return list(x)


def to_yup() -> Matrix:
    """Transform to Yup."""
    return Matrix(
        ((1.0, 0.0, 0.0, 0.0),
         (0.0, 0.0, 1.0, 0.0),
         (0.0, -1.0, 0.0, 0.0),
         (0.0, 0.0, 0.0, 1.0))
    )


to_zup = to_yup


def swizzle_yup(v: typing.Union[Vector, Quaternion], data_path: str) -> typing.Union[Vector, Quaternion]:
    """Manage Yup."""
    target = get_target_property_name(data_path)
    swizzle_func = {
        "delta_location": swizzle_yup_location,
        "delta_rotation_euler": swizzle_yup_rotation,
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
    """Manage Yup location."""
    return Vector((loc[0], loc[2], -loc[1]))


def swizzle_yup_rotation(rot: Quaternion) -> Quaternion:
    """Manage Yup rotation."""
    return Quaternion((rot[0], rot[1], rot[3], -rot[2]))


def swizzle_yup_scale(scale: Vector) -> Vector:
    """Manage Yup scale."""
    return Vector((scale[0], scale[2], scale[1]))


def swizzle_yup_value(value: typing.Any) -> typing.Any:
    """Manage Yup value."""
    return value


def transform(v: typing.Union[Vector, Quaternion], data_path: str, transform: Matrix = Matrix.Identity(4)) -> typing \
        .Union[Vector, Quaternion]:
    """Manage transformations."""
    target = get_target_property_name(data_path)
    transform_func = {
        "delta_location": transform_location,
        "delta_rotation_euler": transform_rotation,
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
    """Transform location."""
    m = Matrix.Translation(location)
    m = multiply(transform, m)
    return m.to_translation()


def transform_rotation(rotation: Quaternion, transform: Matrix = Matrix.Identity(4)) -> Quaternion:
    """Transform rotation."""
    m = rotation.to_matrix().to_4x4()
    m = multiply(transform, m)
    return m.to_quaternion()


def transform_scale(scale: Vector, transform: Matrix = Matrix.Identity(4)) -> Vector:
    """Transform scale."""
    m = Matrix.Identity(4)
    m[0][0] = scale.x
    m[1][1] = scale.y
    m[2][2] = scale.z
    m = multiply(transform, m)

    return m.to_scale()


def transform_value(value: Vector, _: Matrix = Matrix.Identity(4)) -> Vector:
    """Transform value."""
    return value


def round_if_near(value: float, target: float) -> float:
    """If value is very close to target, round to target."""
    return value if abs(value - target) > 2.0e-6 else target
