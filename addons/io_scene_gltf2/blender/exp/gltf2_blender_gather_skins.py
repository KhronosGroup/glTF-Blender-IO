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

from io_scene_gltf2.blender.exp.gltf2_blender_gather import cached
from io_scene_gltf2.blender.exp import gltf2_blender_extract
from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.io.exp import  gltf2_io_generate
from io_scene_gltf2.io.exp import gltf2_io_binary_data
from io_scene_gltf2.io.com import gltf2_io_constants

import mathutils


@cached
def gather_skin(blender_object, export_settings):
    if not __filter_skin(blender_object, export_settings):
        return None

    skin = gltf2_io.Skin(
                    extensions=__gather_extensions(blender_object, export_settings),
                    extras=__gather_extras(blender_object, export_settings),
                    inverse_bind_matrices=__gather_inverse_bind_matrices(blender_object, export_settings),
                    joints=__gather_joints(blender_object, export_settings),
                    name=__gather_name(blender_object, export_settings),
                    skeleton=__gather_skeleton(blender_object, export_settings)

    )

    return skin


def __filter_skin(blender_object, export_settings):
    if not export_settings['gltf_skins']:
        return False
    if blender_object.type != 'ARMATURE' or len(blender_object.pose.bones) == 0:
        return False

    return True


def __gather_extensions(blender_object, export_settings):
    return None


def __gather_extras(blender_object, export_settings):
    return None


def __gather_inverse_bind_matrices(blender_object, export_settings):
    inverse_matrices = []
    for blender_bone in blender_object.pose.bones:
        axis_basis_change = mathutils.Matrix.Identity(4)
        if export_settings['gltf_yup']:
            axis_basis_change  = mathutils.Matrix(
                ((1.0, 0.0, 0.0, 0.0), (0.0, 0.0, 1.0, 0.0), (0.0, -1.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0)))

        inverse_bind_matrix = axis_basis_change * blender_bone.bone.matrix_local
        bind_shape_matrix = axis_basis_change * blender_object.matrix_world.inverted() * blender_object_child.matrix_world * axis_basis_change.inverted()
        inverse_bind_matrix = inverse_bind_matrix.inverted() * bind_shape_matrix
        for column in range(0, 4):
            for row in range(0, 4):
                inverse_matrices.append(inverse_bind_matrix[row][column])

    inverse_bind_matrices = gltf2_io_binary_data.BinaryData(
        data=inverse_matrices,
        component_type=gltf2_io_constants.GLTF_COMPONENT_TYPE_FLOAT,
        element_type=gltf2_io_constants.GLTF_DATA_TYPE_MAT4
    )

    return inverse_bind_matrices


def __gather_joints(blender_object, export_settings):
    return []


def __gather_name(blender_object, export_settings):
    return None


def __gather_skeleton(blender_object, export_settings):
    return None