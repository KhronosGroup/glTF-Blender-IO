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

import typing
import math
from mathutils import Matrix, Vector, Quaternion, Euler

class Conversion():

    @staticmethod
    def matrix_gltf_to_blender(mat_input):
        mat =  Matrix([mat_input[0:4], mat_input[4:8], mat_input[8:12], mat_input[12:16]])
        mat.transpose()
        return mat

    @staticmethod
    def loc_gltf_to_blender(loc):
        return loc

    @staticmethod
    def scale_gltf_to_blender(scale):
        return scale

    @staticmethod
    def quaternion_gltf_to_blender(q):
        return Quaternion([q[3], q[0], q[1], q[2]])


def list_to_mathutils(values: typing.List[float], data_path: str) -> typing.Union[Vector, Quaternion, Euler]:
    target = data_path.split('.')[-1]

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
        return Vector(values)

    return Vector(values)