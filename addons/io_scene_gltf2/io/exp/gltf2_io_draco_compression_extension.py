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
from ctypes import c_void_p, c_uint32, c_uint64, c_bool, c_char_p, cdll
from pathlib import Path
import struct

from io_scene_gltf2.io.exp.gltf2_io_binary_data import BinaryData
from ...io.com.gltf2_io_debug import print_console


def dll_path() -> Path:
    """
    Get the DLL path depending on the underlying platform.
    :return: DLL path.
    """
    # lib_name = 'extern_draco'
    # blender_root = Path(bpy.app.binary_path).parent
    # python_lib = Path("{v[0]}.{v[1]}/python/lib".format(v=bpy.app.version))
    # python_version = "python{v[0]}.{v[1]}".format(v=sys.version_info)
    # paths = {
    #     'win32': blender_root/python_lib/'site-packages'/'{}.dll'.format(lib_name),
    #     'linux': blender_root/python_lib/python_version/'site-packages'/'lib{}.so'.format(lib_name),
    #     'darwin': blender_root.parent/'Resources'/python_lib/python_version/'site-packages'/'lib{}.dylib'.format(lib_name)
    # }

    # path = paths.get(sys.platform)
    path = Path('/Users/work/ux3d/draco_blender/build-xcode/bin/2.80/python/lib/python3.7/Debug/libglTFBlenderIO-Draco.dylib')
    return path if path is not None else ''


def dll_exists(quiet=False) -> bool:
    """
    Checks whether the DLL path exists.
    :return: True if the DLL exists.
    """
    exists = dll_path().exists()
    if quiet is False:
        print("'{}' ".format(dll_path().absolute()) + ("exists, draco mesh compression is available" if exists else
                                                       "does not exist, draco mesh compression not available"))
    return exists


def encode_scene_primitives(scenes, export_settings):
    """
    Handles draco compression.
    Invoked after data has been gathered, but before scenes get traversed.
    Moves position, normal and texture coordinate attributes into a Draco encoded buffer.
    """

    # Load DLL and setup function signatures.
    # Nearly all functions take the encoder as the first argument.
    dll = cdll.LoadLibrary(str(dll_path().resolve()))

    # Initialization:

    dll.encoderCreate.restype = c_void_p
    dll.encoderCreate.argtypes = []

    dll.encoderRelease.restype = None
    dll.encoderRelease.argtypes = [c_void_p]

    # Configuration:

    dll.encoderSetCompressionLevel.restype = None
    dll.encoderSetCompressionLevel.argtypes = [c_void_p, c_uint32]

    dll.encoderSetQuantizationBits.restype = None
    dll.encoderSetQuantizationBits.argtypes = [c_void_p, c_uint32, c_uint32, c_uint32, c_uint32]

    # Data transfer:

    dll.encoderSetFaces.restype = None
    dll.encoderSetFaces.argtypes = [
        c_void_p, # Encoder
        c_uint32, # Index count
        c_uint32, # Index byte length
        c_char_p  # Indices
    ]

    add_attribute_fn_restype = c_uint32 # Draco id
    add_attribute_fn_argtypes = [
        c_void_p, # Encoder
        c_uint32, # Attribute count
        c_char_p  # Values
    ]

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

    # Encoding:

    dll.encoderEncode.restype = c_bool
    dll.encoderEncode.argtypes = [c_void_p]

    dll.encoderEncodeMorphed.restype = c_bool
    dll.encoderEncodeMorphed.argtypes = [c_void_p]

    dll.encoderGetByteLength.restype = c_uint64
    dll.encoderGetByteLength.argtypes = [c_void_p]

    dll.encoderCopy.restype = None
    dll.encoderCopy.argtypes = [c_void_p, c_char_p]

    # Traverse nodes.
    for scene in scenes:
        for node in scene.nodes:
            __traverse_node(node, lambda node: __encode_node(node, dll, export_settings))

    # Cleanup memory.
    # May be shared amongst nodes because of non-unique primitive parents, so memory
    # release happens delayed.
    for scene in scenes:
        for node in scene.nodes:
            __traverse_node(node, __dispose_memory)

def __dispose_memory(node):
    """Remove buffers from attribute, since the data now resides inside the encoded Draco buffer."""
    if not (node.mesh is None):
        for primitive in node.mesh.primitives:

            # Drop indices.
            primitive.indices.buffer_view = None

            # Drop attributes.
            attributes = primitive.attributes
            if 'NORMAL' in attributes:
                attributes['NORMAL'].buffer_view = None
            for attribute in [attributes[attr] for attr in attributes if attr.startswith('TEXCOORD_')]:
                attribute.buffer_view = None

def __encode_node(node, dll, export_settings):
    """Encodes a single node."""
    if not (node.mesh is None):
        print_console('INFO', 'Draco encoder: Encoding mesh "%s".' % node.name)
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

    # Maps component types to their byte length.
    component_type_byte_length = {
        'Byte': 1,
        'UnsignedByte': 1,
        'Short': 2,
        'UnsignedShort': 2,
        'UnsignedInt': 4,
    }

    # Positions are the only attribute type required to be present.
    if 'POSITION' not in attributes:
        print_console('WARNING', 'Draco encoder: Primitive without positions encountered. Skipping.')
        return

    positions = attributes['POSITION']

    # Skip nodes without a position buffer.
    # This happens with Blender instances, i.e. multiple nodes sharing the same mesh.
    if attributes['POSITION'].buffer_view is None:
        return

    normals = attributes['NORMAL'] if 'NORMAL' in attributes else None
    uvs = [attributes[attr] for attr in attributes if attr.startswith('TEXCOORD_')]
    weights = [attributes[attr] for attr in attributes if attr.startswith('WEIGHTS_')]
    joints = [attributes[attr] for attr in attributes if attr.startswith('JOINTS_')]

    print_console('INFO', 'Draco encoder: %s normals, %d uvs, %d weights, %d joints' %
        ('without' if normals is None else 'with', len(uvs), len(weights), len(joints)))

    # Begin mesh.
    encoder = dll.encoderCreate()

    # Each attribute must have the same count of elements.
    count = positions.count

    # Add attributes to mesh encoder, remembering each attribute's Draco id.

    position_id = dll.encoderAddPositions(encoder, count, positions.buffer_view.data)

    normal_id = None
    if normals is not None:
        if normals.count != count:
            print_console('INFO', 'Draco encoder: Mismatching normal count. Skipping.')
            dll.encoderRelease(encoder)
            return
        normal_id = dll.encoderAddNormals(encoder, normals.count, normals.buffer_view.data)

    uv_ids = []
    for uv in uvs:
        if uv.count != count:
            print_console('INFO', 'Draco encoder: Mismatching uv count. Skipping.')
            dll.encoderRelease(encoder)
            return
        uv_ids.append(dll.encoderAddUVs(encoder, uv.count, uv.buffer_view.data))

    weight_ids = []
    for weight in weights:
        if weight.count != count:
            print_console('INFO', 'Draco encoder: Mismatching weight count. Skipping.')
            dll.encoderRelease(encoder)
            return
        weight_ids.append(dll.encoderAddWeights(encoder, weight.count, weight.buffer_view.data))

    joint_ids = []
    for joint in joints:
        if joint.count != count:
            print_console('INFO', 'Draco encoder: Mismatching joint count. Skipping.')
            dll.encoderRelease(encoder)
            return
        joint_ids.append(dll.encoderAddJoints(encoder, joint.count, joint.buffer_view.data))

    # Add face indices to mesh encoder.
    dll.encoderSetFaces(encoder, indices.count, component_type_byte_length[indices.component_type.name], indices.buffer_view.data)

    # Set compression parameters.
    dll.encoderSetCompressionLevel(encoder, export_settings['gltf_draco_mesh_compression_level'])
    dll.encoderSetQuantizationBits(encoder,
        export_settings['gltf_draco_position_quantization'],
        export_settings['gltf_draco_normal_quantization'],
        export_settings['gltf_draco_texcoord_quantization'],
        export_settings['gltf_draco_generic_quantization'])
    
    encodeFunction = dll.encoderEncode if not primitive.targets else dll.encoderEncodeMorphed

    # After all point and connectivity data has been written to the encoder, it can finally be encoded.
    if encodeFunction(encoder):

        # Encoding was successful.
        # Move compressed data into a bytes object,
        # which is referenced by a 'gltf2_io_binary_data.BinaryData':
        #
        # "KHR_draco_mesh_compression": {
        #     ....
        #     "buffer_view": Compressed data inside a 'gltf2_io_binary_data.BinaryData'.
        # }

        # Query size necessary to hold all the compressed data.
        compression_size = dll.encoderGetByteLength(encoder)

        # Allocate byte buffer and write compressed data to it.
        compressed_data = bytes(compression_size)
        dll.encoderCopy(encoder, compressed_data)

        if primitive.extensions is None:
            primitive.extensions = {}

        # Write Draco extension into primitive, including attribute ids:

        extension = {
            'bufferView': BinaryData(compressed_data),
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

        primitive.extensions['KHR_draco_mesh_compression'] = extension

        # Remove buffer views from the accessors of the attributes which compressed:

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

    # Afterwards, the encoder can be released.
    dll.encoderRelease(encoder)

    return
