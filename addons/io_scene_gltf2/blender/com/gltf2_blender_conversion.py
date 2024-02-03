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

from math import sin, cos
import numpy as np
from ...io.com import gltf2_io_constants

PBR_WATTS_TO_LUMENS = 683
# Industry convention, biological peak at 555nm, scientific standard as part of SI candela definition.

def texture_transform_blender_to_gltf(mapping_transform):
    """
    Converts the offset/rotation/scale from a Mapping node applied in Blender's
    UV space to the equivalent KHR_texture_transform.
    """
    offset = mapping_transform.get('offset', [0, 0])
    rotation = mapping_transform.get('rotation', 0)
    scale = mapping_transform.get('scale', [1, 1])
    return {
        'offset': [
            offset[0] - scale[1] * sin(rotation),
            1 - offset[1] - scale[1] * cos(rotation),
        ],
        'rotation': rotation,
        'scale': [scale[0], scale[1]],
    }

def texture_transform_gltf_to_blender(texture_transform):
    """
    Converts a KHR_texture_transform into the equivalent offset/rotation/scale
    for a Mapping node applied in Blender's UV space.
    """
    offset = texture_transform.get('offset', [0, 0])
    rotation = texture_transform.get('rotation', 0)
    scale = texture_transform.get('scale', [1, 1])
    return {
        'offset': [
            offset[0] + scale[1] * sin(rotation),
            1 - offset[1] - scale[1] * cos(rotation),
        ],
        'rotation': rotation,
        'scale': [scale[0], scale[1]],
    }

def get_target(property):
    return {
        "delta_location": "translation",
        "delta_rotation_euler": "rotation",
        "delta_rotation_quaternion": "rotation",
        "delta_scale": "scale",
        "location": "translation",
        "rotation_axis_angle": "rotation",
        "rotation_euler": "rotation",
        "rotation_quaternion": "rotation",
        "scale": "scale",
        "value": "weights"
    }.get(property, None)

def get_component_type(attribute_component_type):
    return {
        "INT8": gltf2_io_constants.ComponentType.Float,
        "BYTE_COLOR": gltf2_io_constants.ComponentType.UnsignedShort,
        "FLOAT2": gltf2_io_constants.ComponentType.Float,
        "FLOAT_COLOR": gltf2_io_constants.ComponentType.Float,
        "FLOAT_VECTOR": gltf2_io_constants.ComponentType.Float,
        "FLOAT_VECTOR_4": gltf2_io_constants.ComponentType.Float,
        "INT": gltf2_io_constants.ComponentType.Float, # No signed Int in glTF accessor
        "FLOAT": gltf2_io_constants.ComponentType.Float,
        "BOOLEAN": gltf2_io_constants.ComponentType.Float
    }.get(attribute_component_type)

def get_channel_from_target(target):
    return {
        "rotation": "rotation_quaternion",
        "translation": "location",
        "scale": "scale"
    }.get(target)

def get_data_type(attribute_component_type):
    return {
        "INT8": gltf2_io_constants.DataType.Scalar,
        "BYTE_COLOR": gltf2_io_constants.DataType.Vec4,
        "FLOAT2": gltf2_io_constants.DataType.Vec2,
        "FLOAT_COLOR": gltf2_io_constants.DataType.Vec4,
        "FLOAT_VECTOR": gltf2_io_constants.DataType.Vec3,
        "FLOAT_VECTOR_4": gltf2_io_constants.DataType.Vec4,
        "INT": gltf2_io_constants.DataType.Scalar,
        "FLOAT": gltf2_io_constants.DataType.Scalar,
        "BOOLEAN": gltf2_io_constants.DataType.Scalar,
    }.get(attribute_component_type)

def get_data_length(attribute_component_type):
    return {
        "INT8": 1,
        "BYTE_COLOR": 4,
        "FLOAT2": 2,
        "FLOAT_COLOR": 4,
        "FLOAT_VECTOR": 3,
        "FLOAT_VECTOR_4": 4,
        "INT": 1,
        "FLOAT": 1,
        "BOOLEAN": 1
    }.get(attribute_component_type)

def get_numpy_type(attribute_component_type):
    return {
        "INT8": np.float32,
        "BYTE_COLOR": np.float32,
        "FLOAT2": np.float32,
        "FLOAT_COLOR": np.float32,
        "FLOAT_VECTOR": np.float32,
        "FLOAT_VECTOR_4": np.float32,
        "INT": np.float32, #signed integer are not supported by glTF
        "FLOAT": np.float32,
        "BOOLEAN": np.float32
    }.get(attribute_component_type)

def get_attribute_type(component_type, data_type):
    if gltf2_io_constants.DataType.num_elements(data_type) == 1:
        return {
            gltf2_io_constants.ComponentType.Float: "FLOAT",
            gltf2_io_constants.ComponentType.UnsignedByte: "INT" # What is the best for compatibility?
        }.get(component_type, None)
    elif gltf2_io_constants.DataType.num_elements(data_type) == 2:
        return {
            gltf2_io_constants.ComponentType.Float: "FLOAT2"
        }.get(component_type, None)
    elif gltf2_io_constants.DataType.num_elements(data_type) == 3:
        return {
            gltf2_io_constants.ComponentType.Float: "FLOAT_VECTOR"
        }.get(component_type, None)
    elif gltf2_io_constants.DataType.num_elements(data_type) == 4:
        return {
            gltf2_io_constants.ComponentType.Float: "FLOAT_COLOR",
            gltf2_io_constants.ComponentType.UnsignedShort: "BYTE_COLOR",
            gltf2_io_constants.ComponentType.UnsignedByte: "BYTE_COLOR" # What is the best for compatibility?
        }.get(component_type, None)
    else:
        pass

def get_gltf_interpolation(interpolation):
        return {
        "BEZIER": "CUBICSPLINE",
        "LINEAR": "LINEAR",
        "CONSTANT": "STEP"
    }.get(interpolation, "LINEAR")

def get_anisotropy_rotation_gltf_to_blender(rotation):
    # glTF rotation is in randian, Blender in 0 to 1
    return rotation / (2 * np.pi)

def get_anisotropy_rotation_blender_to_gltf(rotation):
    # glTF rotation is in randian, Blender in 0 to 1
    return rotation * (2 * np.pi)

def fast_structured_np_unique(arr, *args, **kwargs):
    """
    np.unique optimized for structured arrays when a sorted result is not required.

    np.unique works through sorting, but sorting a structured array requires as many sorts as there are fields in the
    structured dtype.

    By viewing the array as a single non-structured dtype that sorts according to its bytes, unique elements can be
    found with a single sort. Since the values are viewed as a different type to their original, this means that the
    returned array of unique values may not be sorted according to their original type.

    Float field caveats:
    All elements of -0.0 in the input array will be replaced with 0.0 to ensure that both values are collapsed into one.
    NaN values can have lots of different byte representations (e.g. signalling/quiet and custom payloads). Only the
    duplicates of each unique byte representation will be collapsed into one.

    Nested structured dtypes are not supported.
    The behaviour of structured dtypes with overlapping fields is undefined.
    """
    structured_dtype = arr.dtype
    fields = structured_dtype.fields
    if fields is None:
        raise RuntimeError('%s is not a structured dtype' % structured_dtype)

    for field_name, (field_dtype, *_offset_and_optional_title) in fields.items():
        if field_dtype.subdtype is not None:
            raise RuntimeError('Nested structured types are not supported in %s' % structured_dtype)
        if field_dtype.kind == 'f':
            # Replace all -0.0 in the array with 0.0 because -0.0 and 0.0 have different byte representations.
            arr[field_name][arr[field_name] == -0.0] = 0.0
        elif field_dtype.kind not in "iuUSV":
            # Signed integer, unsigned integer, unicode string, byte string (bytes) and raw bytes (void) can be left
            # as they are. Everything else is unsupported.
            raise RuntimeError('Unsupported structured field type %s for field %s' % (field_dtype, field_name))

    structured_itemsize = structured_dtype.itemsize

    # Integer types sort the fastest, but are only available for specific itemsizes.
    uint_dtypes_by_itemsize = {1: np.uint8, 2: np.uint16, 4: np.uint32, 8: np.uint64}
    # Signed/unsigned makes no noticeable speed difference, but using unsigned will result in ordering according to
    # individual bytes like the other, non-integer types.
    if structured_itemsize in uint_dtypes_by_itemsize:
        entire_structure_dtype = uint_dtypes_by_itemsize[structured_itemsize]
    else:
        # Construct a flexible size dtype with matching itemsize to the entire structured dtype.
        # Should always be 4 because each character in a unicode string is UCS4.
        str_itemsize = np.dtype((np.str_, 1)).itemsize
        if structured_itemsize % str_itemsize == 0:
            # Unicode strings seem to be slightly faster to sort than bytes.
            entire_structure_dtype = np.dtype((np.str_, structured_itemsize // str_itemsize))
        else:
            # Bytes seem to be slightly faster to sort than raw bytes (np.void).
            entire_structure_dtype = np.dtype((np.bytes_, structured_itemsize))

    result = np.unique(arr.view(entire_structure_dtype), *args, **kwargs)

    unique = result[0] if isinstance(result, tuple) else result
    # View in the original dtype.
    unique = unique.view(arr.dtype)
    if isinstance(result, tuple):
        return (unique,) + result[1:]
    else:
        return unique
