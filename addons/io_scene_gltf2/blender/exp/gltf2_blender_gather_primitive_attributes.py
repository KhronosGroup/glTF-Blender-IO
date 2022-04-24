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
from io_scene_gltf2.io.com.gltf2_io_debug import print_console


def gather_primitive_attributes(blender_primitive, export_settings):
    """
    Gathers the attributes, such as POSITION, NORMAL, TANGENT from a blender primitive.

    :return: a dictionary of attributes
    """

    interleaving_info = None
    if export_settings['gltf_attributes_interleaving'] == "INTERLEAVED":
        interleaving_info = {"names": [], "data": []}

    attributes = {}
    attributes.update(__gather_position(blender_primitive, interleaving_info, export_settings))
    attributes.update(__gather_normal(blender_primitive, interleaving_info, export_settings))
    attributes.update(__gather_tangent(blender_primitive, interleaving_info, export_settings))
    attributes.update(__gather_texcoord(blender_primitive, interleaving_info, export_settings))
    attributes.update(__gather_colors(blender_primitive, interleaving_info, export_settings))
    attributes.update(__gather_skins(blender_primitive, interleaving_info, export_settings))

    if interleaving_info:
        __interleave_data(attributes, interleaving_info)

    return attributes


def array_to_accessor(array, component_type, data_type, include_max_and_min=False, interleaving_info=None):
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

    buffer_view = None
    if interleaving_info is None:
        buffer_view = gltf2_io_binary_data.BinaryData(array.tobytes())
    else:
        interleaving_info["data"].append(array)

    return gltf2_io.Accessor(
        buffer_view=buffer_view,
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


def __gather_position(blender_primitive, interleaving_info, export_settings):
    position = blender_primitive["attributes"]["POSITION"]

    if interleaving_info:
        interleaving_info["names"].append("POSITION")

    return {
        "POSITION": array_to_accessor(
            position,
            component_type=gltf2_io_constants.ComponentType.Float,
            data_type=gltf2_io_constants.DataType.Vec3,
            include_max_and_min=True,
            interleaving_info=interleaving_info,
        )
    }


def __gather_normal(blender_primitive, interleaving_info, export_settings):
    if not export_settings[gltf2_blender_export_keys.NORMALS]:
        return {}
    if 'NORMAL' not in blender_primitive["attributes"]:
        return {}
    normal = blender_primitive["attributes"]['NORMAL']

    if interleaving_info:
        interleaving_info["names"].append("NORMAL")

    return {
        "NORMAL": array_to_accessor(
            normal,
            component_type=gltf2_io_constants.ComponentType.Float,
            data_type=gltf2_io_constants.DataType.Vec3,
            interleaving_info=interleaving_info,
        )
    }


def __gather_tangent(blender_primitive, interleaving_info, export_settings):
    if not export_settings[gltf2_blender_export_keys.TANGENTS]:
        return {}
    if 'TANGENT' not in blender_primitive["attributes"]:
        return {}
    tangent = blender_primitive["attributes"]['TANGENT']

    if interleaving_info:
        interleaving_info["names"].append("TANGENT")

    return {
        "TANGENT": array_to_accessor(
            tangent,
            component_type=gltf2_io_constants.ComponentType.Float,
            data_type=gltf2_io_constants.DataType.Vec4,
            interleaving_info=interleaving_info,
        )
    }


def __gather_texcoord(blender_primitive, interleaving_info, export_settings):
    attributes = {}
    if export_settings[gltf2_blender_export_keys.TEX_COORDS]:
        tex_coord_index = 0
        tex_coord_id = 'TEXCOORD_' + str(tex_coord_index)
        while blender_primitive["attributes"].get(tex_coord_id) is not None:
            tex_coord = blender_primitive["attributes"][tex_coord_id]

            if interleaving_info:
                interleaving_info["names"].append(tex_coord_id)

            attributes[tex_coord_id] = array_to_accessor(
                tex_coord,
                component_type=gltf2_io_constants.ComponentType.Float,
                data_type=gltf2_io_constants.DataType.Vec2,
                interleaving_info=interleaving_info,
            )
            tex_coord_index += 1
            tex_coord_id = 'TEXCOORD_' + str(tex_coord_index)
    return attributes


def __gather_colors(blender_primitive, interleaving_info, export_settings):
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

            if interleaving_info:
                interleaving_info["names"].append(color_id)

            attributes[color_id] = array_to_accessor(
                colors,
                gltf2_io_constants.ComponentType.UnsignedShort,
                gltf2_io_constants.DataType.Vec4,
                interleaving_info=interleaving_info,
            )

            color_index += 1
            color_id = 'COLOR_' + str(color_index)
    return attributes


def __gather_skins(blender_primitive, interleaving_info, export_settings):
    attributes = {}
    if export_settings[gltf2_blender_export_keys.SKINS]:
        bone_set_index = 0
        joint_id = 'JOINTS_' + str(bone_set_index)
        weight_id = 'WEIGHTS_' + str(bone_set_index)
        while blender_primitive["attributes"].get(joint_id) and blender_primitive["attributes"].get(weight_id):
            if bone_set_index >= 1:
                if not export_settings['gltf_all_vertex_influences']:
                    gltf2_io_debug.print_console("WARNING", "There are more than 4 joint vertex influences."
                                                            "The 4 with highest weight will be used (and normalized).")
                    break
                

            # joints
            if interleaving_info:
                interleaving_info["names"].append(joint_id)

            internal_joint = blender_primitive["attributes"][joint_id]
            component_type = gltf2_io_constants.ComponentType.UnsignedShort
            if max(internal_joint) < 256:
                component_type = gltf2_io_constants.ComponentType.UnsignedByte
            joint = array_to_accessor(
                internal_joint,
                component_type,
                data_type=gltf2_io_constants.DataType.Vec4,
                interleaving_info=interleaving_info,
            )
            attributes[joint_id] = joint

            # weights
            if interleaving_info:
                interleaving_info["names"].append(weight_id)

            internal_weight = blender_primitive["attributes"][weight_id]
            # normalize first 4 weights, when not exporting all influences
            if not export_settings['gltf_all_vertex_influences']:
                for idx in range(0, len(internal_weight), 4):
                    weight_slice = internal_weight[idx:idx + 4]
                    total = sum(weight_slice)
                    if total > 0:
                        factor = 1.0 / total
                        internal_weight[idx:idx + 4] = [w * factor for w in weight_slice]

            weight = array_to_accessor(
                internal_weight,
                component_type=gltf2_io_constants.ComponentType.Float,
                data_type=gltf2_io_constants.DataType.Vec4,
                interleaving_info=interleaving_info,
            )
            attributes[weight_id] = weight

            bone_set_index += 1
            joint_id = 'JOINTS_' + str(bone_set_index)
            weight_id = 'WEIGHTS_' + str(bone_set_index)
    return attributes


def __interleave_data(attributes, interleaving_info):
    
    # Compute the view byte_stride
    view_stride = 0
    for name in interleaving_info["names"]:
        attr = attributes[name]
        attr.byte_offset = view_stride
        view_stride += gltf2_io_constants.ComponentType.get_size(attr.component_type) * gltf2_io_constants.DataType.num_elements(attr.type)

    # Build the view bytearray
    view_bytearray = bytearray()
    for idx in range(0, attributes["POSITION"].count):
        for data in interleaving_info["data"]:
            view_bytearray.extend(data[idx].tobytes())

    # Store the view
    view = gltf2_io_binary_data.BinaryData(bytes(view_bytearray), view_stride)
    for name in interleaving_info["names"]:
        attributes[name].buffer_view = view
