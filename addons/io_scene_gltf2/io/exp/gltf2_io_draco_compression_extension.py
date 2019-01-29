from ctypes import *
from io_scene_gltf2 import *
from io_scene_gltf2.blender.exp.gltf2_blender_export import *
from io_scene_gltf2.blender.exp.gltf2_blender_gather import gather_gltf2
from io_scene_gltf2.io.exp.gltf2_io_binary_data import BinaryData

import sys


def dll_path() -> str:
    """
    Get the DLL path depending on the underlying platform.
    :return: DLL path.
    """
    paths = {
        'win32': 'C:/Windows/blender-draco-exporter.dll',
        'linux': '/usr/lib/libblender-draco-exporter.so',
        'cygwin': '',
        'darwin': '/usr/lib/libblender-draco-exporter.dylib',
    }
    return paths[sys.platform]


def dll_exists() -> bool:
    """
    Checks wether the DLL path exists and the file can be opended for reading.
    :return: True if the DLL exists.
    """
    try:
        f = open(dll_path(), "rb")
        f.close()
        return True
    except FileNotFoundError:
        return False


def compress_scene_primitives(scenes, export_settings):
    """
    Handles draco compression.
    Invoked after data has been gathered, but before scenes get traversed.
    Moves position, normal and texture coordinate attributes into a Draco compressed buffer.
    """

    # Load DLL and setup function signatures.
    # Nearly all functions take the compressor as the first argument.
    dll = cdll.LoadLibrary(dll_path())

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
            __traverse_node(node, dll, export_settings)


def __traverse_node(node, dll, export_settings):
    if not (node.mesh is None):
        print("Compressing mesh " + node.name)
        for primitive in node.mesh.primitives:
            __compress_primitive(primitive, dll, export_settings)

    if not (node.children is None):
        for child in node.children:
            __traverse_node(child, dll, export_settings)


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
    indices.buffer_view = None

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
        compressionSize = dll.compressedSize(compressor)

        # Allocate byte buffer and write compressed data to it.
        compressedData = bytes(compressionSize)
        dll.copyToBytes(compressor, compressedData)

        if primitive.extensions is None:
            primitive.extensions = {}

        texCoordIds = {}
        for id in range(0, dll.getTexCoordAttributeIdCount(compressor)):
            texCoordIds["TEXCOORD_" + str(id)] = dll.getTexCoordAttributeId(compressor, id)

        # Register draco compression extension into primitive.
        primitive.extensions["KHR_draco_mesh_compression"] = {
            'bufferView': BinaryData(compressedData),
            'attributes': {
                'POSITION': dll.getPositionAttributeId(compressor),
                'NORMAL': dll.getNormalAttributeId(compressor),
                **texCoordIds,
            }
        }

        # Set to triangle list mode.
        primitive.mode = 4

        # Remove buffers from attribute, since the data now resides inside the compressed Draco buffer.
        attributes['POSITION'].buffer_view = None
        attributes['NORMAL'].buffer_view = None
        for attribute in [attributes[attr] for attr in attributes if attr.startswith('TEXCOORD_')]:
            attribute.buffer_view = None

    # Afterwards, the compressor can be released.
    dll.disposeCompressor(compressor)

    pass
