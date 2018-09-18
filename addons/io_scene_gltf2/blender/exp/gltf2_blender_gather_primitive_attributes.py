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


from io_scene_gltf2.io.com import gltf2_io_constants
from io_scene_gltf2.io.exp import gltf2_io_binary_data


def gather_primitive_attributes(blender_primitive, export_settings):
    """
    Gathers the attributes, such as POSITION, NORMAL, TANGENT from a blender primitive
    :return: a dictionary of attributes
    """
    attributes = {}
    attributes.update(__gather_position(blender_primitive, export_settings))
    attributes.update(__gather_normal(blender_primitive, export_settings))
    attributes.update(__gather_tangent(blender_primitive, export_settings))
    attributes.update(__gather_texcoord(blender_primitive, export_settings))
    attributes.update(__gather_colors(blender_primitive, export_settings))
    attributes.update(__gather_skins(blender_primitive, export_settings))
    return attributes


def __gather_position(blender_primitive, export_settings):
    position = blender_primitive["attributes"]["POSITION"]
    componentType = gltf2_io_constants.GLTF_COMPONENT_TYPE_FLOAT
    return {
        "POSITION": gltf2_io_binary_data.BinaryData(
            position,
            componentType,
            gltf2_io_constants.GLTF_DATA_TYPE_VEC3,
            group_label="primitives_attributes"
        )
    }


def __gather_normal(blender_primitive, export_settings):
    if export_settings['gltf_normals']:
        normal = blender_primitive["attributes"]['NORMAL']
        return {
            "NORMAL": gltf2_io_binary_data.BinaryData(
                normal,
                gltf2_io_constants.GLTF_COMPONENT_TYPE_FLOAT,
                gltf2_io_constants.GLTF_DATA_TYPE_VEC3,
                group_label="primitives_attributes"
            )
        }
    return {}


def __gather_tangent(blender_primitive, export_settings):
    if export_settings['gltf_tangents']:
        if blender_primitive["attributes"].get('TANGENT') is not None:
            tangent = blender_primitive["attributes"]['TANGENT']
            return {
                "TANGENT": gltf2_io_binary_data.BinaryData(
                    tangent,
                    gltf2_io_constants.GLTF_COMPONENT_TYPE_FLOAT,
                    gltf2_io_constants.GLTF_DATA_TYPE_VEC3,
                    group_label="primitives_attributes"
                )
            }
    return {}


def __gather_texcoord(blender_primitive, export_settings):
    attributes = {}
    if export_settings['gltf_texcoords']:
        texcoord_index = 0
        texcoord_id = 'TEXCOORD_' + str(texcoord_index)
        while blender_primitive["attributes"].get(texcoord_id) is not None:
            texcoord = blender_primitive["attributes"][texcoord_id]
            attributes[texcoord_id] = gltf2_io_binary_data.BinaryData(
                texcoord,
                gltf2_io_constants.GLTF_COMPONENT_TYPE_FLOAT,
                gltf2_io_constants.GLTF_DATA_TYPE_VEC2,
                group_label="primitives_attributes"
            )
            texcoord_index += 1
            texcoord_id = 'TEXCOORD_' + str(texcoord_index)
    return attributes


def __gather_colors(blender_primitive, export_settings):
    attributes = {}
    if export_settings['gltf_colors']:
        color_index = 0
        color_id = 'COLOR_' + str(color_index)
        while blender_primitive["attributes"].get(color_id) is not None:
            internal_color = blender_primitive["attributes"][color_id]
            attributes[color_id] = gltf2_io_binary_data.BinaryData(
                internal_color,
                gltf2_io_constants.GLTF_COMPONENT_TYPE_FLOAT,
                gltf2_io_constants.GLTF_DATA_TYPE_VEC4,
                group_label="primitives_attributes"
            )
            color_index += 1
            color_id = 'COLOR_' + str(color_index)
    return attributes


def __gather_skins(blender_primitive, export_settings):
    attributes = {}
    if export_settings['gltf_skins']:
        bone_index = 0
        joint_id = 'JOINTS_' + str(bone_index)
        weight_id = 'WEIGHTS_' + str(bone_index)
        while blender_primitive["attributes"].get(joint_id) and blender_primitive["attributes"].get(weight_id):

            # joints
            internal_joint = blender_primitive["attributes"][joint_id]
            joint = gltf2_io_binary_data.BinaryData(
                internal_joint,
                gltf2_io_constants.GLTF_COMPONENT_TYPE_UNSIGNED_SHORT,
                gltf2_io_constants.GLTF_DATA_TYPE_VEC4,
                group_label="primitives_attributes"
            ),
            if joint < 0:
                # gltf2_io_debug('ERROR', 'Could not create accessor for ' + joint_id)
                break
            attributes[joint_id] = joint

            # weights
            internal_weight = blender_primitive["attributes"][weight_id]
            weight = gltf2_io_binary_data.BinaryData(
                internal_weight,
                gltf2_io_constants.GLTF_COMPONENT_TYPE_FLOAT,
                gltf2_io_constants.GLTF_DATA_TYPE_VEC4,
                group_label="primitives_attributes"
            )
            if weight < 0:
                # print_console('ERROR', 'Could not create accessor for ' + weight_id)
                break
            attributes[weight_id] = weight

            bone_index += 1
            joint_id = 'JOINTS_' + str(bone_index)
            weight_id = 'WEIGHTS_' + str(bone_index)
    return attributes