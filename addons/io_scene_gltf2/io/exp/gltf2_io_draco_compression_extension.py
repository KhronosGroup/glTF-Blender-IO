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
    Invoked after data has been gathered, but before scenes get traversed.
    Moves position, normal and texture coordinate attributes into a Draco encoded buffer.
    """

    # Load DLL and setup function signatures.
    dll = cdll.LoadLibrary(str(dll_path().resolve()))

    dll.encoderCreate.restype = c_void_p
    dll.encoderCreate.argtypes = []

    dll.encoderRelease.restype = None
    dll.encoderRelease.argtypes = [c_void_p]

    dll.encoderSetCompressionLevel.restype = None
    dll.encoderSetCompressionLevel.argtypes = [c_void_p, c_uint32]

    dll.encoderSetQuantizationBits.restype = None
    dll.encoderSetQuantizationBits.argtypes = [c_void_p, c_uint32, c_uint32, c_uint32, c_uint32]

    dll.encoderSetFaces.restype = None
    dll.encoderSetFaces.argtypes = [c_void_p, c_uint32, c_uint32, c_void_p]

    add_attribute_fn_restype = c_uint32
    add_attribute_fn_argtypes = [c_void_p, c_uint32, c_void_p]

    dll.encoderAddPositions.restype = add_attribute_fn_restype
    dll.encoderAddPositions.argtypes = add_attribute_fn_argtypes

    dll.encoderAddNormals.restype = add_attribute_fn_restype
    dll.encoderAddNormals.argtypes = add_attribute_fn_argtypes

    dll.encoderAddUVs.restype = add_attribute_fn_restype
    dll.encoderAddUVs.argtypes = add_attribute_fn_argtypes

    dll.encoderAddWeights.restype = add_attribute_fn_restype
    dll.encoderAddWeights.argtypes = add_attribute_fn_argtypes

    dll.encoderAddJoints.restype = add_attribute_fn_restype
    dll.encoderAddJoints.argtypes = add_attribute_fn_argtypes

    dll.encoderEncode.restype = c_bool
    dll.encoderEncode.argtypes = [c_void_p, c_uint8]

    dll.encoderGetByteLength.restype = c_uint64
    dll.encoderGetByteLength.argtypes = [c_void_p]

    dll.encoderCopy.restype = None
    dll.encoderCopy.argtypes = [c_void_p, c_void_p]

    for scene in scenes:
        for node in scene.nodes:
            __traverse_node(node, lambda node: __encode_node(node, dll, export_settings))

    # Memory might be shared amongst nodes because of non-unique primitive parents, so release happens delayed.
    for scene in scenes:
        for node in scene.nodes:
            __traverse_node(node, __dispose_memory)

def __dispose_memory(node):
    """Remove buffers from attribute, since the data now resides inside the encoded Draco buffer."""
    if not (node.mesh is None):
        for primitive in node.mesh.primitives:
            primitive.indices.buffer_view = None
            attributes = primitive.attributes
            if 'NORMAL' in attributes:
                attributes['NORMAL'].buffer_view = None
            for attribute in [attributes[attr] for attr in attributes if attr.startswith('TEXCOORD_')]:
                attribute.buffer_view = None

def __encode_node(node, dll, export_settings):
    """Encodes a single node."""
    if not (node.mesh is None):
        print_console('INFO', 'Draco encoder: Encoding mesh {}.'.format(node.name))
        for primitive in node.mesh.primitives:
            __encode_primitive(primitive, dll, export_settings)

def __traverse_node(node, f):
    """Calls `f` for each node and all child nodes, recursively."""
    f(node)
    if not (node.children is None):
        for child in node.children:
            __traverse_node(child, f)


def __encode_primitive(primitive, dll, export_settings):
    attributes = primitive.attributes
    indices = primitive.indices

    component_type_byte_length = {
        'Byte': 1,
        'UnsignedByte': 1,
        'Short': 2,
        'UnsignedShort': 2,
        'UnsignedInt': 4,
    }

    if 'POSITION' not in attributes:
        print_console('WARNING', 'Draco encoder: Primitive without positions encountered. Skipping.')
        return

    positions = attributes['POSITION']

    # Skip nodes without a position buffer, e.g. a primitive from a Blender shared instance.
    if attributes['POSITION'].buffer_view is None:
        return

    normals = attributes['NORMAL'] if 'NORMAL' in attributes else None
    uvs = [attributes[attr] for attr in attributes if attr.startswith('TEXCOORD_')]
    weights = [attributes[attr] for attr in attributes if attr.startswith('WEIGHTS_')]
    joints = [attributes[attr] for attr in attributes if attr.startswith('JOINTS_')]

    print_console('INFO', 'Draco encoder: {} normals, {} uvs, {} weights, {} joints'
        .format('without' if normals is None else 'with', len(uvs), len(weights), len(joints)))

    encoder = dll.encoderCreate()

    position_id = dll.encoderAddPositions(encoder, positions.count, positions.buffer_view.data)

    normal_id = None
    if normals is not None:
        if normals.count != positions.count:
            print_console('INFO', 'Draco encoder: Mismatching normal count. Skipping primitive.')
            dll.encoderRelease(encoder)
            return
        normal_id = dll.encoderAddNormals(encoder, normals.count, normals.buffer_view.data)

    uv_ids = []
    for uv in uvs:
        if uv.count != positions.count:
            print_console('INFO', 'Draco encoder: Mismatching uv count. Skipping primitive.')
            dll.encoderRelease(encoder)
            return
        uv_ids.append(dll.encoderAddUVs(encoder, uv.count, uv.buffer_view.data))

    weight_ids = []
    for weight in weights:
        if weight.count != positions.count:
            print_console('INFO', 'Draco encoder: Mismatching weight count. Skipping primitive.')
            dll.encoderRelease(encoder)
            return
        weight_ids.append(dll.encoderAddWeights(encoder, weight.count, weight.buffer_view.data))

    joint_ids = []
    for joint in joints:
        if joint.count != positions.count:
            print_console('INFO', 'Draco encoder: Mismatching joint count. Skipping primitive.')
            dll.encoderRelease(encoder)
            return
        joint_ids.append(dll.encoderAddJoints(encoder, joint.count, joint.buffer_view.data))

    dll.encoderSetFaces(encoder, indices.count, component_type_byte_length[indices.component_type.name], indices.buffer_view.data)

    dll.encoderSetCompressionLevel(encoder, export_settings['gltf_draco_mesh_compression_level'])
    dll.encoderSetQuantizationBits(encoder,
        export_settings['gltf_draco_position_quantization'],
        export_settings['gltf_draco_normal_quantization'],
        export_settings['gltf_draco_texcoord_quantization'],
        export_settings['gltf_draco_generic_quantization'])
    
    if dll.encoderEncode(encoder, primitive.targets is not None and len(primitive.targets) > 0):
        byte_length = dll.encoderGetByteLength(encoder)
        encoded_data = bytes(byte_length)
        dll.encoderCopy(encoder, encoded_data)

        extension = {
            'bufferView': BinaryData(encoded_data),
            'attributes': {
                'POSITION': position_id
            }
        }

        if normals is not None:
            extension['attributes']['NORMAL'] = normal_id

        for (k, id) in enumerate(uv_ids):
            extension['attributes']['TEXCOORD_' + str(k)] = id

        for (k, id) in enumerate(weight_ids):
            extension['attributes']['WEIGHTS_' + str(k)] = id

        for (k, id) in enumerate(joint_ids):
            extension['attributes']['JOINTS_' + str(k)] = id

        if primitive.extensions is None:
            primitive.extensions = {}
        
        primitive.extensions['KHR_draco_mesh_compression'] = extension

        # Remove buffer views from the accessors of the attributes which compressed.
        positions.buffer_view = None
        if normals is not None:
            normals.buffer_view = None
        for uv in uvs:
            uv.buffer_view = None
        for weight in weights:
            weight.buffer_view = None
        for joint in joints:
            joint.buffer_view = None

        # Set to triangle list mode.
        primitive.mode = 4

    dll.encoderRelease(encoder)
