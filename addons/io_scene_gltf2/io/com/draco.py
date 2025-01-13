# Copyright 2018-2021 The glTF-Blender-IO authors.
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

import os
import sys
from pathlib import Path
import bpy


def dll_path() -> Path:
    """
    Get the library path, that should be at addon root
    :return: library path.
    """
    lib_name = 'extern_draco'
    library_name = {
        'win32': '{}.dll'.format(lib_name),
        'linux': 'lib{}.so'.format(lib_name),
        'darwin': 'lib{}.dylib'.format(lib_name)
    }.get(sys.platform)

    path = os.path.dirname(sys.modules['io_scene_gltf2'].__file__)
    if path is not None:
        return Path(os.path.join(path, library_name))

    if library_name is None:
        print('WARNING', 'Unsupported platform {}, Draco mesh compression is unavailable'.format(sys.platform))


def dll_exists(quiet=False) -> bool:
    """
    Checks whether the DLL path exists.
    :return: True if the DLL exists.
    """
    path = dll_path()
    exists = path.exists() and path.is_file()
    if quiet is False:
        if exists:
            print('INFO', 'Draco mesh compression is available, use library at %s' % dll_path().absolute())
        else:
            print(
                'ERROR',
                'Draco mesh compression is not available because library could not be found at %s' %
                dll_path().absolute())
    return exists
