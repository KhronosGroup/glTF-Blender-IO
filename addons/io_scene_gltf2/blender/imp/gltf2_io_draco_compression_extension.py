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

import bpy
import sys
from ctypes import *
from pathlib import Path
import struct

from io_scene_gltf2.io.imp.gltf2_io_binary import BinaryData
from ...io.com.gltf2_io_debug import print_console
from io_scene_gltf2.io.com.gltf2_io_draco_compression_extension import dll_path


def decode_primitive(gltf, prim):
    """
    Handles draco compression.
    Moves decoded data into new buffers and buffer views held by the accessors of the given primitive.
    """

    # Load DLL and setup function signatures.
    dll = cdll.LoadLibrary(str(dll_path().resolve()))

    dll.decoderCreate.restype = c_void_p
    dll.decoderCreate.argtypes = []

    dll.decoderRelease.restype = None
    dll.decoderRelease.argtypes = [c_void_p]

    dll.decoderDecode.restype = c_bool
    dll.decoderDecode.argtypes = [c_void_p, c_void_p, c_size_t]

    dll.decoderReadAttribute.restype = c_bool
    dll.decoderReadAttribute.argtypes = [c_void_p, c_uint32, c_size_t, c_char_p]

    dll.decoderAttributeIsNormalized.restype = c_bool
    dll.decoderAttributeIsNormalized.argtypes = [c_void_p, c_uint32]

    dll.decoderGetAttributeByteLength.restype = c_size_t
    dll.decoderGetAttributeByteLength.argtypes = [c_void_p, c_uint32]

    dll.decoderGetAttributeData.restype = c_void_p
    dll.decoderGetAttributeData.argtypes = [c_void_p, c_uint32]

    dll.decoderReadIndices.restype = c_bool
    dll.decoderReadIndices.argtypes = [c_void_p, c_size_t]

    dll.decoderGetIndicesByteLength.restype = c_size_t
    dll.decoderGetIndicesByteLength.argtypes = [c_void_p]

    dll.decoderGetIndicesData.restype = c_void_p
    dll.decoderGetIndicesData.argtypes = [c_void_p]
    
    decoder = dll.decoderCreate()
    extension = prim.extensions['KHR_draco_mesh_compression']

    # Create Draco decoder.
    draco_buffer = BinaryData.get_buffer_view(gltf, extension['bufferView'])
    if not dll.decoderDecode(decoder, draco_buffer.obj, draco_buffer.nbytes):
        print_console('ERROR', 'Draco Decoder: Could not decode primitive {}. Skipping primitive.'.format(prim.name))
    
    # Read each attribute.
    for attr in extension['attributes']:
        dracoId = extension['attributes'][attr]
        if attr not in prim.attributes:
            print_console('ERROR', 'Draco Decoder: Draco attribute {} not in primitive attributes'.format(attr))
            return
        
        accessor = gltf.data.accessors[prim.attributes[attr]]
        if not dll.decoderReadAttribute(decoder, dracoId, accessor.component_type, accessor.type.encode()):
            print_console('ERROR', 'Draco Decoder: Could not decode attribute {} of primitive {}. Skipping primitive.'.format(attr, prim.name))
        
        byte_length = dll.decoderGetAttributeByteLength(decoder, dracoId)
        data = dll.decoderGetAttributeData(decoder, dracoId)

        buffer_idx = 0

    dll.decoderRelease(decoder)
