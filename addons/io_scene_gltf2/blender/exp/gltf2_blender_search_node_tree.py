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

#
# Imports
#

import bpy
import typing


class Filter:
    """Base class for all node tree filter operations."""

    def __init__(self):
        pass

    def __call__(self, shader_node):
        return True


class FilterByName(Filter):
    """
    Filter the material node tree by name.

    example usage:
    find_from_socket(start_socket, ShaderNodeFilterByName("Normal"))
    """

    def __init__(self, name):
        self.name = name
        super(FilterByName, self).__init__()

    def __call__(self, shader_node):
        return shader_node.name == self.name


class FilterByType(Filter):
    """Filter the material node tree by type."""

    def __init__(self, type):
        self.type = type
        super(FilterByType, self).__init__()

    def __call__(self, shader_node):
        return isinstance(shader_node, self.type)


class NodeTreeSearchResult:
    def __init__(self, shader_node: bpy.types.Node, path: typing.List[bpy.types.NodeLink]):
        self.shader_node = shader_node
        self.path = path


# TODO: cache these searches
def from_socket(start_socket: bpy.types.NodeSocket,
                shader_node_filter: typing.Union[Filter, typing.Callable]) -> typing.List[NodeTreeSearchResult]:
    """
    Find shader nodes where the filter expression is true.

    :param start_socket: the beginning of the traversal
    :param shader_node_filter: should be a function(x: shader_node) -> bool
    :return: a list of shader nodes for which filter is true
    """
    # hide implementation (especially the search path)
    def __search_from_socket(start_socket: bpy.types.NodeSocket,
                             shader_node_filter: typing.Union[Filter, typing.Callable],
                             search_path: typing.List[bpy.types.NodeLink]) -> typing.List[NodeTreeSearchResult]:
        results = []

        for link in start_socket.links:
            # follow the link to a shader node
            linked_node = link.from_node
            # check if the node matches the filter
            if shader_node_filter(linked_node):
                results.append(NodeTreeSearchResult(linked_node, search_path + [link]))
            # traverse into inputs of the node
            for input_socket in linked_node.inputs:
                linked_results = __search_from_socket(input_socket, shader_node_filter, search_path + [link])
                if linked_results:
                    # add the link to the current path
                    search_path.append(link)
                    results += linked_results

        return results

    if start_socket is None:
        return []

    return __search_from_socket(start_socket, shader_node_filter, [])
