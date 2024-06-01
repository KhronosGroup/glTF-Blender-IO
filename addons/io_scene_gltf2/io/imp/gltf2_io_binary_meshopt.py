# Copyright 2022 The glTF-Blender-IO authors.
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
import sys
import os
from .gltf2_io_gltf import ImportError


class MeshoptDecompressor:
    """Decompressor for """
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("%s should not be instantiated" % cls)

    @staticmethod
    def find_library():
        """Returns path to the meshoptimizer library."""
        import site

        lib_name = 'extern_meshoptimizer'
        lib_name = {
            'win32':  f'{lib_name}.dll',
            'linux':  f'lib{lib_name}.so',
            'darwin': f'lib{lib_name}.dylib',
        }.get(sys.platform)

        locs = site.getsitepackages() + [site.getusersitepackages()]
        locs = [os.path.join(loc, lib_name) for loc in locs]
        for loc in locs:
            if os.path.exists(loc):
                return loc

        print(f'Looked for {lib_name} in the following locations:')
        for loc in locs:
            print('  ', loc)
        print()

        raise ImportError(
            "Can't load model using EXT_meshopt_compression. "
            f"Couldn't find {lib_name}. "
            "See console for where to install it."
        )

    @staticmethod
    def load_library(gltf):
        if hasattr(gltf, 'meshopt_lib'):
            return

        lib_path = MeshoptDecompressor.find_library()
        try:
            lib = ctypes.CDLL(lib_path)
        except Exception as e:
            raise RuntimeError('Error loading meshopt library:', e)

        gltf.meshopt_lib = lib

        # declare type signatures

        decode_fns = [
            lib.meshopt_decodeVertexBuffer,
            lib.meshopt_decodeIndexBuffer,
            lib.meshopt_decodeIndexSequence,
        ]
        for fn in decode_fns:
            fn.restype = ctypes.c_int
            fn.argtypes = [
                ctypes.c_void_p,  # void* destination
                ctypes.c_size_t,  # size_t count
                ctypes.c_size_t,  # size_t stride
                ctypes.POINTER(ctypes.c_ubyte),  # const unsigned char* buffer
                ctypes.c_size_t,  # size_t buffer_size
            ]

        filter_fns = [
            lib.meshopt_decodeFilterOct,
            lib.meshopt_decodeFilterQuat,
            lib.meshopt_decodeFilterExp,
        ]
        for fn in filter_fns:
            fn.restype = None
            fn.argtypes = [
                ctypes.c_void_p,  # void* buffer
                ctypes.c_size_t,  # size_t count
                ctypes.c_size_t,  # size_t stride
            ]

    @staticmethod
    def get_buffer_view(gltf, bufferview_idx):
        """Decodes EXT_meshopt_compression-compressed buffer view."""
        # check if already in cache
        if not hasattr(gltf, 'meshopt_cache'):
            gltf.meshopt_cache = {}
        if bufferview_idx in gltf.meshopt_cache:
            return gltf.meshopt_cache[bufferview_idx]

        bufview = gltf.data.buffer_views[bufferview_idx]
        ext = bufview.extensions['EXT_meshopt_compression']

        buffer_idx = ext['buffer']
        byte_length = ext['byteLength']
        byte_offset = ext.get('byteOffset', 0)
        byte_stride = ext['byteStride']
        count = ext['count']
        mode = ext['mode']
        filter = ext.get('filter', 'NONE')

        # load library
        MeshoptDecompressor.load_library(gltf)
        lib = gltf.meshopt_lib

        # load buffer
        if buffer_idx not in gltf.buffers:
            gltf.load_buffer(buffer_idx)

        buffer = gltf.buffers[buffer_idx]
        buffer = buffer[byte_offset : byte_offset + byte_length]

        # create output buffer
        output = memoryview(bytearray(count * byte_stride))

        dst_ptr = (ctypes.c_ubyte * len(output)).from_buffer(output)
        # TODO: this creates an unnecessary copy, I don't know how to
        #       pass it to C without one though
        buf_ptr = (ctypes.c_ubyte * len(buffer)).from_buffer_copy(buffer)

        decode_fn = {
            'ATTRIBUTES': lib.meshopt_decodeVertexBuffer,
            'TRIANGLES': lib.meshopt_decodeIndexBuffer,
            'INDICES': lib.meshopt_decodeIndexSequence,
        }[mode]

        # decode
        error_code = decode_fn(
            dst_ptr,
            count,
            byte_stride,
            buf_ptr,
            len(buffer),
        )

        if error_code != 0:
            raise RuntimeError(
                'EXT_meshopt_compression: decoding error '
                f'(buffer view: {bufferview_idx}, error code: {error_code})'
            )

        # apply filters
        if mode == 'ATTRIBUTES' and filter != 'NONE':
            filter_fn = {
                'OCTAHEDRAL': lib.meshopt_decodeFilterOct,
                'QUATERNION': lib.meshopt_decodeFilterQuat,
                'EXPONENTIAL': lib.meshopt_decodeFilterExp,
            }[filter]

            filter_fn(dst_ptr, count, byte_stride)

        # cache result
        gltf.meshopt_cache[bufferview_idx] = output

        return output
