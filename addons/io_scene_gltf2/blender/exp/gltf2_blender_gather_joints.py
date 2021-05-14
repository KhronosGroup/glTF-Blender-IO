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
from io_scene_gltf2.blender.exp import gltf2_blender_gather_skins
from io_scene_gltf2.io.exp.gltf2_io_user_extensions import export_user_extensions
from ..com.gltf2_blender_extras import generate_extras
from io_scene_gltf2.blender.exp import gltf2_blender_gather_tree

@cached
def gather_joint_vnode(vnode, export_settings):
    """
    Generate a glTF2 node from a blender bone, as joints in glTF2 are simply nodes.

    :param blender_bone: a blender PoseBone
    :param export_settings: the settings for this export
    :return: a glTF2 node (acting as a joint)
    """
    vtree = export_settings['vtree']
    blender_object = vtree.nodes[vnode].blender_object
    blender_bone = vtree.nodes[vnode].blender_bone

    axis_basis_change = mathutils.Matrix.Identity(4)
    if export_settings[gltf2_blender_export_keys.YUP]:
        axis_basis_change = mathutils.Matrix(
            ((1.0, 0.0, 0.0, 0.0), (0.0, 0.0, 1.0, 0.0), (0.0, -1.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0)))

    # extract bone transform
    if blender_bone.parent is None:
        correction_matrix_local = axis_basis_change @ blender_bone.bone.matrix_local
    else:
        correction_matrix_local = (
            blender_bone.parent.bone.matrix_local.inverted() @
            blender_bone.bone.matrix_local
        )

    if (blender_bone.bone.use_inherit_rotation == False or blender_bone.bone.inherit_scale != "FULL") and blender_bone.parent != None:
        rest_mat = (blender_bone.parent.bone.matrix_local.inverted_safe() @ blender_bone.bone.matrix_local)
        matrix_basis = (rest_mat.inverted_safe() @ blender_bone.parent.matrix.inverted_safe() @ blender_bone.matrix)
    else:
        matrix_basis = blender_bone.matrix
        matrix_basis = blender_object.convert_space(pose_bone=blender_bone, matrix=matrix_basis, from_space='POSE', to_space='LOCAL')

    trans, rot, sca = (correction_matrix_local @ matrix_basis).decompose()
    translation, rotation, scale = (None, None, None)
    if trans[0] != 0.0 or trans[1] != 0.0 or trans[2] != 0.0:
        translation = [trans[0], trans[1], trans[2]]
    if rot[0] != 1.0 or rot[1] != 0.0 or rot[2] != 0.0 or rot[3] != 0.0:
        rotation = [rot[1], rot[2], rot[3], rot[0]]
    if sca[0] != 1.0 or sca[1] != 1.0 or sca[2] != 1.0:
        scale = [sca[0], sca[1], sca[2]]

    # traverse into children
    children = []

    if export_settings["gltf_def_bones"] is False:
        for bone_uuid in [c for c in vtree.nodes[vnode].children if vtree.nodes[c].blender_type == gltf2_blender_gather_tree.VExportNode.BONE]:
            children.append(gather_joint_vnode(bone_uuid, export_settings))
    else:
        _, children_, _ = gltf2_blender_gather_skins.get_bone_tree_vnode(blender_object, export_settings)
        if vtree.nodes[vnode].uuid in children_.keys():
            for bone_uuid in children_[vtree.nodes[vnode].uuid]:
                children.append(gather_joint_vnode(bone_uuid, export_settings))

    # finally add to the joints array containing all the joints in the hierarchy
    node = gltf2_io.Node(
        camera=None,
        children=children,
        extensions=None,
        extras=__gather_extras(blender_bone, export_settings),
        matrix=None,
        mesh=None,
        name=blender_bone.name,
        rotation=rotation,
        scale=scale,
        skin=None,
        translation=translation,
        weights=None
    )

    export_user_extensions('gather_joint_hook', export_settings, node, blender_bone)

    vtree.nodes[vnode].node = node

    return node

def __gather_extras(blender_bone, export_settings):
    if export_settings['gltf_extras']:
        return generate_extras(blender_bone.bone)
    return None
