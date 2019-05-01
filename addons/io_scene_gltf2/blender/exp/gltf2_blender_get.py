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


def get_socket_or_texture_slot(blender_material: bpy.types.Material, name: str):
    """
    For a given material input name, retrieve the corresponding node tree socket or blender render texture slot.

    :param blender_material: a blender material for which to get the socket/slot
    :param name: the name of the socket/slot
    :return: either a blender NodeSocket, if the material is a node tree or a blender Texture otherwise
    """
    if blender_material.node_tree and blender_material.use_nodes:
        #i = [input for input in blender_material.node_tree.inputs]
        #o = [output for output in blender_material.node_tree.outputs]
        if name == "Emissive":
            type = bpy.types.ShaderNodeEmission
            name = "Color"
        elif name == "Background":
            type = bpy.types.ShaderNodeBackground
            name = "Color"
        else:
            type = bpy.types.ShaderNodeBsdfPrincipled
        nodes = [n for n in blender_material.node_tree.nodes if isinstance(n, type)]
        inputs = sum([[input for input in node.inputs if input.name == name] for node in nodes], [])
        if inputs:
            return inputs[0]
    elif bpy.app.version < (2, 80, 0):  # blender 2.8 removed texture_slots
        if name != 'Base Color':
            return None

        gltf2_io_debug.print_console("WARNING", "You are using texture slots, which are deprecated. In future versions"
                                                "of the glTF exporter they will not be supported any more")

        for blender_texture_slot in blender_material.texture_slots:
            if blender_texture_slot and blender_texture_slot.texture and \
                    blender_texture_slot.texture.type == 'IMAGE' and \
                    blender_texture_slot.texture.image is not None:
                #
                # Base color texture
                #
                if blender_texture_slot.use_map_color_diffuse:
                    return blender_texture_slot

    return None


def get_socket_or_texture_slot_old(blender_material: bpy.types.Material, name: str):
    """
    For a given material input name, retrieve the corresponding node tree socket in the special glTF node group.

    :param blender_material: a blender material for which to get the socket/slot
    :param name: the name of the socket/slot
    :return: either a blender NodeSocket, if the material is a node tree or a blender Texture otherwise
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


def get_texture_transform_from_texture_node(texture_node):
    if not isinstance(texture_node, bpy.types.ShaderNodeTexImage):
        return None

    mapping_socket = texture_node.inputs["Vector"]
    if len(mapping_socket.links) == 0:
        return None

    mapping_node = mapping_socket.links[0].from_node
    if not isinstance(mapping_node, bpy.types.ShaderNodeMapping):
        return None

    if mapping_node.vector_type not in ["TEXTURE", "POINT", "VECTOR"]:
        gltf2_io_debug.print_console("WARNING",
            "Skipping exporting texture transform because it had type " +
            mapping_node.vector_type + "; recommend using POINT instead"
        )
        return None

    if mapping_node.rotation[0] or mapping_node.rotation[1]:
        # TODO: can we handle this?
        gltf2_io_debug.print_console("WARNING",
            "Skipping exporting texture transform because it had non-zero "
            "rotations in the X/Y direction; only a Z rotation can be exported!"
        )
        return None

    mapping_transform = {}
    mapping_transform["offset"] = [mapping_node.translation[0], mapping_node.translation[1]]
    mapping_transform["rotation"] = mapping_node.rotation[2]
    mapping_transform["scale"] = [mapping_node.scale[0], mapping_node.scale[1]]

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

            if bpy.app.version >= (2, 80, 0):
                new_offset = Matrix.Rotation(-rotation, 3, 'Z') @ Vector((-offset[0], -offset[1], 1))
            else:
                new_offset = Matrix.Rotation(-rotation, 3, 'Z') * Vector((-offset[0], -offset[1], 1))
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
