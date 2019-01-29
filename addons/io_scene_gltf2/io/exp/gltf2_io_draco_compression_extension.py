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
        'linux': '/usr/share/lib/libblender-draco-exporter.so',
        'cygwin': '',
        'darwin': '',
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


def compress_scene_primitives(scenes):
    """
    Handles draco compression.
    Invoked after data has been gathered, but before scenes get traversed.
    Moves position, normal and texture coordinate attributes into a Draco compressed buffer.
    """

    # Load DLL
    dll = cdll.LoadLibrary(dll_path())

    # Set up function pointer types.
    dll.createCompressor.restype = c_void_p
    dll.createCompressor.argtypes = []

    dll.compress.restype = None
    dll.compress.argtypes = [c_void_p]

    dll.compressedSize.restype = c_uint64
    dll.compressedSize.argtypes = [c_void_p]

    dll.disposeCompressor.restype = None
    dll.disposeCompressor.argtypes = [c_void_p]

    dll.setFaces.restype = None
    dll.setFaces.argtypes = [c_void_p, c_uint32, c_uint32, c_void_p]

    dll.addPositions.restype = None
    dll.addPositions.argtypes = [c_void_p, c_uint32, c_char_p]

    dll.addNormals.restype = None
    dll.addNormals.argtypes = [c_void_p, c_uint32, c_char_p]

    dll.addTexcoords.restype = None
    dll.addTexcoords.argtypes = [c_void_p, c_uint32, c_char_p]

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

    for scene in scenes:
        for node in scene.nodes:
            __traverse_node(node, dll)


def __traverse_node(node, dll):
    if not (node.mesh is None):
        print("Compressing mesh " + node.name)
        for primitive in node.mesh.primitives:
            __compress_primitive(primitive, dll)

    if not (node.children is None):
        for child in node.children:
            __traverse_node(child, dll)


def __compress_primitive(primitive, dll):
    attributes = primitive.attributes

    # Begin mesh.
    compressor = dll.createCompressor()

    # Process position attributes.
    dll.addPositions(compressor, attributes['POSITION'].count, attributes['POSITION'].buffer_view.data)
    attributes['POSITION'].buffer_view = None

    # Process normal attributes.
    dll.addNormals(compressor, attributes['NORMAL'].count, attributes['NORMAL'].buffer_view.data)
    attributes['NORMAL'].buffer_view = None

    # Process texture coordinate attributes.
    for attribute in [attributes[attr] for attr in attributes if attr.startswith('TEXCOORD_')]:
        dll.addTexcoords(compressor, attribute.count, attribute.buffer_view.data)
        attribute.buffer_view = None

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

    # After all point and connectivity data has been written to the compressor,
    # it can finally be compressed.
    dll.compress(compressor)

    # Query size necessary to hold all the compressed data.
    compressionSize = dll.compressedSize(compressor)

    # Allocate byte buffer and write compressed data to it.
    compressedData = bytes(compressionSize)
    dll.copyToBytes(compressor, compressedData)

    if primitive.extensions is None:
        primitive.extensions = {}

    texCoordIds = {}
    texCoordAttributeCount = dll.getTexCoordAttributeIdCount(compressor)
    if texCoordAttributeCount == 1:
        texCoordIds["TEXCOORD_0"] = dll.getTexCoordAttributeId(compressor, 0)

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

    # Afterwards, the compressor can be released.
    dll.disposeCompressor(compressor)

    pass
