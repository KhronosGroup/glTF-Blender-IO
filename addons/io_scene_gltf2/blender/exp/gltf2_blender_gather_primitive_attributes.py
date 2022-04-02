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
            position,
            component_type=gltf2_io_constants.ComponentType.Float,
            data_type=gltf2_io_constants.DataType.Vec3,
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
            normal,
            component_type=gltf2_io_constants.ComponentType.Float,
            data_type=gltf2_io_constants.DataType.Vec3,
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
            tangent,
            component_type=gltf2_io_constants.ComponentType.Float,
            data_type=gltf2_io_constants.DataType.Vec4,
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
                tex_coord,
                component_type=gltf2_io_constants.ComponentType.Float,
                data_type=gltf2_io_constants.DataType.Vec2,
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
            colors = blender_primitive["attributes"][color_id]

            if type(colors) is not np.ndarray:
                colors = np.array(colors, dtype=np.float32)
                colors = colors.reshape(len(colors) // 4, 4)

            # Convert to normalized ushorts
            colors *= 65535
            colors += 0.5  # bias for rounding
            colors = colors.astype(np.uint16)

            attributes[color_id] = gltf2_io.Accessor(
                buffer_view=gltf2_io_binary_data.BinaryData(colors.tobytes()),
                byte_offset=None,
                component_type=gltf2_io_constants.ComponentType.UnsignedShort,
                count=len(colors),
                extensions=None,
                extras=None,
                max=None,
                min=None,
                name=None,
                normalized=True,
                sparse=None,
                type=gltf2_io_constants.DataType.Vec4,
            )

            color_index += 1
            color_id = 'COLOR_' + str(color_index)
    return attributes


def __gather_skins(blender_primitive, export_settings):
    attributes = {}
    factors = {}

    if not export_settings[gltf2_blender_export_keys.SKINS]:
        return attributes

    # Retrieve max set index
    max_bone_set_index = 0
    while blender_primitive["attributes"].get('JOINTS_' + str(max_bone_set_index)) and blender_primitive["attributes"].get('WEIGHTS_' + str(max_bone_set_index)):
        max_bone_set_index += 1
    max_bone_set_index -= 1

    if max_bone_set_index > 0 and not export_settings['gltf_all_vertex_influences']:
        gltf2_io_debug.print_console("WARNING", "There are more than 4 joint vertex influences."
                                                "The 4 with highest weight will be used (and normalized).")

        # Take into account only the first set of 4 weights
        max_bone_set_index = 0

    for s in range(0, max_bone_set_index+1):
        joint_id = 'JOINTS_' + str(s)
        weight_id = 'WEIGHTS_' + str(s)

        # joints
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

        # weights
        internal_weight = blender_primitive["attributes"][weight_id]
        
        for idx in range(0, len(internal_weight), 4):
            if max_bone_set_index == 0:
            # Only one set, we can directly normalized
                weight_slice = internal_weight[idx:idx + 4]
                total = sum(weight_slice)
                if total > 0:
                    factor = 1.0 / total
                    internal_weight[idx:idx + 4] = [w * factor for w in weight_slice]
            else:
                # We need to normalize across all sets
                # For first set, retrieve all data, and calculate norm factor, and apply it
                if s == 0:
                    total_weights = np.empty(0, dtype=float)
                    total_weights = np.append(total_weights, internal_weight[idx:idx + 4])
                    for s_loop in range(1, max_bone_set_index+1):
                        total_weights = np.append(total_weights, blender_primitive["attributes"]["WEIGHTS_" + str(s_loop)][idx:idx + 4])

                    total = sum(total_weights)
                    if total > 0:
                        factors[idx] = 1.0 / total
                    else:
                        factors[idx] = 1.0
                    
                    # apply for this first set
                    internal_weight[idx:idx + 4] = [w * factors[idx] for w in internal_weight[idx:idx + 4]]


                else:
                    # We already calcule the norm factor, apply it
                    internal_weight[idx:idx + 4] = [w * factors[idx] for w in internal_weight[idx:idx + 4]]

        weight = array_to_accessor(
            internal_weight,
            component_type=gltf2_io_constants.ComponentType.Float,
            data_type=gltf2_io_constants.DataType.Vec4,
            )
        attributes[weight_id] = weight

    return attributes
