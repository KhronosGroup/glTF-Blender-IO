# Copyright 2026 The glTF-Blender-IO authors.
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

import ctypes
import numpy as np

from ...io.com.library import dll_path


class MeshoptEncoder:
    """Meshopt encoder."""
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("%s should not be instantiated" % cls)

    @staticmethod
    def find_library():
        """Find the Meshopt encoder library."""
        path = dll_path('extern_meshoptimizer', 'MeshOptimizer')
        if path is not None and path.exists() and path.is_file():
            return path
        else:
            raise RuntimeError("Meshopt encoder library not found at {}".format(path))

    @staticmethod
    def load_library(export_settings):
        """Load the Meshopt encoder library."""
        if 'meshopt_encoder' in export_settings.keys():
            return
        lib_path = MeshoptEncoder.find_library()
        try:
            lib = ctypes.CDLL(lib_path.resolve())
        except Exception as e:
            raise RuntimeError("Failed to load Meshopt encoder library: {}".format(e))

        export_settings['meshopt_encoder'] = lib

        # Define type signatures for the encoder functions
        lib.meshopt_encodeIndexVersion.argtypes = [ctypes.c_int]
        lib.meshopt_encodeIndexVersion.restype = None
        lib.meshopt_encodeIndexVersion(1)

        lib.meshopt_encodeVertexVersion.argtypes = [ctypes.c_int]
        lib.meshopt_encodeVertexVersion.restype = None
        lib.meshopt_encodeVertexVersion(0)   # TODO: 0 for EXT, 1 for KHR

        lib.meshopt_encodeIndexBufferBound.argtypes = [ctypes.c_size_t, ctypes.c_size_t]
        lib.meshopt_encodeIndexBufferBound.restype = ctypes.c_size_t

        lib.meshopt_encodeIndexBuffer.argtypes = [
            ctypes.POINTER(ctypes.c_ubyte),   # buffer
            ctypes.c_size_t,                  # buffer_size
            ctypes.POINTER(ctypes.c_uint),    # indices
            ctypes.c_size_t,                  # index_count
        ]
        lib.meshopt_encodeIndexBuffer.restype = ctypes.c_size_t

        lib.encodeVertexBuffer.restype = ctypes.c_int
        lib.encodeVertexBuffer.argtypes = [
            ctypes.c_void_p,  # unsigned char* out
            ctypes.c_size_t,  # size_t n
            ctypes.c_void_p,  # const void* vertices
            ctypes.c_size_t,  # size_t vertex_count
            ctypes.c_size_t,  # size_t vertex_size
        ]

        lib.encodeIndexBuffer.restype = ctypes.c_int
        lib.encodeIndexBuffer.argtypes = [
            ctypes.c_void_p,  # unsigned char* out
            ctypes.c_size_t,  # size_t n
            ctypes.c_void_p,  # const unsigned int* indices
            ctypes.c_size_t,  # size_t index_size
        ]

        lib.encodeIndexSequence.restype = ctypes.c_int
        lib.encodeIndexSequence.argtypes = [
            ctypes.c_void_p,  # unsigned char* out
            ctypes.c_size_t,  # size_t n
            ctypes.c_void_p,  # const unsigned int* indices
            ctypes.c_size_t,  # size_t index_count
        ]

    @staticmethod
    def encode_indices(mode, data, export_settings):

        if mode not in [4, None]:
            return MeshoptEncoder.encode_index_sequence(data, export_settings)
        else:
            return MeshoptEncoder.encode_index_buffer(data, export_settings)

    @staticmethod
    def encode_index_buffer(data, export_settings):

        MeshoptEncoder.load_library(export_settings)
        lib = export_settings['meshopt_encoder']

        index_count = len(data)
        vertex_count = int(data.max()) + 1

        bound = lib.meshopt_encodeIndexBufferBound(index_count, vertex_count)
        buffer = (ctypes.c_ubyte * bound)()

        to_be_converted_data = np.ascontiguousarray(data, dtype=np.uint32)

        written = lib.meshopt_encodeIndexBuffer(
            buffer,
            bound,
            to_be_converted_data.ctypes.data_as(ctypes.POINTER(ctypes.c_uint)),
            index_count
        )

        return bytes(buffer[:written])

    @staticmethod
    def encode_index_sequence(data, export_settings):

        MeshoptEncoder.load_library(export_settings)
        lib = export_settings['meshopt_encoder']

        index_count = len(data)
        vertex_count = int(data.max()) + 1

        # vertex count is not needed for sequence encoding
        bound = lib.meshopt_encodeIndexSequenceBound(index_count, vertex_count)
        buffer = (ctypes.c_ubyte * bound)()

        to_be_converted_data = np.ascontiguousarray(data, dtype=np.uint32)

        written = lib.meshopt_encodeIndexSequence(
            buffer,
            bound,
            to_be_converted_data.ctypes.data_as(ctypes.POINTER(ctypes.c_uint)),
            index_count
        )

        return bytes(buffer[:written])

    @staticmethod
    def encode_attribute(attribute_name, data, export_settings):

        MeshoptEncoder.load_library(export_settings)
        lib = export_settings['meshopt_encoder']

        vertex_count = len(data)
        vertex_size = data.strides[0]

        bound = lib.meshopt_encodeVertexBufferBound(vertex_count, vertex_size)
        buffer = (ctypes.c_ubyte * bound)()

        to_be_converted_data = np.ascontiguousarray(data)

        written = lib.encodeVertexBuffer(
            buffer,
            bound,
            to_be_converted_data.ctypes.data_as(ctypes.c_void_p),
            vertex_count,
            vertex_size
        )

        # TODO manage filter

        return bytes(buffer[:written])
