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

#
# Imports
#

import bpy

from ...io.com.gltf2_io_debug import *

from ...io.exp.gltf2_io_get import *

#
# Globals
#

#
# Functions
#


def get_animation_target(action_group: bpy.types.ActionGroup):
    return action_group.channels[0].data_path.split('.')[-1]


def get_socket_or_texture_slot(blender_material: bpy.types.Material, name: str):
    """
    For a given material input name, retrieve the corresponding node tree socket or blender render texture slot
    :param blender_material: a blender material for which to get the socket/slot
    :param name: the name of the socket/slot
    :return: either a blender NodeSocket, if the material is a node tree or a blender Texture otherwise
    """
    if blender_material.node_tree and blender_material.use_nodes:
        if name == "Emissive":
            # Emissive is a special case as  the input node in the 'Emission' shader node is named 'Color' and only the
            # output is named 'Emission'
            links = [link for link in blender_material.node_tree.links if link.from_socket.name == 'Emission']
            if not links:
                return None
            return links[0].to_socket
        links = [link for link in blender_material.node_tree.links if link.to_socket.name == name]
        if not links:
            return None
        return links[0].to_socket
    elif bpy.app.version < (2, 80, 0): # blender 2.8 removed texture_slots
        if name != 'Base Color':
            return None

        for blender_texture_slot in blender_material.texture_slots:
            if blender_texture_slot and blender_texture_slot.texture and blender_texture_slot.texture.type == 'IMAGE' and blender_texture_slot.texture.image is not None:
                #
                # Base color texture
                #
                if blender_texture_slot.use_map_color_diffuse:
                    return blender_texture_slot

        return None
    else:
        return None

def find_shader_image_from_shader_socket(shader_socket, max_hops=10):
    """
     returns the first ShaderNodeTexImage found in the path from the socket
    """
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

def get_shader_add_to_shader_node(shader_node):

    if shader_node is None:
        return None

    if len(shader_node.outputs['BSDF'].links) == 0:
        return None

    to_node = shader_node.outputs['BSDF'].links[0].to_node

    if not isinstance(to_node, bpy.types.ShaderNodeAddShader):
        return None

    return to_node

#

def get_shader_emission_from_shader_add(shader_add):

    if shader_add is None:
        return None

    if not isinstance(shader_add, bpy.types.ShaderNodeAddShader):
        return None

    from_node = None

    for input in shader_add.inputs:

        if len(input.links) == 0:
            continue

        from_node = input.links[0].from_node

        if isinstance(from_node, bpy.types.ShaderNodeEmission):
            break

    return from_node


def get_shader_mapping_from_shader_image(shader_image):

    if shader_image is None:
        return None

    if not isinstance(shader_image, bpy.types.ShaderNodeTexImage):
        return None

    if shader_image.inputs.get('Vector') is None:
        return None

    if len(shader_image.inputs['Vector'].links) == 0:
        return None

    from_node = shader_image.inputs['Vector'].links[0].from_node

    #

    if not isinstance(from_node, bpy.types.ShaderNodeMapping):
        return None

    return from_node

def get_image_material_usage_to_socket(shader_image, socket_name):
    if shader_image is None:
        return -1

    if not isinstance(shader_image, bpy.types.ShaderNodeTexImage):
        return -2

    if shader_image.outputs.get('Color') is None:
        return -3

    if len(shader_image.outputs.get('Color').links) == 0:
        return -4

    for img_link in shader_image.outputs.get('Color').links:
        separate_rgb = img_link.to_node

        if not isinstance(separate_rgb, bpy.types.ShaderNodeSeparateRGB):
            continue

        for i, channel in enumerate("RGB"):
            if separate_rgb.outputs.get(channel) is None:
                continue
            for link in separate_rgb.outputs.get(channel).links:
                if socket_name == link.to_socket.name:
                    return i

    return -6

def get_emission_node_from_lamp_output_node(lamp_node):
    if lamp_node is None:
        return None

    if not isinstance(lamp_node, bpy.types.ShaderNodeOutputLamp):
        return None

    if lamp_node.inputs.get('Surface') is None:
        return None

    if len(lamp_node.inputs.get('Surface').links) == 0:
        return None

    from_node = lamp_node.inputs.get('Surface').links[0].from_node
    if isinstance(from_node, bpy.types.ShaderNodeEmission):
        return from_node

    return None


def get_ligth_falloff_node_from_emission_node(emission_node, type):
    if emission_node is None:
        return None

    if not isinstance(emission_node, bpy.types.ShaderNodeEmission):
        return None

    if emission_node.inputs.get('Strength') is None:
        return None

    if len(emission_node.inputs.get('Strength').links) == 0:
        return None

    from_node = emission_node.inputs.get('Strength').links[0].from_node
    if not isinstance(from_node, bpy.types.ShaderNodeLightFalloff):
        return None

    if from_node.outputs.get(type) is None:
        return None

    if len(from_node.outputs.get(type).links) == 0:
        return None

    if emission_node != from_node.outputs.get(type).links[0].to_node:
        return None

    return from_node


def get_shader_image_from_shader_node(name, shader_node):

    if shader_node is None:
        return None

    if not isinstance(shader_node, bpy.types.ShaderNodeGroup) and not isinstance(shader_node, bpy.types.ShaderNodeBsdfPrincipled) and not isinstance(shader_node, bpy.types.ShaderNodeEmission):
        return None

    if shader_node.inputs.get(name) is None:
        return None

    if len(shader_node.inputs[name].links) == 0:
        return None

    from_node = shader_node.inputs[name].links[0].from_node

    #

    if isinstance(from_node, bpy.types.ShaderNodeNormalMap):

        name = 'Color'

        if len(from_node.inputs[name].links) == 0:
            return None

        from_node = from_node.inputs[name].links[0].from_node

    #

    if not isinstance(from_node, bpy.types.ShaderNodeTexImage):
        return None

    return from_node


def get_texture_index_from_shader_node(export_settings, glTF, name, shader_node):
    """
    Return the texture index in the glTF array.
    """

    from_node = get_shader_image_from_shader_node(name, shader_node)

    if from_node is None:
        return -1

    #

    if from_node.image is None or from_node.image.size[0] == 0 or from_node.image.size[1] == 0:
        return -1

    return get_texture_index(glTF, from_node.image.name)

def get_texture_index_from_export_settings(export_settings, name):
    """
    Return the texture index in the glTF array
    """

def get_texcoord_index_from_shader_node(glTF, name, shader_node):
    """
    Return the texture coordinate index, if assigend and used.
    """

    from_node = get_shader_image_from_shader_node(name, shader_node)

    if from_node is None:
        return 0

    #

    if len(from_node.inputs['Vector'].links) == 0:
        return 0

    input_node = from_node.inputs['Vector'].links[0].from_node

    #

    if isinstance(input_node, bpy.types.ShaderNodeMapping):

        if len(input_node.inputs['Vector'].links) == 0:
            return 0

        input_node = input_node.inputs['Vector'].links[0].from_node

    #

    if not isinstance(input_node, bpy.types.ShaderNodeUVMap):
        return 0

    if input_node.uv_map == '':
        return 0

    #

    # Try to gather map index.
    for blender_mesh in bpy.data.meshes:
        texCoordIndex = blender_mesh.uv_textures.find(input_node.uv_map)
        if texCoordIndex >= 0:
            return texCoordIndex

    return 0


def get_image_uri(export_settings, blender_image):
    """
    Return the final URI depending on a filepath.
    """

    file_format = get_image_format(export_settings, blender_image)
    extension = '.jpg' if file_format == 'JPEG' else '.png'

    return get_image_name(blender_image.name) + extension


def get_image_format(export_settings, blender_image):
    """
    Return the final output format of the given image. Only PNG and JPEG are
    supported as outputs - all other formats must be converted.
    """
    if blender_image.file_format in ['PNG', 'JPEG']:
        return blender_image.file_format

    use_alpha = export_settings['filtered_images_use_alpha'].get(blender_image.name)

    return 'PNG' if use_alpha else 'JPEG'


def get_node(data_path):
    """
    Return Blender node on a given Blender data path.
    """

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


def get_data_path(data_path):
    """
    Return Blender data path.
    """

    index = data_path.rfind('.')

    if index == -1:
        return data_path

    return data_path[(index + 1):]
