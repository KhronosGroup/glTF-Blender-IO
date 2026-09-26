# Copyright 2026 The glTF-Blender-IO authors.
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

import numpy as np

SQRT3 = np.sqrt(3)
SQRT6 = np.sqrt(6)
SQRT10 = np.sqrt(10)
SQRT15 = np.sqrt(15)


# Coefficient conversion from Yup to Zup

def convert_sh_d1_batch(c0, c1, c2):
    o0, o1 = c0.copy(), c1.copy()
    new_c0 = o1
    new_c1 = -o0
    # No change for c2
    return new_c0, new_c1, c2


def convert_sh_d2_batch(c0, c1, c2, c3, c4):
    o0, o2, o3, o4 = c0.copy(), c2.copy(), c3.copy(), c4.copy()
    new_c0 = o3
    new_c1 = -c1
    new_c2 = -0.5 * o2 - (SQRT3 / 2) * o4
    new_c3 = -o0
    new_c4 = -(SQRT3 / 2) * o2 + 0.5 * o4
    return new_c0, new_c1, new_c2, new_c3, new_c4


def convert_sh_d3_batch(c0, c1, c2, c3, c4, c5, c6):
    o0, o2, o3, o4, o5, o6 = (
        c0.copy(), c2.copy(), c3.copy(),
        c4.copy(), c5.copy(), c6.copy(),
    )
    new_c0 = -(SQRT10 / 4) * o3 + (SQRT6 / 4) * o5
    new_c1 = -c1
    new_c2 = -(SQRT6 / 4) * o3 - (SQRT10 / 4) * o5
    new_c3 = (SQRT6 / 4) * o2 + (SQRT10 / 4) * o0
    new_c4 = -0.25 * o4 - (SQRT15 / 4) * o6
    new_c5 = (SQRT10 / 4) * o2 - (SQRT6 / 4) * o0
    new_c6 = -(SQRT15 / 4) * o4 + 0.25 * o6
    return new_c0, new_c1, new_c2, new_c3, new_c4, new_c5, new_c6
