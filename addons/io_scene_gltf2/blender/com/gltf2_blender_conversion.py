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
from math import sqrt, sin, cos

def matrix_gltf_to_blender(mat_input):
    """Matrix from glTF format to Blender format."""
    mat = Matrix([mat_input[0:4], mat_input[4:8], mat_input[8:12], mat_input[12:16]])
    mat.transpose()
    return mat

def loc_gltf_to_blender(loc):
    """Location."""
    return loc

def scale_gltf_to_blender(scale):
    """Scaling."""
    return scale

def quaternion_gltf_to_blender(q):
    """Quaternion from glTF to Blender."""
    return Quaternion([q[3], q[0], q[1], q[2]])

def scale_to_matrix(scale):
    """Scale to matrix."""
    mat = Matrix()
    for i in range(3):
        mat[i][i] = scale[i]

    return mat

def correction_rotation():
    """Correction of Rotation."""
    # Correction is needed for lamps, because Yup2Zup is not written in vertices
    # and lamps has no vertices :)
    return Quaternion((sqrt(2)/2, -sqrt(2)/2, 0.0, 0.0)).to_matrix().to_4x4()

def texture_transform_blender_to_gltf(mapping_transform):
    """
    Converts the offset/rotation/scale from a Mapping node applied in Blender's
    UV space to the equivalent KHR_texture_transform.
    """
    offset = mapping_transform.get('offset', [0, 0])
    rotation = mapping_transform.get('rotation', 0)
    scale = mapping_transform.get('scale', [1, 1])
    return {
        'offset': [
            offset[0] - scale[1] * sin(rotation),
            1 - offset[1] - scale[1] * cos(rotation),
        ],
        'rotation': rotation,
        'scale': [scale[0], scale[1]],
    }

def texture_transform_gltf_to_blender(texture_transform):
    """
    Converts a KHR_texture_transform into the equivalent offset/rotation/scale
    for a Mapping node applied in Blender's UV space.
    """
    offset = texture_transform.get('offset', [0, 0])
    rotation = texture_transform.get('rotation', 0)
    scale = texture_transform.get('scale', [1, 1])
    return {
        'offset': [
            offset[0] + scale[1] * sin(rotation),
            1 - offset[1] - scale[1] * cos(rotation),
        ],
        'rotation': rotation,
        'scale': [scale[0], scale[1]],
    }
