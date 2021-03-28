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

import base64

from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.io.exp import gltf2_io_binary_data


class Buffer:
    """Class representing binary data for use in a glTF file as 'buffer' property."""

    def __init__(self, buffer_index=0):
        self.__data = bytearray(b"")
        self.__buffer_index = buffer_index

    def add_and_get_view(self, binary_data: gltf2_io_binary_data.BinaryData) -> gltf2_io.BufferView:
        """Add binary data to the buffer. Return a glTF BufferView."""
        offset = len(self.__data)
        self.__data.extend(binary_data.data)

        length = binary_data.byte_length

        # offsets should be a multiple of 4 --> therefore add padding if necessary
        padding = (4 - (length % 4)) % 4
        self.__data.extend(b"\x00" * padding)

        buffer_view = gltf2_io.BufferView(
            buffer=self.__buffer_index,
            byte_length=length,
            byte_offset=offset,
            byte_stride=None,
            extensions=None,
            extras=None,
            name=None,
            target=None
        )
        return buffer_view

    @property
    def byte_length(self):
        return len(self.__data)

    def to_bytes(self):
        return self.__data

    def to_embed_string(self):
        return 'data:application/octet-stream;base64,' + base64.b64encode(self.__data).decode('ascii')

    def clear(self):
        self.__data = b""
