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


class TRS:

    def __new__(cls, *args, **kwargs):
        raise RuntimeError("{} should not be instantiated".format(cls.__name__))

    @staticmethod
    def scale_to_matrix(scale):
        # column major !
        return [scale[0], 0, 0, 0,
                0, scale[1], 0, 0,
                0, 0, scale[2], 0,
                0, 0, 0, 1]

    @staticmethod
    def quaternion_to_matrix(q):
        x, y, z, w = q
        # TODO : is q normalized ? --> if not, multiply by 1/(w*w + x*x + y*y + z*z)
        # column major !
        return [
            1 - 2 * y * y - 2 * z * z, 2 * x * y + 2 * w * z, 2 * x * z - 2 * w * y, 0,
            2 * x * y - 2 * w * z, 1 - 2 * x * x - 2 * z * z, 2 * y * z + 2 * w * x, 0,
            2 * x * z + 2 * y * w, 2 * y * z - 2 * w * x, 1 - 2 * x * x - 2 * y * y, 0,
            0, 0, 0, 1]

    @staticmethod
    def matrix_multiply(m, n):
        # column major !

        return [
            m[0] * n[0] + m[4] * n[1] + m[8] * n[2] + m[12] * n[3],
            m[1] * n[0] + m[5] * n[1] + m[9] * n[2] + m[13] * n[3],
            m[2] * n[0] + m[6] * n[1] + m[10] * n[2] + m[14] * n[3],
            m[3] * n[0] + m[7] * n[1] + m[11] * n[2] + m[15] * n[3],
            m[0] * n[4] + m[4] * n[5] + m[8] * n[6] + m[12] * n[7],
            m[1] * n[4] + m[5] * n[5] + m[9] * n[6] + m[13] * n[7],
            m[2] * n[4] + m[6] * n[5] + m[10] * n[6] + m[14] * n[7],
            m[3] * n[4] + m[7] * n[5] + m[11] * n[6] + m[15] * n[7],
            m[0] * n[8] + m[4] * n[9] + m[8] * n[10] + m[12] * n[11],
            m[1] * n[8] + m[5] * n[9] + m[9] * n[10] + m[13] * n[11],
            m[2] * n[8] + m[6] * n[9] + m[10] * n[10] + m[14] * n[11],
            m[3] * n[8] + m[7] * n[9] + m[11] * n[10] + m[15] * n[11],
            m[0] * n[12] + m[4] * n[13] + m[8] * n[14] + m[12] * n[15],
            m[1] * n[12] + m[5] * n[13] + m[9] * n[14] + m[13] * n[15],
            m[2] * n[12] + m[6] * n[13] + m[10] * n[14] + m[14] * n[15],
            m[3] * n[12] + m[7] * n[13] + m[11] * n[14] + m[15] * n[15],
        ]

    @staticmethod
    def translation_to_matrix(translation):
        # column major !
        return [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0,
                translation[0], translation[1], translation[2], 1.0]
