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
    path = Path('/Users/work/ux3d/draco_blender/build/bin/2.80/python/lib/python3.7/Debug/libglTF-Blender-IO_DracoMeshCompression.dylib')
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
