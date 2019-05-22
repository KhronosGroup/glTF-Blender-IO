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
from io_scene_gltf2.blender.com import gltf2_blender_json


def generate_extras(blender_element):
    """Filter and create a custom property, which is stored in the glTF extra field."""
    if not blender_element:
        return None

    extras = {}

    # Custom properties, which are in most cases present and should not be exported.
    black_list = ['cycles', 'cycles_visibility', 'cycles_curves', '_RNA_UI']

    count = 0
    for custom_property in blender_element.keys():
        if custom_property in black_list:
            continue

        value = __to_json_compatible(blender_element[custom_property])

        if value is not None:
            extras[custom_property] = value
            count += 1

    if count == 0:
        return None

    return extras


def __to_json_compatible(value):
    """Make a value (usually a custom property) compatible with json"""

    if isinstance(value, bpy.types.ID):
        return value

    elif isinstance(value, str):
        return value

    elif isinstance(value, (int, float)):
        return value

    # for list classes
    elif isinstance(value, list):
        value = list(value)
        # make sure contents are json-compatible too
        for index in range(len(value)):
            value[index] = __to_json_compatible(value[index])
        return value

    # for IDPropertyArray classes
    elif hasattr(value, "to_list"):
        value = value.to_list()
        return value

    elif hasattr(value, "to_dict"):
        value = value.to_dict()
        if gltf2_blender_json.is_json_convertible(value):
            return value

    return None
