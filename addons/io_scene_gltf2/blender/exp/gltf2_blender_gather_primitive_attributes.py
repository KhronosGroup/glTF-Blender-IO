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
from ...io.exp.gltf2_io_user_extensions import export_user_extensions



def gather_primitive_attributes(blender_primitive, export_settings):
    """
    Gathers the attributes, such as POSITION, NORMAL, TANGENT, and all custom attributes from a blender primitive

    :return: a dictionary of attributes
    """
    attributes = {}

    # loop on each attribute extracted
    # for skinning, all linked attributes (WEIGHTS_ and JOINTS_) need to be calculated
    # in one shot (because of normalization), so we need to check that it is called only once.

    skin_done = False

    for attribute in blender_primitive["attributes"]:
        if (attribute.startswith("JOINTS_") or attribute.startswith("WEIGHTS_")) and skin_done is True:
            continue
        if attribute.startswith("MORPH_"):
            continue # Target for morphs will be managed later
        attributes.update(__gather_attribute(blender_primitive, attribute, export_settings))
        if (attribute.startswith("JOINTS_") or attribute.startswith("WEIGHTS_")):
            skin_done = True

    return attributes


def array_to_accessor(array, component_type, data_type, include_max_and_min=False):

    amax = None
    amin = None
    if include_max_and_min:
        amax = np.amax(array, axis=0).tolist()
        amin = np.amin(array, axis=0).tolist()

    return gltf2_io.Accessor(
        buffer_view=gltf2_io_binary_data.BinaryData(array.tobytes(), gltf2_io_constants.BufferViewTarget.ARRAY_BUFFER),
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

def __gather_skins(blender_primitive, export_settings):
    attributes = {}

    if not export_settings[gltf2_blender_export_keys.SKINS]:
        return attributes

    # Retrieve max set index
    max_bone_set_index = 0
    while blender_primitive["attributes"].get('JOINTS_' + str(max_bone_set_index)) and blender_primitive["attributes"].get('WEIGHTS_' + str(max_bone_set_index)):
        max_bone_set_index += 1
    max_bone_set_index -= 1

    # Here, a set represents a group of 4 weights.
    # So max_bone_set_index value:
    # if -1 => No weights
    # if 1 => Max 4 weights
    # if 2 => Max 8 weights
    # etc...

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
        joints = np.array(internal_joint, dtype= gltf2_io_constants.ComponentType.to_numpy_dtype(component_type))
        joints = joints.reshape(-1, 4)
        joint = array_to_accessor(
            joints,
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
        weight_id = 'WEIGHTS_' + str(s)
        weight_arrs[s] /= weight_total

        weight = array_to_accessor(
            weight_arrs[s],
            component_type=gltf2_io_constants.ComponentType.Float,
            data_type=gltf2_io_constants.DataType.Vec4,
            )
        attributes[weight_id] = weight

    return attributes


def __gather_attribute(blender_primitive, attribute, export_settings):
    data = blender_primitive["attributes"][attribute]


    include_max_and_mins = {
        "POSITION": True
    }

    if (attribute.startswith("_") or attribute.startswith("COLOR_")) and blender_primitive["attributes"][attribute]['component_type'] == gltf2_io_constants.ComponentType.UnsignedShort:
        # Byte Color vertex color, need to normalize

        data['data'] *= 65535
        data['data'] += 0.5  # bias for rounding
        data['data'] = data['data'].astype(np.uint16)

        export_user_extensions('gather_attribute_change', export_settings, attribute, data, True)

        return { attribute : gltf2_io.Accessor(
                buffer_view=gltf2_io_binary_data.BinaryData(data['data'].tobytes(), gltf2_io_constants.BufferViewTarget.ARRAY_BUFFER),
                byte_offset=None,
                component_type=data['component_type'],
                count=len(data['data']),
                extensions=None,
                extras=None,
                max=None,
                min=None,
                name=None,
                normalized=True,
                sparse=None,
                type=data['data_type'],
            )
        }

    elif attribute.startswith("JOINTS_") or attribute.startswith("WEIGHTS_"):
        return __gather_skins(blender_primitive, export_settings)

    else:

        export_user_extensions('gather_attribute_change', export_settings, attribute, data, False)

        return {
            attribute: array_to_accessor(
                data['data'],
                component_type=data['component_type'],
                data_type=data['data_type'],
                include_max_and_min=include_max_and_mins.get(attribute, False)
            )
        }
