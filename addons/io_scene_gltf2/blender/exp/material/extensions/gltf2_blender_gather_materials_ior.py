# Copyright 2018-2022 The glTF-Blender-IO authors.
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

from .....io.com.gltf2_io_extensions import Extension
from .....io.com.gltf2_io_constants import GLTF_IOR
from ....exp import gltf2_blender_get

def export_ior(blender_material, extensions, export_settings):
    ior_socket = gltf2_blender_get.get_socket(blender_material, 'IOR')

    if not ior_socket:
        return None

    # We don't manage case where socket is linked, always check default value
    if ior_socket.is_linked:
        # TODOExt: add warning?
        return None

    if ior_socket.default_value == GLTF_IOR:
        return None

    # Export only if the following extensions are exported:
    need_to_export_ior = [
        'KHR_materials_transmission',
        'KHR_materials_volume',
        'KHR_materials_specular'
    ]

    if not any([e in extensions.keys() for e in need_to_export_ior]):
        return None

    ior_extension = {}
    ior_extension['ior'] = ior_socket.default_value

    return Extension('KHR_materials_ior', ior_extension, False)