# Copyright 2018-2019 The glTF-Blender-IO authors.
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
from io_scene_gltf2.io.com import gltf2_io_debug
from io_scene_gltf2.blender.exp import gltf2_blender_extract
from io_scene_gltf2.blender.com import gltf2_blender_math
from io_scene_gltf2.blender.exp import gltf2_blender_gather_skins


@cached
def gather_joint(blender_object, blender_bone, export_settings):
    """
    Generate a glTF2 node from a blender bone, as joints in glTF2 are simply nodes.

    :param blender_bone: a blender PoseBone
    :param export_settings: the settings for this export
    :return: a glTF2 node (acting as a joint)
    """
    axis_basis_change = mathutils.Matrix.Identity(4)
    if export_settings[gltf2_blender_export_keys.YUP]:
        axis_basis_change = mathutils.Matrix(
            ((1.0, 0.0, 0.0, 0.0), (0.0, 0.0, 1.0, 0.0), (0.0, -1.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0)))

    # extract bone transform
    if blender_bone.parent is None:
        correction_matrix_local = gltf2_blender_math.multiply(axis_basis_change, blender_bone.bone.matrix_local)
    else:
        correction_matrix_local = gltf2_blender_math.multiply(
            blender_bone.parent.bone.matrix_local.inverted(), blender_bone.bone.matrix_local)
    matrix_basis = blender_bone.matrix_basis
    trans, rot, sca = gltf2_blender_extract.decompose_transition(
        gltf2_blender_math.multiply(correction_matrix_local, matrix_basis), export_settings)
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
        for bone in blender_bone.children:
            children.append(gather_joint(blender_object, bone, export_settings))
    else:
        _, children_, _ = gltf2_blender_gather_skins.get_bone_tree(None, blender_bone.id_data)
        if blender_bone.name in children_.keys():
            for bone in children_[blender_bone.name]:
                children.append(gather_joint(blender_object, blender_bone.id_data.pose.bones[bone], export_settings))

    # finally add to the joints array containing all the joints in the hierarchy
    return gltf2_io.Node(
        camera=None,
        children=children,
        extensions=None,
        extras=None,
        matrix=None,
        mesh=None,
        name=blender_bone.name,
        rotation=rotation,
        scale=scale,
        skin=None,
        translation=translation,
        weights=None
    )
