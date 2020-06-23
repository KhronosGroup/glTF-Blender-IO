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
    lib_name = 'extern_draco'
    blender_root = Path(bpy.app.binary_path).parent
    python_lib = Path("{v[0]}.{v[1]}/python/lib".format(v=bpy.app.version))
    python_version = "python{v[0]}.{v[1]}".format(v=sys.version_info)
    paths = {
        'win32': blender_root/python_lib/'site-packages'/'{}.dll'.format(lib_name),
        'linux': blender_root/python_lib/python_version/'site-packages'/'lib{}.so'.format(lib_name),
        'darwin': blender_root.parent/'Resources'/python_lib/python_version/'site-packages'/'lib{}.dylib'.format(lib_name)
    }

    path = paths.get(sys.platform)
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


def compress_scene_primitives(scenes, export_settings):
    """
    Handles draco compression.
    Invoked after data has been gathered, but before scenes get traversed.
    Moves position, normal and texture coordinate attributes into a Draco compressed buffer.
    """

    # Load DLL and setup function signatures.
    # Nearly all functions take the compressor as the first argument.
    dll = cdll.LoadLibrary(str(dll_path().resolve()))

    # Initialization:

    dll.create_compressor.restype = c_void_p
    dll.create_compressor.argtypes = []

    dll.destroy_compressor.restype = None
    dll.destroy_compressor.argtypes = [c_void_p]

    # Configuration:

    dll.set_compression_level.restype = None
    dll.set_compression_level.argtypes = [c_void_p, c_uint32]

    dll.set_position_quantization.restype = None
    dll.set_position_quantization.argtypes = [c_void_p, c_uint32]

    dll.set_normal_quantization.restype = None
    dll.set_normal_quantization.argtypes = [c_void_p, c_uint32]

    dll.set_uv_quantization.restype = None
    dll.set_uv_quantization.argtypes = [c_void_p, c_uint32]

    dll.set_generic_quantization.restype = None
    dll.set_generic_quantization.argtypes = [c_void_p, c_uint32]

    # Data transfer:

    dll.set_faces.restype = None
    dll.set_faces.argtypes = [
        c_void_p, # Compressor
        c_uint32, # Index count
        c_uint32, # Index byte length
        c_char_p  # Indices
    ]

    add_attribute_fn_restype = c_uint32 # Draco id
    add_attribute_fn_argtypes = [
        c_void_p, # Compressor
        c_uint32, # Attribute count
        c_char_p  # Values
    ]

    dll.add_positions_f32.restype = add_attribute_fn_restype
    dll.add_positions_f32.argtypes = add_attribute_fn_argtypes

    dll.add_normals_f32.restype = add_attribute_fn_restype
    dll.add_normals_f32.argtypes = add_attribute_fn_argtypes

    dll.add_uvs_f32.restype = add_attribute_fn_restype
    dll.add_uvs_f32.argtypes = add_attribute_fn_argtypes

    dll.add_weights_f32.restype = add_attribute_fn_restype
    dll.add_weights_f32.argtypes = add_attribute_fn_argtypes

    dll.add_joints_u16.restype = add_attribute_fn_restype
    dll.add_joints_u16.argtypes = add_attribute_fn_argtypes

    # Compression:

    dll.compress.restype = c_bool
    dll.compress.argtypes = [
        c_void_p # Compressor
    ]

    dll.compress_morphed.restype = c_bool
    dll.compress_morphed.argtypes = [
        c_void_p # Compressor
    ]

    dll.get_compressed_size.restype = c_uint64
    dll.get_compressed_size.argtypes = [
        c_void_p # Compressor
    ]

    dll.copy_to_bytes.restype = None
    dll.copy_to_bytes.argtypes = [
        c_void_p, # Compressor
        c_char_p  # Destination pointer
    ]

    # Traverse nodes.
    for scene in scenes:
        for node in scene.nodes:
            __traverse_node(node, lambda node: __compress_node(node, dll, export_settings))

    # Cleanup memory.
    # May be shared amongst nodes because of non-unique primitive parents, so memory
    # release happens delayed.
    for scene in scenes:
        for node in scene.nodes:
            __traverse_node(node, __dispose_memory)

def __dispose_memory(node):
    """Remove buffers from attribute, since the data now resides inside the compressed Draco buffer."""
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

def __compress_node(node, dll, export_settings):
    """Compress a single node."""
    if not (node.mesh is None):
        print_console('INFO', 'Draco exporter: Compressing mesh "%s".' % node.name)
        for primitive in node.mesh.primitives:
            __compress_primitive(primitive, dll, export_settings)

def __traverse_node(node, f):
    """Calls f for each node and all child nodes, recursively."""
    f(node)
    if not (node.children is None):
        for child in node.children:
            __traverse_node(child, f)


def __compress_primitive(primitive, dll, export_settings):

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
        print_console('WARNING', 'Draco exporter: Primitive without positions encountered. Skipping.')
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

    print_console('INFO', 'Draco exporter: %s normals, %d uvs, %d weights, %d joints' %
        ('without' if normals is None else 'with', len(uvs), len(weights), len(joints)))

    # Begin mesh.
    compressor = dll.create_compressor()

    # Each attribute must have the same count of elements.
    count = positions.count

    # Add attributes to mesh compressor, remembering each attribute's Draco id.

    position_id = dll.add_positions_f32(compressor, count, positions.buffer_view.data)

    normal_id = None
    if normals is not None:
        if normals.count != count:
            print_console('INFO', 'Draco exporter: Mismatching normal count. Skipping.')
            dll.disposeCompressor(compressor)
            return
        normal_id = dll.add_normals_f32(compressor, normals.count, normals.buffer_view.data)

    uv_ids = []
    for uv in uvs:
        if uv.count != count:
            print_console('INFO', 'Draco exporter: Mismatching uv count. Skipping.')
            dll.disposeCompressor(compressor)
            return
        uv_ids.append(dll.add_uvs_f32(compressor, uv.count, uv.buffer_view.data))

    weight_ids = []
    for weight in weights:
        if weight.count != count:
            print_console('INFO', 'Draco exporter: Mismatching weight count. Skipping.')
            dll.disposeCompressor(compressor)
            return
        weight_ids.append(dll.add_weights_f32(compressor, weight.count, weight.buffer_view.data))

    joint_ids = []
    for joint in joints:
        if joint.count != count:
            print_console('INFO', 'Draco exporter: Mismatching joint count. Skipping.')
            dll.disposeCompressor(compressor)
            return
        joint_ids.append(dll.add_joints_u16(compressor, joint.count, joint.buffer_view.data))

    # Add face indices to mesh compressor.
    dll.set_faces(compressor, indices.count, component_type_byte_length[indices.component_type.name], indices.buffer_view.data)

    # Set compression parameters.
    dll.set_compression_level(compressor, export_settings['gltf_draco_mesh_compression_level'])
    dll.set_position_quantization(compressor, export_settings['gltf_draco_position_quantization'])
    dll.set_normal_quantization(compressor, export_settings['gltf_draco_normal_quantization'])
    dll.set_uv_quantization(compressor, export_settings['gltf_draco_texcoord_quantization'])
    dll.set_generic_quantization(compressor, export_settings['gltf_draco_generic_quantization'])

    compress_fn = dll.compress if not primitive.targets else dll.compress_morphed

    # After all point and connectivity data has been written to the compressor,
    # it can finally be compressed.
    if dll.compress(compressor):

        # Compression was successful.
        # Move compressed data into a bytes object,
        # which is referenced by a 'gltf2_io_binary_data.BinaryData':
        #
        # "KHR_draco_mesh_compression": {
        #     ....
        #     "buffer_view": Compressed data inside a 'gltf2_io_binary_data.BinaryData'.
        # }

        # Query size necessary to hold all the compressed data.
        compression_size = dll.get_compressed_size(compressor)

        # Allocate byte buffer and write compressed data to it.
        compressed_data = bytes(compression_size)
        dll.copy_to_bytes(compressor, compressed_data)

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

    # Afterwards, the compressor can be released.
    dll.destroy_compressor(compressor)

    return
