# Copyright (c) 2017 The Khronos Group Inc.
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

#
# Imports
#

import struct

from ..common.gltf2_io_debug import *
from ..common.gltf2_io_constants import *

#
# Globals
#

#
# Functions
#
def create_asset(export_settings,
                glTF):
    """
    Generates the top level asset entry.
    """

    asset = {}

    #
    #

    asset['version'] = '2.0'

    #

    asset['generator'] = 'Khronos Blender glTF 2.0 exporter'

    #

    if export_settings['gltf_copyright'] != "":
        asset['copyright'] = export_settings['gltf_copyright']

    #
    #

    glTF['asset'] = asset

def create_extensionsUsed(export_settings,
                          glTF, extension):
    """
    Creates and assigns the 'extensionsUsed' property.
    """

    if glTF.get('extensionsUsed') is None:
        glTF['extensionsUsed'] = []

    extensionsUsed = glTF['extensionsUsed']

    if extension not in extensionsUsed:
        extensionsUsed.append(extension)


def create_extensionsRequired(export_settings,
                              glTF, extension):
    """
    Creates and assigns the 'extensionsRequired' property.
    """

    if glTF.get('extensionsRequired') is None:
        glTF['extensionsRequired'] = []

    extensionsRequired = glTF['extensionsRequired']

    if extension not in extensionsRequired:
        extensionsRequired.append(extension)


def create_sampler(export_settings,
                   glTF, magFilter, wrap):
    """
    Creates and appends a sampler with the given parameters.
    """

    if glTF.get('samplers') is None:
        glTF['samplers'] = []

    samplers = glTF['samplers']

    #

    if len(samplers) == 0:
        sampler = {}

        samplers.append(sampler)

    if magFilter == 9729 and wrap == 10497:
        return 0

    #

    index = 0

    for currentSampler in samplers:
        if currentSampler.get('magFilter') is None or currentSampler.get('wrapS'):
            index += 1
            continue

        if currentSampler['magFilter'] == filter and currentSampler['wrapS'] == wrap:
            return index

    #

    minFilter = 9986
    if magFilter == 9728:
        minFilter = 9984

    sampler = {
        'magFilter': magFilter,
        'minFilter': minFilter,
        'wrapS': wrap,
        'wrapT': wrap
    }

    samplers.append(sampler)

    return len(samplers) - 1


def create_bufferView(export_settings,
        glTF,
        data_buffer,
        target,
        alignment
):
    """
    Creates and appends a bufferView with the given parameters.
    :type target: str
    """

    if data_buffer is None:
        return -1

    gltf_target_number = [34962, 34963]
    gltf_target_enums = ["ARRAY_BUFFER", "ELEMENT_ARRAY_BUFFER"]

    target_number = 0
    if target in gltf_target_enums:
        target_number = gltf_target_number[gltf_target_enums.index(target)]

    #

    if glTF.get('bufferViews') is None:
        glTF['bufferViews'] = []

    bufferViews = glTF['bufferViews']

    #

    bufferView = {}

    if target_number != 0:
        bufferView['target'] = target_number

    bufferView['byteLength'] = len(data_buffer)

    binary = export_settings['gltf_binary']

    #

    binary_length = len(binary)

    remainder = 0

    if alignment > 0:
        remainder = binary_length % alignment

    if remainder > 0:
        padding_byte = struct.pack('<1b', 0)
        for i in range(0, alignment - remainder):
            binary.extend(padding_byte)

    #

    bufferView['byteOffset'] = len(binary)
    binary.extend(data_buffer)

    # Only have one buffer. 
    bufferView['buffer'] = 0

    #

    bufferViews.append(bufferView)

    return len(bufferViews) - 1


def create_accessor(export_settings,
        glTF,
        data,
        componentType,
        count,
        type,
        target
):
    """
    Creates and appends an accessor with the given parameters.
    :type type: str
    :type componentType: str
    """

    if data is None:
        print_console('ERROR', 'No data')
        return -1

    gltf_convert_type = ["b", "B", "h", "H", "I", "f"]

    gltf_enum_names = [
        GLTF_COMPONENT_TYPE_BYTE,
        GLTF_COMPONENT_TYPE_UNSIGNED_BYTE,
        GLTF_COMPONENT_TYPE_SHORT,
        GLTF_COMPONENT_TYPE_UNSIGNED_SHORT,
        GLTF_COMPONENT_TYPE_UNSIGNED_INT,
        GLTF_COMPONENT_TYPE_FLOAT
    ]

    gltf_convert_type_size = [1, 1, 2, 2, 4, 4]

    if componentType not in gltf_enum_names:
        print_console('ERROR', 'Invalid componentType ' + componentType)
        return -1

    component_type_integer = [5120, 5121, 5122, 5123, 5125, 5126][gltf_enum_names.index(componentType)]

    convert_type = gltf_convert_type[gltf_enum_names.index(componentType)]
    convert_type_size = gltf_convert_type_size[gltf_enum_names.index(componentType)]

    if count < 1:
        print_console('ERROR', 'Invalid count ' + str(count))
        return -1

    gltf_type_count = [1, 2, 3, 4, 4, 9, 16]
    gltf_type = [
        GLTF_DATA_TYPE_SCALAR,
        GLTF_DATA_TYPE_VEC2,
        GLTF_DATA_TYPE_VEC3,
        GLTF_DATA_TYPE_VEC4,
        GLTF_DATA_TYPE_MAT2,
        GLTF_DATA_TYPE_MAT3,
        GLTF_DATA_TYPE_MAT4
    ]

    if type not in gltf_type:
        print_console('ERROR', 'Invalid tyoe ' + type)
        return -1

    type_count = gltf_type_count[gltf_type.index(type)]

    #

    if glTF.get('accessors') is None:
        glTF['accessors'] = []

    accessors = glTF['accessors']

    #

    accessor = {
        'componentType': component_type_integer,
        'count': count,
        'type': type
    }

    #

    minimum = []
    maximum = []

    for component in range(0, count):
        for component_index in range(0, type_count):
            element = data[component * type_count + component_index]

            if component == 0:
                minimum.append(element)
                maximum.append(element)
            else:
                minimum[component_index] = min(minimum[component_index], element)
                maximum[component_index] = max(maximum[component_index], element)

    accessor['min'] = minimum
    accessor['max'] = maximum

    #

    convert_type = '<' + str(count * type_count) + convert_type

    data_buffer = struct.pack(convert_type, *data)

    buffer_view = create_bufferView(export_settings, glTF, data_buffer, target, convert_type_size)

    if buffer_view < 0:
        print_console('ERROR', 'Invalid buffer view')
        return -1

    accessor['bufferView'] = buffer_view

    #

    accessors.append(accessor)

    return len(accessors) - 1
