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

from typing import List, Dict, Any


class Extension:
    """Container for extensions. Allows to specify requiredness"""
    def __init__(self, name: str, extension: Dict[str, Any], required: bool = True):
        self.name = name
        self.extension = extension
        self.required = required


class ChildOfRootExtension(Extension):
    """Container object for extensions that should be appended to the root extensions"""
    def __init__(self, path: List[str], name: str, extension: Dict[str, Any], required: bool = True):
        """
        Wrap a local extension entity into an object that will later be inserted into a root extension and converted
        to a reference.
        :param path: The path of the extension object in the root extension. E.g. ['lights'] for
        KHR_lights_punctual. Must be a path to a list in the extensions dict.
        :param extension: The data that should be placed into the extension list
        """
        self.path = path
        super().__init__(name, extension, required)
