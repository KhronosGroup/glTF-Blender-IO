# Copyright 2018 The glTF-Blender-IO authors.
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

import array
from io_scene_gltf2.io.com import gltf2_io_constants


class BinaryData:
    """

    """
    def __init__(self, data: bytes):
        if not isinstance(data, bytes):
            raise TypeError("Data is not a bytes array")
        self.data = data

    @classmethod
    def from_list(cls, lst: list, gltf_component_type: gltf2_io_constants.ComponentType):
        # if gltf_component_type not in gltf2_io_constants.ComponentType:
        #     raise ValueError("Invalid list data type")
        format_char = gltf2_io_constants.ComponentType.to_type_code(gltf_component_type)
        return BinaryData(array.array(format_char, lst).tobytes())

    @property
    def byte_length(self):
        return len(self.data)
