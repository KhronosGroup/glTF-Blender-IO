# Copyright (c) 2017 The Khronos Group Inc.
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

#
# Imports
#

import bpy
import typing


class Filter():
    """
    Base class for all node tree filter operations
    """
    def __init__(self):
        pass

    def __call__(self, shader_node):
        return True


class FilterByName(Filter):
    """
    Filter the material node tree by name

    example usage:
    find_from_socket(start_socket, ShaderNodeFilterByName("Normal"))
    """
    def __init__(self, name):
        self.name = name

    def __call__(self, shader_node):
        return shader_node.name == self.name


class FilterByType(Filter):
    """
    Filter the material node tree by type
    """
    def __init__(self, type):
        self.type = type

    def __call__(self, shader_node):
        return isinstance(shader_node, self.type)


def gather_from_socket(start_socket: bpy.types.NodeSocket,
                       shader_node_filter: typing.Union[Filter, typing.Callable]):
    """
    Find shader nodes where the filter expression is true.
    :param start_socket: the beginning of the traversal
    :param shader_node_filter: should be a function(x: shader_node) -> bool
    :return: a list of shader nodes for which filter is true
    """
    results = []
    for link in start_socket.links:
        linked_node = link.from_node
        if shader_node_filter(linked_node):
            results.append(linked_node)
        for input_socket in linked_node.inputs:
            results += gather_from_socket(input_socket, shader_node_filter)
    return results