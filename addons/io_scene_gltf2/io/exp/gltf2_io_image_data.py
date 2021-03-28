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
import re


class ImageData:
    """Contains encoded images"""
    # FUTURE_WORK: as a method to allow the node graph to be better supported, we could model some of
    # the node graph elements with numpy functions

    def __init__(self, data: bytes, mime_type: str, name: str):
        self._data = data
        self._mime_type = mime_type
        self._name = name

    def __eq__(self, other):
        return self._data == other.data

    def __hash__(self):
        return hash(self._data)

    def adjusted_name(self):
        regex_dot = re.compile("\.")
        adjusted_name = re.sub(regex_dot, "_", self.name)
        new_name = "".join([char for char in adjusted_name if char not in "!#$&'()*+,/:;<>?@[\]^`{|}~"])
        return new_name

    @property
    def data(self):
        return self._data

    @property
    def name(self):
        return self._name

    @property
    def file_extension(self):
        if self._mime_type == "image/jpeg":
            return ".jpg"
        return ".png"

    @property
    def byte_length(self):
        return len(self._data)
