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

import numpy as np

from . import gltf2_blender_export_keys
from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.io.com import gltf2_io_constants
from io_scene_gltf2.io.com import gltf2_io_debug
from io_scene_gltf2.io.exp import gltf2_io_binary_data


def gather_primitive_attributes(blender_primitive, export_settings):
    """
    Gathers the attributes, such as POSITION, NORMAL, TANGENT from a blender primitive.

    :return: a dictionary of attributes
    """
    attributes = {}
    attributes.update(__gather_position(blender_primitive, export_settings))
    attributes.update(__gather_normal(blender_primitive, export_settings))
    attributes.update(__gather_tangent(blender_primitive, export_settings))
    attributes.update(__gather_texcoord(blender_primitive, export_settings))
    attributes.update(__gather_colors(blender_primitive, export_settings))
    attributes.update(__gather_skins(blender_primitive, export_settings))

    # Add custom attributes
    for attribute in [attr_key for attr_key in blender_primitive["attributes"].keys() if attr_key[0] == "_"]:
        attributes.update(__gather_custom_attribute(blender_primitive, attribute, export_settings))

    return attributes


def array_to_accessor(array, component_type, data_type, include_max_and_min=False):
    dtype = gltf2_io_constants.ComponentType.to_numpy_dtype(component_type)
    num_elems = gltf2_io_constants.DataType.num_elements(data_type)

    if type(array) is not np.ndarray:
        array = np.array(array, dtype=dtype)
        array = array.reshape(len(array) // num_elems, num_elems)

    assert array.dtype == dtype
    assert array.shape[1] == num_elems

    amax = None
    amin = None
    if include_max_and_min:
        amax = np.amax(array, axis=0).tolist()
        amin = np.amin(array, axis=0).tolist()

    return gltf2_io.Accessor(
        buffer_view=gltf2_io_binary_data.BinaryData(array.tobytes()),
        byte_offset=None,
        component_type=component_type,
        count=len(array),
        extensions=None,
        extras=None,
        max=amax,
        min=amin,
        name=None,
        normalized=None,
        sparse=None,
        type=data_type,
    )


def __gather_position(blender_primitive, export_settings):
    position = blender_primitive["attributes"]["POSITION"]
    return {
        "POSITION": array_to_accessor(
            position['data'],
            component_type=position['component_type'],
            data_type=position['data_type'],
            include_max_and_min=True
        )
    }


def __gather_normal(blender_primitive, export_settings):
    if not export_settings[gltf2_blender_export_keys.NORMALS]:
        return {}
    if 'NORMAL' not in blender_primitive["attributes"]:
        return {}
    normal = blender_primitive["attributes"]['NORMAL']
    return {
        "NORMAL": array_to_accessor(
            normal['data'],
            component_type=normal['component_type'],
            data_type=normal['data_type'],
        )
    }


def __gather_tangent(blender_primitive, export_settings):
    if not export_settings[gltf2_blender_export_keys.TANGENTS]:
        return {}
    if 'TANGENT' not in blender_primitive["attributes"]:
        return {}
    tangent = blender_primitive["attributes"]['TANGENT']
    return {
        "TANGENT": array_to_accessor(
            tangent['data'],
            component_type=tangent['component_type'],
            data_type=tangent['data_type'],
        )
    }


def __gather_texcoord(blender_primitive, export_settings):
    attributes = {}
    if export_settings[gltf2_blender_export_keys.TEX_COORDS]:
        tex_coord_index = 0
        tex_coord_id = 'TEXCOORD_' + str(tex_coord_index)
        while blender_primitive["attributes"].get(tex_coord_id) is not None:
            tex_coord = blender_primitive["attributes"][tex_coord_id]
            attributes[tex_coord_id] = array_to_accessor(
                tex_coord['data'],
                component_type=tex_coord['component_type'],
                data_type=tex_coord['data_type'],
            )
            tex_coord_index += 1
            tex_coord_id = 'TEXCOORD_' + str(tex_coord_index)
    return attributes


def __gather_colors(blender_primitive, export_settings):
    attributes = {}
    if export_settings[gltf2_blender_export_keys.COLORS]:
        color_index = 0
        color_id = 'COLOR_' + str(color_index)
        while blender_primitive["attributes"].get(color_id) is not None:
            col = blender_primitive["attributes"][color_id]
            colors = col['data']

            if type(colors) is not np.ndarray:
                colors = np.array(colors, dtype=np.float32)
                colors = colors.reshape(len(colors) // 4, 4)

            normalized = False
            if col['component_type'] == gltf2_io_constants.ComponentType.UnsignedShort:
                # Convert to normalized ushorts
                colors *= 65535
                colors += 0.5  # bias for rounding
                colors = colors.astype(np.uint16)
                normalized = True        

            attributes[color_id] = gltf2_io.Accessor(
                buffer_view=gltf2_io_binary_data.BinaryData(colors.tobytes()),
                byte_offset=None,
                component_type=col['component_type'],
                count=len(colors),
                extensions=None,
                extras=None,
                max=None,
                min=None,
                name=None,
                normalized=normalized,
                sparse=None,
                type=col['data_type'],
            )

            color_index += 1
            color_id = 'COLOR_' + str(color_index)
    return attributes


def __gather_skins(blender_primitive, export_settings):
    attributes = {}

    if not export_settings[gltf2_blender_export_keys.SKINS]:
        return attributes

    # Retrieve max set index
    max_bone_set_index = 0
    while blender_primitive["attributes"].get('JOINTS_' + str(max_bone_set_index)) and blender_primitive["attributes"].get('WEIGHTS_' + str(max_bone_set_index)):
        max_bone_set_index += 1
    max_bone_set_index -= 1

    # If no skinning
    if max_bone_set_index < 0:
        return attributes

    if max_bone_set_index > 0 and not export_settings['gltf_all_vertex_influences']:
        gltf2_io_debug.print_console("WARNING", "There are more than 4 joint vertex influences."
                                                "The 4 with highest weight will be used (and normalized).")

        # Take into account only the first set of 4 weights
        max_bone_set_index = 0

    # Convert weights to numpy arrays, and setting joints
    weight_arrs = []
    for s in range(0, max_bone_set_index+1):

        weight_id = 'WEIGHTS_' + str(s)
        weight = blender_primitive["attributes"][weight_id]
        weight = np.array(weight, dtype=np.float32)
        weight = weight.reshape(len(weight) // 4, 4)
        weight_arrs.append(weight)


        # joints
        joint_id = 'JOINTS_' + str(s)
        internal_joint = blender_primitive["attributes"][joint_id]
        component_type = gltf2_io_constants.ComponentType.UnsignedShort
        if max(internal_joint) < 256:
            component_type = gltf2_io_constants.ComponentType.UnsignedByte
        joint = array_to_accessor(
            internal_joint,
            component_type,
            data_type=gltf2_io_constants.DataType.Vec4,
        )
        attributes[joint_id] = joint

    # Sum weights for each vertex
    for s in range(0, max_bone_set_index+1):
        sums = weight_arrs[s].sum(axis=1)
        if s == 0:
            weight_total = sums
        else:
            weight_total += sums

    # Normalize weights so they sum to 1
    weight_total = weight_total.reshape(-1, 1)
    for s in range(0, max_bone_set_index+1):
        weight_arrs[s] /= weight_total

        weight = array_to_accessor(
            weight_arrs[s],
            component_type=gltf2_io_constants.ComponentType.Float,
            data_type=gltf2_io_constants.DataType.Vec4,
            )
        attributes[weight_id] = weight

    return attributes

def __gather_custom_attribute(blender_primitive, attribute, export_settings):
    data = blender_primitive["attributes"][attribute]
    return {
        attribute: array_to_accessor(
            data['data'],
            component_type=data['component_type'],
            data_type=data['data_type'],
            include_max_and_min=True
        )
    }