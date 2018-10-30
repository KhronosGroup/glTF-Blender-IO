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

from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached
from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.io.exp import gltf2_io_binary_data
from io_scene_gltf2.io.com import gltf2_io_constants
from io_scene_gltf2.blender.exp import gltf2_blender_gather_joints
from io_scene_gltf2.blender.exp import gltf2_blender_gather_nodes
from io_scene_gltf2.blender.com import gltf2_blender_math
import mathutils


@cached
def gather_skin(blender_object, export_settings):
    """
    Gather armatures, bones etc into a glTF2 skin object
    :param blender_object: the object which may contain a skin
    :param export_settings:
    :return: a glTF2 skin object
    """
    if not __filter_skin(blender_object, export_settings):
        return None

    return gltf2_io.Skin(
                    extensions=__gather_extensions(blender_object, export_settings),
                    extras=__gather_extras(blender_object, export_settings),
                    inverse_bind_matrices=__gather_inverse_bind_matrices(blender_object, export_settings),
                    joints=__gather_joints(blender_object, export_settings),
                    name=__gather_name(blender_object, export_settings),
                    skeleton=__gather_skeleton(blender_object, export_settings)
    )


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

    axis_basis_change = mathutils.Matrix.Identity(4)
    if export_settings['gltf_yup']:
        axis_basis_change = mathutils.Matrix(
            ((1.0, 0.0, 0.0, 0.0), (0.0, 0.0, 1.0, 0.0), (0.0, -1.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0)))

    # # artificial torso, as needed by glTF
    # inverse_bind_matrix = blender_object.matrix_world.inverted() * axis_basis_change.inverted()
    # for column in range(0, 4):
    #     for row in range(0, 4):
    #         inverse_matrices.append(inverse_bind_matrix[row][column])

    #
    for blender_bone in blender_object.pose.bones:
        inverse_bind_matrix = gltf2_blender_math.multiply(axis_basis_change, blender_bone.bone.matrix_local)
        bind_shape_matrix = gltf2_blender_math.multiply(gltf2_blender_math.multiply(axis_basis_change, blender_object.matrix_world.inverted()), axis_basis_change.inverted())

        inverse_bind_matrix = gltf2_blender_math.multiply(inverse_bind_matrix.inverted(), bind_shape_matrix)
        for column in range(0, 4):
            for row in range(0, 4):
                inverse_matrices.append(inverse_bind_matrix[row][column])

    binary_data = gltf2_io_binary_data.BinaryData.from_list(inverse_matrices, gltf2_io_constants.ComponentType.Float)
    return gltf2_io.Accessor(
        buffer_view=binary_data,
        byte_offset=None,
        component_type=gltf2_io_constants.ComponentType.Float,
        count=len(inverse_matrices) // gltf2_io_constants.DataType.num_elements(gltf2_io_constants.DataType.Mat4),
        extensions=None,
        extras=None,
        max=None,
        min=None,
        name=None,
        normalized=None,
        sparse=None,
        type=gltf2_io_constants.DataType.Mat4
    )


def __gather_joints(blender_object, export_settings):
    # # the skeletal hierarchy groups below a 'root' joint
    # # TODO: add transform?
    # torso = gltf2_io.Node(
    #     camera=None,
    #     children=[],
    #     extensions={},
    #     extras=None,
    #     matrix=[],
    #     mesh=None,
    #     name="Skeleton_" + blender_object.name,
    #     rotation=None,
    #     scale=None,
    #     skin=None,
    #     translation=None,
    #     weights=None
    # )

    root_joints = []
    # build the hierarchy of nodes out of the bones
    for blender_bone in blender_object.pose.bones:
        if not blender_bone.parent:
            root_joints.append(gltf2_blender_gather_joints.gather_joint(blender_bone, export_settings))

    # joints is a flat list containing all nodes belonging to the skin
    joints = []

    def __collect_joints(node):
        joints.append(node)
        for child in node.children:
            __collect_joints(child)
    for joint in root_joints:
        __collect_joints(joint)

    return joints


def __gather_name(blender_object, export_settings):
    return blender_object.name


def __gather_skeleton(blender_object, export_settings):
    # In the future support the result of https://github.com/KhronosGroup/glTF/pull/1195
    return None #gltf2_blender_gather_nodes.gather_node(blender_object, export_settings)
