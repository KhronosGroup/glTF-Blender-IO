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
