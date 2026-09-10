# SPDX-FileCopyrightText: 2026 The glTF-Blender-IO authors
#
# SPDX-License-Identifier: Apache-2.0

import ctypes
import numpy as np

from ...io.com.library import dll_path


class KtxEncoder:
    """KTX2 encoder."""
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("%s should not be instantiated" % cls)

    @staticmethod
    def find_library():
        """Find the KTX encoder library."""
        path = dll_path('bf_intern_ktx_bridge', 'KTX')
        if path is not None and path.exists() and path.is_file():
            return path
        else:
            raise RuntimeError("KTX encoder library not found at {}".format(path))

    @staticmethod
    def load_library(export_settings):
        """Load the KTX encoder library."""
        if 'ktx_encoder' in export_settings.keys():
            return
        lib_path = KtxEncoder.find_library()
        try:
            lib = ctypes.CDLL(lib_path.resolve())
        except Exception as e:
            raise RuntimeError("Failed to load KTX encoder library: {}".format(e))

        export_settings['ktx_encoder'] = lib

        # ktx_error_code_e encodeToFile(const char* filename, const unsigned char* pixels,
        #                                unsigned int width, unsigned int height,
        #                                unsigned int channels, int quality)
        lib.encodeToFile.restype = ctypes.c_int
        lib.encodeToFile.argtypes = [
            ctypes.c_char_p,                 # const char* filename
            ctypes.POINTER(ctypes.c_ubyte),  # const unsigned char* pixels
            ctypes.c_uint32,                 # unsigned int width
            ctypes.c_uint32,                 # unsigned int height
            ctypes.c_uint32,                 # unsigned int channels
            ctypes.c_int,                    # int quality
        ]

    @staticmethod
    def encode_file(export_settings, filepath, pixels, width, height, channels, quality=80):
        """Encodes a flat RGB(A) pixel buffer to a KTX2 file at `filepath`.

        `pixels` is a flat float buffer of width * height * channels values in [0, 1], rows
        bottom-to-top -- i.e. straight from `Image.pixels.foreach_get()`, symmetric with what
        `KtxDecoder.decode_file()` returns on the import side. Values are rescaled to [0, 255]
        and rounded, not truncated -- a raw `dtype=np.uint8` cast would floor every value to
        0 or 1.
        """
        KtxEncoder.load_library(export_settings)
        lib = export_settings['ktx_encoder']

        pixels = np.ascontiguousarray(pixels, dtype=np.float32)
        pixels = np.clip(np.rint(pixels * 255.0), 0, 255).astype(np.uint8)

        error_code = lib.encodeToFile(
            str(filepath).encode('utf-8'),
            pixels.ctypes.data_as(ctypes.POINTER(ctypes.c_ubyte)),
            width,
            height,
            channels,
            quality,
        )
        if error_code != 0:
            raise RuntimeError("KTX encoding failed with error code {}".format(error_code))
