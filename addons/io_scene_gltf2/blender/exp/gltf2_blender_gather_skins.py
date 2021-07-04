# Copyright 2018-2021 The glTF-Blender-IO authors.
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

import mathutils
from . import gltf2_blender_export_keys
from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached
from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.io.exp import gltf2_io_binary_data
from io_scene_gltf2.io.com import gltf2_io_constants
from io_scene_gltf2.blender.exp import gltf2_blender_gather_accessors
from io_scene_gltf2.blender.exp import gltf2_blender_gather_joints
from io_scene_gltf2.io.exp.gltf2_io_user_extensions import export_user_extensions
from io_scene_gltf2.blender.exp import gltf2_blender_gather_tree


#@cached
def gather_skin(armature_uuid, export_settings):
    """
    Gather armatures, bones etc into a glTF2 skin object.

    :param blender_object: the object which may contain a skin
    :param export_settings:
    :return: a glTF2 skin object
    """

    blender_armature_object = export_settings['vtree'].nodes[armature_uuid].blender_object

    if not __filter_skin(blender_armature_object, export_settings):
        return None

    skin = gltf2_io.Skin(
        extensions=__gather_extensions(blender_armature_object, export_settings),
        extras=__gather_extras(blender_armature_object, export_settings),
        inverse_bind_matrices=__gather_inverse_bind_matrices(armature_uuid, export_settings),
        joints=__gather_joints(armature_uuid, export_settings),
        name=__gather_name(blender_armature_object, export_settings),
        skeleton=__gather_skeleton(blender_armature_object, export_settings)
    )

    export_user_extensions('gather_skin_hook', export_settings, skin, blender_armature_object)

    return skin


def __filter_skin(blender_armature_object, export_settings):
    if not export_settings[gltf2_blender_export_keys.SKINS]:
        return False
    if blender_armature_object.type != 'ARMATURE' or len(blender_armature_object.pose.bones) == 0:
        return False

    return True


def __gather_extensions(blender_armature_object, export_settings):
    return None


def __gather_extras(blender_armature_object, export_settings):
    return None

def __gather_inverse_bind_matrices(armature_uuid, export_settings):

    blender_armature_object = export_settings['vtree'].nodes[armature_uuid].blender_object

    axis_basis_change = mathutils.Matrix.Identity(4)
    if export_settings[gltf2_blender_export_keys.YUP]:
        axis_basis_change = mathutils.Matrix(
            ((1.0, 0.0, 0.0, 0.0), (0.0, 0.0, 1.0, 0.0), (0.0, -1.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0)))

    if export_settings['gltf_def_bones'] is False:
        # build the hierarchy of nodes out of the bones
        root_bones = []
        for blender_bone in blender_armature_object.pose.bones:
            if not blender_bone.parent:
                root_bones.append(blender_bone)
    else:
        _, children_, root_bones = get_bone_tree_vnode(export_settings['vtree'].nodes[armature_uuid], export_settings)
        root_bones = [export_settings['vtree'].nodes[r].blender_bone for r in root_bones]

    matrices = []

    # traverse the matrices in the same order as the joints and compute the inverse bind matrix
    def __collect_matrices(bone):
        inverse_bind_matrix = (
            axis_basis_change @
            (
                blender_armature_object.matrix_world @
                bone.bone.matrix_local
            )
        ).inverted()
        matrices.append(inverse_bind_matrix)

        if export_settings['gltf_def_bones'] is False:
            for child in bone.children:
                __collect_matrices(child)
        else:
            if bone.name in children_.keys():
                for child in children_[bone.name]:
                    __collect_matrices(blender_armature_object.pose.bones[child])

    # start with the "root" bones and recurse into children, in the same ordering as the how joints are gathered
    for root_bone in root_bones:
        __collect_matrices(root_bone)

    # flatten the matrices
    inverse_matrices = []
    for matrix in matrices:
        for column in range(0, 4):
            for row in range(0, 4):
                inverse_matrices.append(matrix[row][column])

    binary_data = gltf2_io_binary_data.BinaryData.from_list(inverse_matrices, gltf2_io_constants.ComponentType.Float)
    return gltf2_blender_gather_accessors.gather_accessor(
        binary_data,
        gltf2_io_constants.ComponentType.Float,
        len(inverse_matrices) // gltf2_io_constants.DataType.num_elements(gltf2_io_constants.DataType.Mat4),
        None,
        None,
        gltf2_io_constants.DataType.Mat4,
        export_settings
    )


def __gather_joints(armature_uuid, export_settings):
    root_joints = []
    blender_armature_object = export_settings['vtree'].nodes[armature_uuid].blender_object
    if export_settings['gltf_def_bones'] is False:
        # build the hierarchy of nodes out of the bones
        for blender_bone in blender_armature_object.pose.bones:
            if not blender_bone.parent:
                root_joints.append(gltf2_blender_gather_joints.gather_joint_vnode(export_settings['vtree'].nodes[armature_uuid].bones[blender_bone.name], export_settings))
    else:
        _, children_, root_joints = get_bone_tree_vnode(export_settings['vtree'].nodes[armature_uuid], export_settings)
        root_joints = [gltf2_blender_gather_joints.gather_joint_vnode(export_settings['vtree'].nodes[armature_uuid].bones[export_settings['vtree'].nodes[i].blender_bone.name], export_settings) for i in root_joints]

    # joints is a flat list containing all nodes belonging to the skin
    joints = []

    def __collect_joints(node):
        joints.append(node)
        if export_settings['gltf_def_bones'] is False:
            for child in node.children:
                __collect_joints(child)
        else:
            if node.name in children_.keys():
                for child in children_[node.name]:
                    __collect_joints(gltf2_blender_gather_joints.gather_joint_vnode(export_settings['vtree'].joint_to_vnode[id(blender_armature_object.pose.bones[child])], export_settings))

    for joint in root_joints:
        __collect_joints(joint)

    return joints


def __gather_name(blender_armature_object, export_settings):
    return blender_armature_object.name


def __gather_skeleton(blender_armature_object, export_settings):
    # In the future support the result of https://github.com/KhronosGroup/glTF/pull/1195
    return None


@cached
def get_bone_tree_vnode(vnode, export_settings):
    # Same as get_bone_tree, but with vnode

    vtree = export_settings['vtree']

    vnodes = []
    children = {}
    root_vnodes = []

    def get_parent(vnode):
        vnodes.append(vnode)
        if vnode.parent_bone_uuid is not None:
            if vnode.parent_bone_uuid not in children.keys():
                children[vnode.parent_bone_uuid] = []
            children[vnode.parent_bone_uuid].append(vnode.uuid)
            get_parent(vtree.nodes[vnode.parent_bone_uuid])
        else:
            root_vnodes.append(vnode.uuid)

    # Retrieve list of deformation bone vnode
    bone_names = [(n.blender_bone.name, n.uuid) for n in vtree.nodes.values() if n.blender_type == gltf2_blender_gather_tree.VExportNode.BONE and n.blender_object == vnode.blender_object]

    for b, uuid_ in [(b, uuid_) for (b, uuid_) in bone_names if vnode.blender_object.data.bones[b].use_deform is True]:
        get_parent(vtree.nodes[uuid_])

    # remove duplicates
    for k, v in children.items():
        children[k] = list(set(v))
    list_ = list(set(vnodes))
    root_ = list(set(root_vnodes))
    return list_, children, root_


@cached
def get_bone_tree(blender_armature_object): #TODO export settings at end of parameters ????

    bones = []
    children = {}
    root_bones = []

    def get_parent(bone):
        bones.append(bone.name)
        if bone.parent is not None:
            if bone.parent.name not in children.keys():
                children[bone.parent.name] = []
            children[bone.parent.name].append(bone.name)
            get_parent(bone.parent)
        else:
            root_bones.append(bone.name)

    for bone in [b for b in blender_armature_object.data.bones if b.use_deform is True]:
        get_parent(bone)

    # remove duplicates
    for k, v in children.items():
        children[k] = list(set(v))
    list_ = list(set(bones))
    root_ = list(set(root_bones))
    return [blender_armature_object.data.bones[b] for b in list_], children, [blender_armature_object.pose.bones[b] for b in root_]
