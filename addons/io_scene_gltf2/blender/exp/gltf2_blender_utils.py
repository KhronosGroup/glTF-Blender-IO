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

import math
from io_scene_gltf2.io.com import gltf2_io_constants


#TODO: we could apply functional programming to these problems (currently we only have a single use case)

def split_list_by_data_type(l: list, data_type: gltf2_io_constants.DataType):
    """
    Split a flat list of components by their data type \\
    E.g.: A list [0,1,2,3,4,5] of data type Vec3 would be split to [[0,1,2], [3,4,5]]
    :param l: the flat list
    :param data_type: the data type of the list
    :return: a list of lists, where each element list contains the components of the data type
    """
    if not (len(l) % gltf2_io_constants.DataType.num_elements(data_type) == 0):
        raise ValueError("List length does not match specified data type")
    num_elements = gltf2_io_constants.DataType.num_elements(data_type)
    return [l[i:i + num_elements] for i in range(0, len(l), num_elements)]


def max_components(l: list, data_type: gltf2_io_constants.DataType) -> list:
    """
    Find the maximum components in a flat list, as for example is required for the glTF2.0 accessor min and max properties
    :param l: the flat list of components
    :param data_type: the data type of the list (determines the length of the result)
    :return: a list with length num_elements(data_type) containing the maximum per component along the list
    """
    components_lists = split_list_by_data_type(l, data_type)
    result = [-math.inf] * gltf2_io_constants.DataType.num_elements(data_type)
    for components in components_lists:
        for i, c in enumerate(components):
            result[i] = max(result[i], c)
    return result


def min_components(l: list, data_type: gltf2_io_constants.DataType) -> list:
    """
        Find the minimum components in a flat list, as for example is required for the glTF2.0 accessor min and max properties
        :param l: the flat list of components
        :param data_type: the data type of the list (determines the length of the result)
        :return: a list with length num_elements(data_type) containing the minimum per component along the list
        """
    components_lists = split_list_by_data_type(l, data_type)
    result = [math.inf] * gltf2_io_constants.DataType.num_elements(data_type)
    for components in components_lists:
        for i, c in enumerate(components):
            result[i] = min(result[i], c)
    return result



