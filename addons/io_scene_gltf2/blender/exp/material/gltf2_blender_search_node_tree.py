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
from mathutils import Vector, Matrix
from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached
from ...com.gltf2_blender_material_helpers import get_gltf_node_name, get_gltf_node_old_name, get_gltf_old_group_node_name
from ....blender.com.gltf2_blender_conversion import texture_transform_blender_to_gltf
from io_scene_gltf2.io.com import gltf2_io_debug
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
    def __init__(self, shader_node: bpy.types.Node, path: typing.List[bpy.types.NodeLink], group_path: typing.List[bpy.types.Node]):
        self.shader_node = shader_node
        self.path = path
        self.group_path = group_path


# TODO: cache these searches
def from_socket(start_socket: NodeTreeSearchResult,
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
                             search_path: typing.List[bpy.types.NodeLink],
                             group_path: typing.List[bpy.types.Node]) -> typing.List[NodeTreeSearchResult]:
        results = []
        for link in start_socket.links:
            # follow the link to a shader node
            linked_node = link.from_node

            if linked_node.type == "GROUP":
                group_output_node = [node for node in linked_node.node_tree.nodes if node.type == "GROUP_OUTPUT"][0]
                socket =  [sock for sock in group_output_node.inputs if sock.name == link.from_socket.name][0]
                group_path.append(linked_node)
                linked_results = __search_from_socket(socket, shader_node_filter, search_path + [link], group_path.copy())
                if linked_results:
                    # add the link to the current path
                    search_path.append(link)
                    results += linked_results
                continue

            if linked_node.type == "GROUP_INPUT":
                socket = [sock for sock in group_path[-1].inputs if sock.name == link.from_socket.name][0]
                linked_results = __search_from_socket(socket, shader_node_filter, search_path + [link], group_path[:-1])
                if linked_results:
                    # add the link to the current path
                    search_path.append(link)
                    results += linked_results
                continue

            # check if the node matches the filter
            if shader_node_filter(linked_node):
                results.append(NodeTreeSearchResult(linked_node, search_path + [link], group_path))
            # traverse into inputs of the node
            for input_socket in linked_node.inputs:
                linked_results = __search_from_socket(input_socket, shader_node_filter, search_path + [link], group_path.copy())
                if linked_results:
                    # add the link to the current path
                    search_path.append(link)
                    results += linked_results

        return results

    if start_socket.socket is None:
        return []

    return __search_from_socket(start_socket.socket, shader_node_filter, [], start_socket.group_path)

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
        if socket.socket.type != 'RGBA': return None
        return list(socket.socket.default_value)[:3]
    if kind == 'VALUE':
        if socket.socket.type != 'VALUE': return None
        return socket.socket.default_value
    return None

#TODOSNode : @cached? If yes, need to use id of node tree, has this is probably not fully hashable
# For now, not caching it. If we encounter performance issue, we will see later
def get_material_nodes(node_tree: bpy.types.NodeTree, group_path, type):
    """
    For a given tree, recursively return all nodes including node groups.
    """

    nodes = []
    for node in [n for n in node_tree.nodes if isinstance(n, type) and not n.mute]:
        nodes.append((node, group_path.copy()))

    # Some weird node groups with missing datablock can have no node_tree, so checking n.node_tree (See #1797)
    for node in [n for n in node_tree.nodes if n.type == "GROUP" and n.node_tree is not None and not n.mute and n.node_tree.name != get_gltf_old_group_node_name()]: # Do not enter the olf glTF node group
        new_group_path = group_path.copy()
        new_group_path.append(node)
        nodes.extend(get_material_nodes(node.node_tree, new_group_path, type))

    return nodes

def get_socket_from_gltf_material_node(blender_material: bpy.types.Material, name: str):
    """
    For a given material input name, retrieve the corresponding node tree socket in the special glTF node group.

    :param blender_material: a blender material for which to get the socket
    :param name: the name of the socket
    :return: a blender NodeSocket
    """
    gltf_node_group_names = [get_gltf_node_name().lower(), get_gltf_node_old_name().lower()]
    if blender_material.node_tree and blender_material.use_nodes:
        nodes = get_material_nodes(blender_material.node_tree, [blender_material], bpy.types.ShaderNodeGroup)
        # Some weird node groups with missing datablock can have no node_tree, so checking n.node_tree (See #1797)
        nodes = [n for n in nodes if n[0].node_tree is not None and ( n[0].node_tree.name.lower().startswith(get_gltf_old_group_node_name()) or n[0].node_tree.name.lower() in gltf_node_group_names)]
        inputs = sum([[(input, node[1]) for input in node[0].inputs if input.name == name] for node in nodes], [])
        if inputs:
            return NodeSocket(inputs[0][0], inputs[0][1])

    return NodeSocket(None, None)

class NodeSocket:
    def __init__(self, socket, group_path):
        self.socket = socket
        self.group_path = group_path

class ShNode:
    def __init__(self, node, group_path):
        self.node = node
        self.group_path = group_path

def get_node_socket(blender_material, type, name):
    """
    For a given material input name, retrieve the corresponding node tree socket for a given node type.

    :param blender_material: a blender material for which to get the socket
    :return: a blender NodeSocket for a given type
    """
    nodes = get_material_nodes(blender_material.node_tree, [blender_material], type)
    #TODOSNode : Why checking outputs[0] ? What about alpha for texture node, that is outputs[1] ????
    nodes = [node for node in nodes if check_if_is_linked_to_active_output(node[0].outputs[0], node[1])]
    inputs = sum([[(input, node[1]) for input in node[0].inputs if input.name == name] for node in nodes], [])
    if inputs:
        return NodeSocket(inputs[0][0], inputs[0][1])
    return NodeSocket(None, None)


def get_socket(blender_material: bpy.types.Material, name: str, volume=False):
    """
    For a given material input name, retrieve the corresponding node tree socket.

    :param blender_material: a blender material for which to get the socket
    :param name: the name of the socket
    :return: a blender NodeSocket
    """
    if blender_material.node_tree and blender_material.use_nodes:
        #i = [input for input in blender_material.node_tree.inputs]
        #o = [output for output in blender_material.node_tree.outputs]
        if name == "Emissive":
            # Check for a dedicated Emission node first, it must supersede the newer built-in one
            # because the newer one is always present in all Principled BSDF materials.
            emissive_socket = get_node_socket(blender_material, bpy.types.ShaderNodeEmission, "Color")
            if emissive_socket.socket is not None:
                return emissive_socket
            # If a dedicated Emission node was not found, fall back to the Principled BSDF Emission socket.
            name = "Emission Color"
            type = bpy.types.ShaderNodeBsdfPrincipled
        elif name == "Background":
            type = bpy.types.ShaderNodeBackground
            name = "Color"
        else:
            if volume is False:
                type = bpy.types.ShaderNodeBsdfPrincipled
            else:
                type = bpy.types.ShaderNodeVolumeAbsorption

        return get_node_socket(blender_material, type, name)

    return NodeSocket(None, None)

def get_factor_from_socket(socket, kind):
    """
    For baseColorFactor, metallicFactor, etc.
    Get a constant value from a socket, or a constant value
    from a MULTIPLY node just before the socket.
    kind is either 'RGB' or 'VALUE'.
    """
    fac = get_const_from_socket(socket, kind)
    if fac is not None:
        return fac

    node = previous_node(socket)
    if node.node is not None:
        x1, x2 = None, None
        if kind == 'RGB':
            if node.node.type == 'MIX' and node.node.data_type == "RGBA" and node.node.blend_type == 'MULTIPLY':
                # TODO: handle factor in inputs[0]?
                x1 = get_const_from_socket(NodeSocket(node.node.inputs[6], node.group_path), kind)
                x2 = get_const_from_socket(NodeSocket(node.node.inputs[7], node.group_path), kind)
        if kind == 'VALUE':
            if node.node.type == 'MATH' and node.node.operation == 'MULTIPLY':
                x1 = get_const_from_socket(NodeSocket(node.node.inputs[0], node.group_path), kind)
                x2 = get_const_from_socket(NodeSocket(node.node.inputs[1], node.group_path), kind)
        if x1 is not None and x2 is None: return x1
        if x2 is not None and x1 is None: return x2

    return None

def get_const_from_socket(socket, kind):
    if not socket.socket.is_linked:
        if kind == 'RGB':
            if socket.socket.type != 'RGBA': return None
            return list(socket.socket.default_value)[:3]
        if kind == 'VALUE':
            if socket.socket.type != 'VALUE': return None
            return socket.socket.default_value

    # Handle connection to a constant RGB/Value node
    prev_node = previous_node(socket)
    if prev_node.node is not None:
        if kind == 'RGB' and prev_node.node.type == 'RGB':
            return list(prev_node.node.outputs[0].default_value)[:3]
        if kind == 'VALUE' and prev_node.node.type == 'VALUE':
            return prev_node.node.outputs[0].default_value

    return None


def previous_socket(socket: NodeSocket):
    soc = socket.socket
    group_path = socket.group_path.copy()
    while True:
        if not soc.is_linked:
            return NodeSocket(None, None)

        from_socket = soc.links[0].from_socket

        # If we are entering a node group (from outputs)
        if from_socket.node.type == "GROUP":
            socket_name = from_socket.name
            sockets = [n for n in from_socket.node.node_tree.nodes if n.type == "GROUP_OUTPUT"][0].inputs
            socket = [s for s in sockets if s.name == socket_name][0]
            group_path.append(from_socket.node)
            soc = socket
            continue

        # If we are exiting a node group (from inputs)
        if from_socket.node.type == "GROUP_INPUT":
            socket_name = from_socket.name
            sockets = group_path[-1].inputs
            socket = [s for s in sockets if s.name == socket_name][0]
            group_path = group_path[:-1]
            soc = socket
            continue

        # Skip over reroute nodes
        if from_socket.node.type == 'REROUTE':
            soc = from_socket.node.inputs[0]
            continue

        return NodeSocket(from_socket, group_path)


def previous_node(socket: NodeSocket):
    prev_socket = previous_socket(socket)
    if prev_socket.socket is not None:
        return ShNode(prev_socket.socket.node, prev_socket.group_path)
    return ShNode(None, None)

def get_texture_transform_from_mapping_node(mapping_node):
    if mapping_node.node.vector_type not in ["TEXTURE", "POINT", "VECTOR"]:
        gltf2_io_debug.print_console("WARNING",
            "Skipping exporting texture transform because it had type " +
            mapping_node.node.vector_type + "; recommend using POINT instead"
        )
        return None


    rotation_0, rotation_1 = mapping_node.node.inputs['Rotation'].default_value[0], mapping_node.node.inputs['Rotation'].default_value[1]
    if  rotation_0 or rotation_1:
        # TODO: can we handle this?
        gltf2_io_debug.print_console("WARNING",
            "Skipping exporting texture transform because it had non-zero "
            "rotations in the X/Y direction; only a Z rotation can be exported!"
        )
        return None

    mapping_transform = {}
    if mapping_node.node.vector_type != "VECTOR":
        mapping_transform["offset"] = [mapping_node.node.inputs['Location'].default_value[0], mapping_node.node.inputs['Location'].default_value[1]]
    mapping_transform["rotation"] = mapping_node.node.inputs['Rotation'].default_value[2]
    mapping_transform["scale"] = [mapping_node.node.inputs['Scale'].default_value[0], mapping_node.node.inputs['Scale'].default_value[1]]

    if mapping_node.node.vector_type == "TEXTURE":
        # This means use the inverse of the TRS transform.
        def inverted(mapping_transform):
            offset = mapping_transform["offset"]
            rotation = mapping_transform["rotation"]
            scale = mapping_transform["scale"]

            # Inverse of a TRS is not always a TRS. This function will be right
            # at least when the following don't occur.
            if abs(rotation) > 1e-5 and abs(scale[0] - scale[1]) > 1e-5:
                return None
            if abs(scale[0]) < 1e-5 or abs(scale[1]) < 1e-5:
                return None

            new_offset = Matrix.Rotation(-rotation, 3, 'Z') @ Vector((-offset[0], -offset[1], 1))
            new_offset[0] /= scale[0]; new_offset[1] /= scale[1]
            return {
                "offset": new_offset[0:2],
                "rotation": -rotation,
                "scale": [1/scale[0], 1/scale[1]],
            }

        mapping_transform = inverted(mapping_transform)
        if mapping_transform is None:
            gltf2_io_debug.print_console("WARNING",
                "Skipping exporting texture transform with type TEXTURE because "
                "we couldn't convert it to TRS; recommend using POINT instead"
            )
            return None

    elif mapping_node.node.vector_type == "VECTOR":
        # Vectors don't get translated
        mapping_transform["offset"] = [0, 0]

    texture_transform = texture_transform_blender_to_gltf(mapping_transform)

    if all([component == 0 for component in texture_transform["offset"]]):
        del(texture_transform["offset"])
    if all([component == 1 for component in texture_transform["scale"]]):
        del(texture_transform["scale"])
    if texture_transform["rotation"] == 0:
        del(texture_transform["rotation"])

    if len(texture_transform) == 0:
        return None

    return texture_transform

def check_if_is_linked_to_active_output(shader_socket, group_path):
    for link in shader_socket.links:

        # If we are entering a node group
        if link.to_node.type == "GROUP":
            socket_name = link.to_socket.name
            sockets = [n for n in link.to_node.node_tree.nodes if n.type == "GROUP_INPUT"][0].outputs
            socket = [s for s in sockets if s.name == socket_name][0]
            group_path.append(link.to_node)
            #TODOSNode : Why checking outputs[0] ? What about alpha for texture node, that is outputs[1] ????
            ret = check_if_is_linked_to_active_output(socket, group_path) # recursive until find an output material node
            if ret is True:
                return True
            continue

        # If we are exiting a node group
        if link.to_node.type == "GROUP_OUTPUT":
            socket_name = link.to_socket.name
            sockets = group_path[-1].outputs
            socket = [s for s in sockets if s.name == socket_name][0]
            group_path = group_path[:-1]
            #TODOSNode : Why checking outputs[0] ? What about alpha for texture node, that is outputs[1] ????
            ret = check_if_is_linked_to_active_output(socket, group_path) # recursive until find an output material node
            if ret is True:
                return True
            continue

        if isinstance(link.to_node, bpy.types.ShaderNodeOutputMaterial) and link.to_node.is_active_output is True:
            return True

        if len(link.to_node.outputs) > 0: # ignore non active output, not having output sockets
            #TODOSNode : Why checking outputs[0] ? What about alpha for texture node, that is outputs[1] ????
            ret = check_if_is_linked_to_active_output(link.to_node.outputs[0], group_path) # recursive until find an output material node
            if ret is True:
                return True

    return False

def get_vertex_color_info(color_socket, alpha_socket, export_settings):

    attribute_color = None
    attribute_alpha = None
    attribute_color_type = None
    attribute_alpha_type = None

    # Retrieve Attribute used as vertex color for Color
    if color_socket is not None and color_socket.socket is not None:
        node = previous_node(color_socket)
        if node.node is not None:
            if node.node.type == 'MIX' and node.node.data_type == "RGBA" and node.node.blend_type == 'MULTIPLY':
                use_vc, attribute_color, use_active = get_attribute_name(NodeSocket(node.node.inputs[6], node.group_path), export_settings)
                if use_vc is False:
                    use_vc, attribute_color, use_active = get_attribute_name(NodeSocket(node.node.inputs[7], node.group_path), export_settings)
                if use_vc is True and use_active is True:
                    attribute_color_type = "active"
                elif use_vc is True and use_active is None and attribute_color is not None:
                    attribute_color_type = "name"

    if alpha_socket is not None and alpha_socket.socket is not None:
        node = previous_node(alpha_socket)
        if node.node is not None:
            if node.node.type == 'MIX' and node.node.data_type == "FLOAT" and node.node.blend_type == 'MULTIPLY':
                use_vc, attribute_alpha, use_active = get_attribute_name(NodeSocket(node.node.inputs[2], node.group_path), export_settings)
                if use_vc is False:
                    use_vc, attribute_alpha, use_active = get_attribute_name(NodeSocket(node.node.inputs[3], node.group_path), export_settings)
                if use_vc is True and use_active is True:
                    attribute_alpha_type = "active"
                elif use_vc is True and use_active is None and attribute_alpha is not None:
                    attribute_alpha_type = "name"

    return {"color": attribute_color, "alpha": attribute_alpha, "color_type": attribute_color_type, "alpha_type": attribute_alpha_type}

def get_attribute_name(socket, export_settings):
    node = previous_node(socket)
    if node.node is not None and node.node.type == "ATTRIBUTE" \
            and node.node.attribute_type == "GEOMETRY" \
            and node.node.attribute_name is not None \
            and node.node.attribute_name != "":
        return True, node.node.attribute_name, None
    elif node.node is not None and node.node.type == "ATTRIBUTE" \
            and node.node.attribute_type == "GEOMETRY" \
            and node.node.attribute_name == "":
        return True, None, True

    if node.node is not None and node.node.type == "VERTEX_COLOR" \
            and node.node.layer_name is not None \
            and node.node.layer_name != "":
        return True, node.node.layer_name, None
    elif node.node is not None and node.node.type == "VERTEX_COLOR" \
            and node.node.layer_name == "":
        return True, None, True

    return False, None, None

def detect_anisotropy_nodes(
        anisotropy_socket,
        anisotropy_rotation_socket,
        anisotropy_tangent_socket,
        export_settings):
    """
    Detects if the material uses anisotropy and returns the corresponding data.

    :param anisotropy_socket: the anisotropy socket
    :param anisotropy_rotation_socket: the anisotropy rotation socket
    :param anisotropy_tangent_socket: the anisotropy tangent socket
    :param export_settings: the export settings
    :return: a tuple (is_anisotropy, anisotropy_data)
    """

    if anisotropy_socket.socket is None:
        return False, None
    if anisotropy_rotation_socket.socket is None:
        return False, None
    if anisotropy_tangent_socket.socket is None:
        return False, None

    # Check that tangent is linked to a tangent node, with UVMap as input
    tangent_node = previous_node(anisotropy_tangent_socket)
    if tangent_node.node is None or tangent_node.node.type != "TANGENT":
        return False, None
    if tangent_node.node.direction_type != "UV_MAP":
        return False, None

    # Check that anisotropy is linked to a multiply node
    if not anisotropy_socket.socket.is_linked:
        return False, None
    if not anisotropy_rotation_socket.socket.is_linked:
        return False, None
    if not anisotropy_tangent_socket.socket.is_linked:
        return False, None
    anisotropy_multiply_node = anisotropy_socket.socket.links[0].from_node
    if anisotropy_multiply_node is None or anisotropy_multiply_node.type != "MATH":
        return False, None
    if anisotropy_multiply_node.operation != "MULTIPLY":
        return False, None
    # this multiply node should have the first input linked to separate XYZ, on Z
    if not anisotropy_multiply_node.inputs[0].is_linked:
        return False, None
    separate_xyz_node = anisotropy_multiply_node.inputs[0].links[0].from_node
    if separate_xyz_node is None or separate_xyz_node.type != "SEPXYZ":
        return False, None
    separate_xyz_z_socket = anisotropy_multiply_node.inputs[0].links[0].from_socket
    if separate_xyz_z_socket.name != "Z":
        return False, None
    # This separate XYZ node output should be linked to ArcTan2 node (X on inputs[1], Y on inputs[0])
    if not separate_xyz_node.outputs[0].is_linked:
        return False, None
    arctan2_node = separate_xyz_node.outputs[0].links[0].to_node
    if arctan2_node.type != "MATH":
        return False, None
    if arctan2_node.operation != "ARCTAN2":
        return False, None
    if arctan2_node.inputs[0].links[0].from_socket.name != "Y":
        return False, None
    if arctan2_node.inputs[1].links[0].from_socket.name != "X":
        return False, None
    # This arctan2 node output should be linked to anisotropy rotation (Math add node)
    if not arctan2_node.outputs[0].is_linked:
        return False, None
    anisotropy_rotation_node = arctan2_node.outputs[0].links[0].to_node
    if anisotropy_rotation_node.type != "MATH":
        return False, None
    if anisotropy_rotation_node.operation != "ADD":
        return False, None
    # This anisotropy rotation node should have the output linked to rotation conversion node
    if not anisotropy_rotation_node.outputs[0].is_linked:
        return False, None
    rotation_conversion_node = anisotropy_rotation_node.outputs[0].links[0].to_node
    if rotation_conversion_node.type != "MATH":
        return False, None
    if rotation_conversion_node.operation != "DIVIDE":
        return False, None
    # This rotation conversion node should have the second input value PI
    if abs(rotation_conversion_node.inputs[1].default_value - 6.283185) > 0.0001:
        return False, None
    # This rotation conversion node should have the output linked to anisotropy rotation socket of Principled BSDF
    if not rotation_conversion_node.outputs[0].is_linked:
        return False, None
    if rotation_conversion_node.outputs[0].links[0].to_socket.name != "Anisotropic Rotation":
        return False, None
    if rotation_conversion_node.outputs[0].links[0].to_node.type != "BSDF_PRINCIPLED":
        return False, None

    # Separate XYZ node should have the input linked to anisotropy multiply Add node (for normalization)
    if not separate_xyz_node.inputs[0].is_linked:
        return False, None
    anisotropy_multiply_add_node = separate_xyz_node.inputs[0].links[0].from_node
    if anisotropy_multiply_add_node.type != "VECT_MATH":
        return False, None
    if anisotropy_multiply_add_node.operation != "MULTIPLY_ADD":
        return False, None
    if list(anisotropy_multiply_add_node.inputs[1].default_value) != [2.0, 2.0, 1.0]:
        return False, None
    if list(anisotropy_multiply_add_node.inputs[2].default_value) != [-1.0, -1.0, 0.0]:
        return False, None
    if not anisotropy_multiply_add_node.inputs[0].is_linked:
        return False, None
    # This anisotropy multiply Add node should have the first input linked to a texture node
    anisotropy_texture_node = anisotropy_multiply_add_node.inputs[0].links[0].from_node
    if anisotropy_texture_node.type != "TEX_IMAGE":
        return False, None

    tex_ok = has_image_node_from_socket(NodeSocket(anisotropy_multiply_add_node.inputs[0], anisotropy_socket.group_path), export_settings)
    if tex_ok is False:
        return False, None

    return True, {
        'anisotropyStrength': get_const_from_socket(NodeSocket(anisotropy_multiply_node.inputs[1], anisotropy_socket.group_path), 'VALUE'),
        'anisotropyRotation': get_const_from_socket(NodeSocket(anisotropy_rotation_node.inputs[1], anisotropy_socket.group_path), 'VALUE'),
        'tangent': tangent_node.node.uv_map,
        'tex_socket': NodeSocket(anisotropy_multiply_add_node.inputs[0], anisotropy_socket.group_path),
        }
