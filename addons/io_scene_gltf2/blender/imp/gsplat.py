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
    c0, c1 = c0.copy(), c1.copy()
    c0[:] = c1
    c1[:] = -c0
    # No change for c2
    return c0, c1, c2


def convert_sh_d2_batch(c0, c1, c2, c3, c4):
    c0, c2, c3, c4 = c0.copy(), c2.copy(), c3.copy(), c4.copy()
    c0[:] = c3
    c1 *= -1
    c2[:] = -0.5 * c2 - (SQRT3 / 2) * c4
    c3[:] = -c0
    c4[:] = -(SQRT3 / 2) * c2 + 0.5 * c4
    return c0, c1, c2, c3, c4


def convert_sh_d3_batch(c0, c1, c2, c3, c4, c5, c6):
    c0, c2, c3, c4, c5, c6 = (
        c0.copy(), c2.copy(), c3.copy(),
        c4.copy(), c5.copy(), c6.copy(),
    )
    c0[:] = -(SQRT10 / 4) * c3 + (SQRT6 / 4) * c5
    c1 *= -1
    c2[:] = -(SQRT6 / 4) * c3 - (SQRT10 / 4) * c5
    c3[:] = (SQRT6 / 4) * c2 + (SQRT10 / 4) * c0
    c4[:] = -0.25 * c4 - (SQRT15 / 4) * c6
    c5[:] = (SQRT10 / 4) * c2 - (SQRT6 / 4) * c0
    c6[:] = -(SQRT15 / 4) * c4 + 0.25 * c6
    return c0, c1, c2, c3, c4, c5, c6


def detect_sh_degree_from_gltf(prim, gltf):
    """Detect the SH degree from the glTF primitive."""

    degree = 3
    if any([attr for attr in prim.attributes.keys() if attr.startswith("KHR_gaussian_splatting:SH_DEGREE_3")]):
        return degree
    else:
        degree = 2

    if any([attr for attr in prim.attributes.keys() if attr.startswith("KHR_gaussian_splatting:SH_DEGREE_2")]):
        return degree
    else:
        degree = 1

    if any([attr for attr in prim.attributes.keys() if attr.startswith("KHR_gaussian_splatting:SH_DEGREE_1")]):
        return degree
    else:
        degree = 0

    if any([attr for attr in prim.attributes.keys() if attr.startswith("KHR_gaussian_splatting:SH_DEGREE_0")]):
        return degree
    else:
        gltf.log.error(
            "Could not detect SH degree for the current primitive. Defaulting to degree 0.")
    return degree
