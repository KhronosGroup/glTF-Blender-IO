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

from ctypes import *
from pathlib import Path

from io_scene_gltf2.io.exp.gltf2_io_binary_data import BinaryData
from ...io.com.gltf2_io_debug import print_console
from io_scene_gltf2.io.com.gltf2_io_draco_compression_extension import dll_path


def encode_scene_primitives(scenes, export_settings):
    """
    Handles draco compression.
    Moves position, normal and texture coordinate attributes into a Draco encoded buffer.
    """

    # Load DLL and setup function signatures.
    dll = cdll.LoadLibrary(str(dll_path().resolve()))

    dll.encoderCreate.restype = c_void_p
    dll.encoderCreate.argtypes = [c_uint32]

    dll.encoderRelease.restype = None
    dll.encoderRelease.argtypes = [c_void_p]

    dll.encoderSetCompressionLevel.restype = None
    dll.encoderSetCompressionLevel.argtypes = [c_void_p, c_uint32]

    dll.encoderSetQuantizationBits.restype = None
    dll.encoderSetQuantizationBits.argtypes = [c_void_p, c_uint32, c_uint32, c_uint32, c_uint32, c_uint32]
    
    dll.encoderSetIndices.restype = None
    dll.encoderSetIndices.argtypes = [c_void_p, c_size_t, c_uint32, c_void_p]

    dll.encoderSetAttribute.restype = c_uint32
    dll.encoderSetAttribute.argtypes = [c_void_p, c_char_p, c_size_t, c_char_p, c_void_p]

    dll.encoderEncode.restype = c_bool
    dll.encoderEncode.argtypes = [c_void_p, c_uint8]

    dll.encoderGetByteLength.restype = c_uint64
    dll.encoderGetByteLength.argtypes = [c_void_p]

    dll.encoderCopy.restype = None
    dll.encoderCopy.argtypes = [c_void_p, c_void_p]

    for scene in scenes:
        for node in scene.nodes:
            __traverse_node(node, lambda node: __encode_node(node, dll, export_settings))


def __traverse_node(node, f):
    f(node)
    if not (node.children is None):
        for child in node.children:
            __traverse_node(child, f)


def __encode_node(node, dll, export_settings):
    if not (node.mesh is None):
        print_console('INFO', 'Draco encoder: Encoding mesh {}.'.format(node.name))
        for primitive in node.mesh.primitives:
            __encode_primitive(primitive, dll, export_settings)


def __encode_primitive(primitive, dll, export_settings):
    attributes = primitive.attributes
    indices = primitive.indices

    if 'POSITION' not in attributes:
        print_console('WARNING', 'Draco encoder: Primitive without positions encountered. Skipping.')
        return

    positions = attributes['POSITION']

    # Skip nodes without a position buffer, e.g. a primitive from a Blender shared instance.
    if attributes['POSITION'].buffer_view is None:
        return

    encoder = dll.encoderCreate(positions.count)

    draco_ids = {}
    for attr_name in attributes:
        attr = attributes[attr_name]
        draco_id = dll.encoderSetAttribute(encoder, attr_name.encode(), attr.component_type, attr.type.encode(), attr.buffer_view.data)
        draco_ids[attr_name] = draco_id
        attr.buffer_view = None

    dll.encoderSetIndices(encoder, indices.component_type, indices.count, indices.buffer_view.data)
    indices.buffer_view = None

    dll.encoderSetCompressionLevel(encoder, export_settings['gltf_draco_mesh_compression_level'])
    dll.encoderSetQuantizationBits(encoder,
        export_settings['gltf_draco_position_quantization'],
        export_settings['gltf_draco_normal_quantization'],
        export_settings['gltf_draco_texcoord_quantization'],
        export_settings['gltf_draco_color_quantization'],
        export_settings['gltf_draco_generic_quantization'])
    
    if not dll.encoderEncode(encoder, primitive.targets is not None and len(primitive.targets) > 0):
        print_console('ERROR', 'Could not encode primitive. Skipping primitive.')

    byte_length = dll.encoderGetByteLength(encoder)
    encoded_data = bytes(byte_length)
    dll.encoderCopy(encoder, encoded_data)

    if primitive.extensions is None:
        primitive.extensions = {}
    
    primitive.extensions['KHR_draco_mesh_compression'] = {
        'bufferView': BinaryData(encoded_data),
        'attributes': draco_ids
    }

    # Set to triangle list mode.
    primitive.mode = 4

    dll.encoderRelease(encoder)
