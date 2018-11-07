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

from mathutils import Matrix, Quaternion


class Conversion():
    """Conversion class."""

    @staticmethod
    def matrix_gltf_to_blender(mat_input):
        """Matrix from glTF format to Blender format."""
        mat = Matrix([mat_input[0:4], mat_input[4:8], mat_input[8:12], mat_input[12:16]])
        mat.transpose()
        return mat

    @staticmethod
    def loc_gltf_to_blender(loc):
        """Location."""
        return loc

    @staticmethod
    def scale_gltf_to_blender(scale):
        """Scaling."""
        return scale

    @staticmethod
    def quaternion_gltf_to_blender(q):
        """Quaternion from glTF to Blender."""
        return Quaternion([q[3], q[0], q[1], q[2]])

    def scale_to_matrix(scale):
        """Scale to matrix."""
        mat = Matrix()
        for i in range(3):
            mat[i][i] = scale[i]

        return mat
