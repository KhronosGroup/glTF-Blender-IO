# Copyright (c) 2018 The Khronos Group Inc.
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

from io_scene_gltf2.blender.exp.gltf2_blender_gather import cached
from io_scene_gltf2.blender.exp import gltf2_blender_extract
from io_scene_gltf2.blender.exp import gltf2_blender_gather_primitive_attributes

from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.io.exp import gltf2_io_binary_data
from io_scene_gltf2.io.com import gltf2_io_constants
from io_scene_gltf2.io.com import gltf2_io_debug


@cached
def gather_primitives(blender_object, export_settings):
    """
    Extract the mesh primitives from a blender object
    :param blender_object: the mesh object
    :param export_settings:
    :return: a list of glTF2 primitives
    """
    primitives = []
    blender_mesh = blender_object.data
    blender_vertex_groups = blender_object.vertex_groups
    blender_primitives = gltf2_blender_extract.extract_primitives(None, blender_mesh, blender_vertex_groups, export_settings)

    for internal_primitive in blender_primitives:

        primitive = gltf2_io.MeshPrimitive(
            attributes=__gather_attributes(internal_primitive, export_settings),
            extensions={},
            extras={},
            indices=__gather_indices(internal_primitive, export_settings),
            material=__gather_materials(internal_primitive, export_settings),
            mode=None,
            targets=__gather_targets(internal_primitive, export_settings)
        )
        primitives.append(primitive)

    return primitives


def __gather_materials(blender_primitive, export_settings):
    # if export_settings['gltf_materials']:
    #     material = get_material_index(glTF, internal_primitive['material'])
    #
    #     if get_material_requires_texcoords(glTF, material) and not export_settings['gltf_texcoords']:
    #         material = -1
    #
    #     if get_material_requires_normals(glTF, material) and not export_settings['gltf_normals']:
    #         material = -1
    #
    #     # Meshes/primitives without material are allowed.
    #     if material >= 0:
    #         primitive.material = material
    #     else:
    #         print_console('WARNING', 'Material ' + internal_primitive[
    #             'material'] + ' not found. Please assign glTF 2.0 material or enable Blinn-Phong material in export.')

    return None


def __gather_indices(blender_primitive, export_settings):
    indices = blender_primitive['indices']

    max_index = max(indices)
    if max_index < (1 << 8):
        component_type = gltf2_io_constants.GLTF_COMPONENT_TYPE_UNSIGNED_BYTE
    elif max_index < (1 << 16):
        component_type = gltf2_io_constants.GLTF_COMPONENT_TYPE_UNSIGNED_SHORT
    elif max_index < (1 << 32):
        component_type = gltf2_io_constants.GLTF_COMPONENT_TYPE_UNSIGNED_INT
    else:
        gltf2_io_debug.print_console('ERROR', 'Invalid max_index: ' + str(max_index))
        return None

    if export_settings['gltf_force_indices']:
        component_type = export_settings['gltf_indices']

    element_type = gltf2_io_constants.GLTF_DATA_TYPE_SCALAR
    return gltf2_io_binary_data.BinaryData(indices, component_type, element_type, group_label="primitive_indices")


def __gather_attributes(blender_primitive, export_settings):
    return gltf2_blender_gather_primitive_attributes.gather_primitive_attributes(blender_primitive, export_settings)


def __gather_targets(blender_primitive, blender_object, export_settings):
    if export_settings['gltf_morph']:
        targets = []
        blender_mesh = blender_object.data
        if blender_mesh.shape_keys is not None:
            morph_index = 0
            for blender_shape_key in blender_mesh.shape_keys.key_blocks:
                if blender_shape_key != blender_shape_key.relative_key:

                    target_position_id = 'MORPH_POSITION_' + str(morph_index)
                    target_normal_id = 'MORPH_NORMAL_' + str(morph_index)
                    target_tangent_id = 'MORPH_TANGENT_' + str(morph_index)

                    if blender_primitive["attributes"].get(target_position_id):
                        target = {}
                        internal_target_position = blender_primitive["attributes"][target_position_id]
                        target["POSITION"] = gltf2_io_binary_data.BinaryData(
                            internal_target_position,
                            gltf2_io_constants.GLTF_COMPONENT_TYPE_FLOAT,
                            gltf2_io_constants.GLTF_DATA_TYPE_VEC3,
                            group_label="primitives_targets"
                        )
                        if export_settings['gltf_normals'] \
                                and export_settings['gltf_morph_normal'] \
                                and blender_primitive["attributes"].get(target_normal_id):

                            internal_target_normal = blender_primitive["attributes"][target_normal_id]
                            target['NORMAL'] = gltf2_io_binary_data.BinaryData(
                                internal_target_normal,
                                gltf2_io_constants.GLTF_COMPONENT_TYPE_FLOAT,
                                gltf2_io_constants.GLTF_DATA_TYPE_VEC3,
                                group_label="primitives_targets"
                            )
                        if export_settings['gltf_tangents'] \
                                and export_settings['gltf_morph_tangent'] \
                                and blender_primitive["attributes"].get(target_tangent_id):
                            internal_target_tangent = blender_primitive["attributes"][target_tangent_id]
                            target['TANGENT'] = gltf2_io_binary_data.BinaryData(
                                internal_target_tangent,
                                gltf2_io_constants.GLTF_COMPONENT_TYPE_FLOAT,
                                gltf2_io_constants.GLTF_DATA_TYPE_VEC3,
                                group_label="primitives_targets"
                            )
                        targets.append(target)
                        morph_index += 1
        return targets
    return None
