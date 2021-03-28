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

import bpy
from mathutils import Vector, Matrix

from ..com.gltf2_blender_material_helpers import get_gltf_node_name
from ...blender.com.gltf2_blender_conversion import texture_transform_blender_to_gltf
from io_scene_gltf2.io.com import gltf2_io_debug


def get_animation_target(action_group: bpy.types.ActionGroup):
    return action_group.channels[0].data_path.split('.')[-1]


def get_object_from_datapath(blender_object, data_path: str):
    if "." in data_path:
        # gives us: ('modifiers["Subsurf"]', 'levels')
        path_prop, path_attr = data_path.rsplit(".", 1)

        # same as: prop = obj.modifiers["Subsurf"]
        if path_attr in ["rotation", "scale", "location",
                         "rotation_axis_angle", "rotation_euler", "rotation_quaternion"]:
            prop = blender_object.path_resolve(path_prop)
        else:
            prop = blender_object.path_resolve(data_path)
    else:
        prop = blender_object
        # single attribute such as name, location... etc
        # path_attr = data_path

    return prop


def get_socket(blender_material: bpy.types.Material, name: str):
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
            type = bpy.types.ShaderNodeEmission
            name = "Color"
            nodes = [n for n in blender_material.node_tree.nodes if isinstance(n, type) and not n.mute]
            nodes = [node for node in nodes if check_if_is_linked_to_active_output(node.outputs[0])]
            inputs = sum([[input for input in node.inputs if input.name == name] for node in nodes], [])
            if inputs:
                return inputs[0]
            # If a dedicated Emission node was not found, fall back to the Principled BSDF Emission socket.
            name = "Emission"
            type = bpy.types.ShaderNodeBsdfPrincipled
        elif name == "Background":
            type = bpy.types.ShaderNodeBackground
            name = "Color"
        else:
            type = bpy.types.ShaderNodeBsdfPrincipled
        nodes = [n for n in blender_material.node_tree.nodes if isinstance(n, type) and not n.mute]
        nodes = [node for node in nodes if check_if_is_linked_to_active_output(node.outputs[0])]
        inputs = sum([[input for input in node.inputs if input.name == name] for node in nodes], [])
        if inputs:
            return inputs[0]

    return None


def get_socket_old(blender_material: bpy.types.Material, name: str):
    """
    For a given material input name, retrieve the corresponding node tree socket in the special glTF node group.

    :param blender_material: a blender material for which to get the socket
    :param name: the name of the socket
    :return: a blender NodeSocket
    """
    gltf_node_group_name = get_gltf_node_name().lower()
    if blender_material.node_tree and blender_material.use_nodes:
        nodes = [n for n in blender_material.node_tree.nodes if \
            isinstance(n, bpy.types.ShaderNodeGroup) and \
            (n.node_tree.name.startswith('glTF Metallic Roughness') or n.node_tree.name.lower() == gltf_node_group_name)]
        inputs = sum([[input for input in node.inputs if input.name == name] for node in nodes], [])
        if inputs:
            return inputs[0]

    return None

def check_if_is_linked_to_active_output(shader_socket):
    for link in shader_socket.links:
        if isinstance(link.to_node, bpy.types.ShaderNodeOutputMaterial) and link.to_node.is_active_output is True:
            return True

        if len(link.to_node.outputs) > 0: # ignore non active output, not having output sockets
            ret = check_if_is_linked_to_active_output(link.to_node.outputs[0]) # recursive until find an output material node
            if ret is True:
                return True

    return False

def find_shader_image_from_shader_socket(shader_socket, max_hops=10):
    """Find any ShaderNodeTexImage in the path from the socket."""
    if shader_socket is None:
        return None

    if max_hops <= 0:
        return None

    for link in shader_socket.links:
        if isinstance(link.from_node, bpy.types.ShaderNodeTexImage):
            return link.from_node

        for socket in link.from_node.inputs.values():
            image = find_shader_image_from_shader_socket(shader_socket=socket, max_hops=max_hops - 1)
            if image is not None:
                return image

    return None


def get_texture_transform_from_mapping_node(mapping_node):
    if mapping_node.vector_type not in ["TEXTURE", "POINT", "VECTOR"]:
        gltf2_io_debug.print_console("WARNING",
            "Skipping exporting texture transform because it had type " +
            mapping_node.vector_type + "; recommend using POINT instead"
        )
        return None


    rotation_0, rotation_1 = mapping_node.inputs['Rotation'].default_value[0], mapping_node.inputs['Rotation'].default_value[1]
    if  rotation_0 or rotation_1:
        # TODO: can we handle this?
        gltf2_io_debug.print_console("WARNING",
            "Skipping exporting texture transform because it had non-zero "
            "rotations in the X/Y direction; only a Z rotation can be exported!"
        )
        return None

    mapping_transform = {}
    mapping_transform["offset"] = [mapping_node.inputs['Location'].default_value[0], mapping_node.inputs['Location'].default_value[1]]
    mapping_transform["rotation"] = mapping_node.inputs['Rotation'].default_value[2]
    mapping_transform["scale"] = [mapping_node.inputs['Scale'].default_value[0], mapping_node.inputs['Scale'].default_value[1]]

    if mapping_node.vector_type == "TEXTURE":
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

    elif mapping_node.vector_type == "VECTOR":
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


def get_node(data_path):
    """Return Blender node on a given Blender data path."""
    if data_path is None:
        return None

    index = data_path.find("[\"")
    if (index == -1):
        return None

    node_name = data_path[(index + 2):]

    index = node_name.find("\"")
    if (index == -1):
        return None

    return node_name[:(index)]


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
    if node is not None:
        x1, x2 = None, None
        if kind == 'RGB':
            if node.type == 'MIX_RGB' and node.blend_type == 'MULTIPLY':
                # TODO: handle factor in inputs[0]?
                x1 = get_const_from_socket(node.inputs[1], kind)
                x2 = get_const_from_socket(node.inputs[2], kind)
        if kind == 'VALUE':
            if node.type == 'MATH' and node.operation == 'MULTIPLY':
                x1 = get_const_from_socket(node.inputs[0], kind)
                x2 = get_const_from_socket(node.inputs[1], kind)
        if x1 is not None and x2 is None: return x1
        if x2 is not None and x1 is None: return x2

    return None


def get_const_from_socket(socket, kind):
    if not socket.is_linked:
        if kind == 'RGB':
            if socket.type != 'RGBA': return None
            return list(socket.default_value)[:3]
        if kind == 'VALUE':
            if socket.type != 'VALUE': return None
            return socket.default_value

    # Handle connection to a constant RGB/Value node
    prev_node = previous_node(socket)
    if prev_node is not None:
        if kind == 'RGB' and prev_node.type == 'RGB':
            return list(prev_node.outputs[0].default_value)[:3]
        if kind == 'VALUE' and prev_node.type == 'VALUE':
            return prev_node.outputs[0].default_value

    return None


def previous_socket(socket):
    while True:
        if not socket.is_linked:
            return None

        from_socket = socket.links[0].from_socket

        # Skip over reroute nodes
        if from_socket.node.type == 'REROUTE':
            socket = from_socket.node.inputs[0]
            continue

        return from_socket


def previous_node(socket):
    prev_socket = previous_socket(socket)
    if prev_socket is not None:
        return prev_socket.node
    return None
