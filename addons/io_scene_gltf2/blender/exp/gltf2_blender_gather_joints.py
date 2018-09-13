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
from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.io.com import gltf2_io_debug
from io_scene_gltf2.blender.exp import gltf2_blender_extract

import mathutils


@cached
def gather_joint(blender_bone, export_settings):
    """
    Generate a glTF2 node from a blender bone, as joints in glTF2 are simply nodes
    :param blender_bone: a blender PoseBone
    :param export_settings: the settings for this export
    :return: a glTF2 node (acting as a joint)
    """

    axis_basis_change = mathutils.Matrix.Identity(4)
    if export_settings['gltf_yup']:
        axis_basis_change = mathutils.Matrix(
            ((1.0, 0.0, 0.0, 0.0), (0.0, 0.0, 1.0, 0.0), (0.0, -1.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0)))

    # extract bone transform
    if blender_bone.parent is None:
        correction_matrix_local = axis_basis_change * blender_bone.bone.matrix_local
    else:
        correction_matrix_local = blender_bone.parent.bone.matrix_local.inverted() * blender_bone.bone.matrix_local
    matrix_basis = blender_bone.matrix_basis
    if export_settings['gltf_bake_skins']:
        gltf2_io_debug.print_console("WARNING", "glTF bake skins not supported")
        # matrix_basis = blender_object.convert_space(blender_bone, blender_bone.matrix, from_space='POSE',
        #                                             to_space='LOCAL')
    translation, rotation, scale = gltf2_blender_extract.decompose_transition(correction_matrix_local * matrix_basis,
                                                                              'JOINT', export_settings)

    # traverse into children
    children = []
    for bone in blender_bone.children:
        children.append(gather_joint(bone))

    # finally add to the joints array containing all the joints in the hierarchy
    return gltf2_io.Node(
        camera=None,
        children=children,
        extensions={},
        extras=None,
        matrix=[],
        mesh=None,
        name=blender_bone.name,
        rotation=rotation,
        scale=scale,
        skin=None,
        translation=translation,
        weights=None
    )
