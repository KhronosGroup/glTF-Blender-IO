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

#
# Imports
#

import bpy
from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached
from ..com.gltf2_blender_material_helpers import get_gltf_node_name, get_gltf_node_old_name
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


#TODOSNodes: is path still used somewhere ?
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
    #TODOSNodes Manage groups
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

@cached
def get_texture_node_from_socket(socket, export_settings):
    result = from_socket(
        socket,
        FilterByType(bpy.types.ShaderNodeTexImage))
    if not result:
        return None
    if result[0].shader_node.image is None:
        return None
    return result[0]

def has_image_node_from_socket(socket, export_settings):
    result = get_texture_node_from_socket(socket, export_settings)
    return result is not None

# return the default value of a socket, even if this socket is linked
def get_const_from_default_value_socket(socket, kind):
    if kind == 'RGB':
        if socket.type != 'RGBA': return None
        return list(socket.default_value)[:3]
    if kind == 'VALUE':
        if socket.type != 'VALUE': return None
        return socket.default_value
    return None


def get_socket_from_gltf_material_node(blender_material: bpy.types.Material, name: str):
    """
    For a given material input name, retrieve the corresponding node tree socket in the special glTF node group.

    :param blender_material: a blender material for which to get the socket
    :param name: the name of the socket
    :return: a blender NodeSocket
    """
    gltf_node_group_names = [get_gltf_node_name().lower(), get_gltf_node_old_name().lower()]
    if blender_material.node_tree and blender_material.use_nodes:
        nodes = [n for n in blender_material.node_tree.nodes if \
            isinstance(n, bpy.types.ShaderNodeGroup) and \
            (n.node_tree.name.startswith('glTF Metallic Roughness') or n.node_tree.name.lower() in gltf_node_group_names)]
        inputs = sum([[input for input in node.inputs if input.name == name] for node in nodes], [])
        if inputs:
            return inputs[0]

    return None