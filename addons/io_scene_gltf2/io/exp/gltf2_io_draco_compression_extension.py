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

from io_scene_gltf2.io.exp.gltf2_io_binary_data import BinaryData
from ...io.com.gltf2_io_debug import print_console


def dll_path() -> Path:
    """
    Get the DLL path depending on the underlying platform.
    :return: DLL path.
    """
    lib_name = 'extern_draco'
    blender_root = Path(bpy.app.binary_path).parent
    python_lib = Path('2.80/python/lib')
    paths = {
        'win32': blender_root/python_lib/'site-packages'/'{}.dll'.format(lib_name),
        'linux': blender_root/python_lib/'python3.7'/'site-packages'/'lib{}.so'.format(lib_name),
        'darwin': blender_root.parent/'Resources'/python_lib/'python3.7'/'site-packages'/'lib{}.dylib'.format(lib_name)
    }

    path = paths.get(sys.platform)
    return path if path is not None else ''


def dll_exists() -> bool:
    """
    Checks whether the DLL path exists.
    :return: True if the DLL exists.
    """
    exists = dll_path().exists()
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

    dll.createCompressor.restype = c_void_p
    dll.createCompressor.argtypes = []

    dll.setCompressionLevel.restype = None
    dll.setCompressionLevel.argtypes = [c_void_p, c_uint32]

    dll.setPositionQuantizationBits.restype = None
    dll.setPositionQuantizationBits.argtypes = [c_void_p, c_uint32]

    dll.setNormalQuantizationBits.restype = None
    dll.setNormalQuantizationBits.argtypes = [c_void_p, c_uint32]

    dll.setTexCoordQuantizationBits.restype = None
    dll.setTexCoordQuantizationBits.argtypes = [c_void_p, c_uint32]

    dll.compress.restype = c_bool
    dll.compress.argtypes = [c_void_p]

    dll.compressedSize.restype = c_uint64
    dll.compressedSize.argtypes = [c_void_p]

    dll.disposeCompressor.restype = None
    dll.disposeCompressor.argtypes = [c_void_p]

    dll.setFaces.restype = None
    dll.setFaces.argtypes = [c_void_p, c_uint32, c_uint32, c_void_p]

    dll.addPositionAttribute.restype = None
    dll.addPositionAttribute.argtypes = [c_void_p, c_uint32, c_char_p]

    dll.addNormalAttribute.restype = None
    dll.addNormalAttribute.argtypes = [c_void_p, c_uint32, c_char_p]

    dll.addTexCoordAttribute.restype = None
    dll.addTexCoordAttribute.argtypes = [c_void_p, c_uint32, c_char_p]

    dll.copyToBytes.restype = None
    dll.copyToBytes.argtypes = [c_void_p, c_char_p]

    dll.getTexCoordAttributeIdCount.restype = c_uint32
    dll.getTexCoordAttributeIdCount.argtypes = [c_void_p]

    dll.getTexCoordAttributeId.restype = c_uint32
    dll.getTexCoordAttributeId.argtypes = [c_void_p, c_uint32]

    dll.getPositionAttributeId.restype = c_uint32
    dll.getPositionAttributeId.argtypes = [c_void_p]

    dll.getNormalAttributeId.restype = c_uint32
    dll.getNormalAttributeId.argtypes = [c_void_p]

    dll.setCompressionLevel.restype = None
    dll.setCompressionLevel.argtypes = [c_void_p, c_uint32]

    dll.setPositionQuantizationBits.restype = None
    dll.setPositionQuantizationBits.argtypes = [c_void_p, c_uint32]

    dll.setNormalQuantizationBits.restype = None
    dll.setNormalQuantizationBits.argtypes = [c_void_p, c_uint32]

    dll.setTexCoordQuantizationBits.restype = None
    dll.setTexCoordQuantizationBits.argtypes = [c_void_p, c_uint32]

    for scene in scenes:
        for node in scene.nodes:
            __traverse_node(node, lambda node: __compress_node(node, dll, export_settings))

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
            attributes['POSITION'].buffer_view = None
            attributes['NORMAL'].buffer_view = None
            for attribute in [attributes[attr] for attr in attributes if attr.startswith('TEXCOORD_')]:
                attribute.buffer_view = None

def __compress_node(node, dll, export_settings):
    """Compress a single node."""
    if not (node.mesh is None):
        print_console("INFO", "Compressing mesh " + node.name)
        for primitive in node.mesh.primitives:
            __compress_primitive(primitive, dll, export_settings)

def __traverse_node(node, f):
    """Calls f for each node and all child nodes, recursively."""
    f(node)
    if not (node.children is None):
        for child in node.children:
            __traverse_node(child)


def __compress_primitive(primitive, dll, export_settings):
    attributes = primitive.attributes

    # Begin mesh.
    compressor = dll.createCompressor()

    # Process position attributes.
    dll.addPositionAttribute(compressor, attributes['POSITION'].count, attributes['POSITION'].buffer_view.data)

    # Process normal attributes.
    dll.addNormalAttribute(compressor, attributes['NORMAL'].count, attributes['NORMAL'].buffer_view.data)

    # Process texture coordinate attributes.
    for attribute in [attributes[attr] for attr in attributes if attr.startswith('TEXCOORD_')]:
        dll.addTexCoordAttribute(compressor, attribute.count, attribute.buffer_view.data)

    # Process faces.
    index_byte_length = {
        'Byte': 1,
        'UnsignedByte': 1,
        'Short': 2,
        'UnsignedShort': 2,
        'UnsignedInt': 4,
    }
    indices = primitive.indices
    dll.setFaces(compressor, indices.count, index_byte_length[indices.component_type.name], indices.buffer_view.data)

    # Set compression parameters.
    dll.setCompressionLevel(compressor, export_settings['gltf_draco_mesh_compression_level'])
    dll.setPositionQuantizationBits(compressor, export_settings['gltf_draco_position_quantization'])
    dll.setNormalQuantizationBits(compressor, export_settings['gltf_draco_normal_quantization'])
    dll.setTexCoordQuantizationBits(compressor, export_settings['gltf_draco_texcoord_quantization'])

    # After all point and connectivity data has been written to the compressor,
    # it can finally be compressed.
    if dll.compress(compressor):

        # Compression was successfull.
        # Move compressed data into a bytes object,
        # which is referenced by a 'gltf2_io_binary_data.BinaryData':
        #
        # "KHR_draco_mesh_compression": {
        #     ....
        #     "buffer_view": Compressed data inside a 'gltf2_io_binary_data.BinaryData'.
        # }

        # Query size necessary to hold all the compressed data.
        compression_size = dll.compressedSize(compressor)

        # Allocate byte buffer and write compressed data to it.
        compressed_data = bytes(compression_size)
        dll.copyToBytes(compressor, compressed_data)

        if primitive.extensions is None:
            primitive.extensions = {}

        tex_coord_ids = {}
        for id in range(0, dll.getTexCoordAttributeIdCount(compressor)):
            tex_coord_ids["TEXCOORD_" + str(id)] = dll.getTexCoordAttributeId(compressor, id)

        # Register draco compression extension into primitive.
        primitive.extensions["KHR_draco_mesh_compression"] = {
            'bufferView': BinaryData(compressed_data),
            'attributes': {
                'POSITION': dll.getPositionAttributeId(compressor),
                'NORMAL': dll.getNormalAttributeId(compressor),
                **tex_coord_ids,
            }
        }

        # Set to triangle list mode.
        primitive.mode = 4

    # Afterwards, the compressor can be released.
    dll.disposeCompressor(compressor)

    pass
