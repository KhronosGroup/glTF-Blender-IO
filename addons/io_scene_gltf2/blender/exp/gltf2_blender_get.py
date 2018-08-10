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

from ...io.com.gltf2_io_debug import *

from ...io.exp.gltf2_io_get import *

#
# Globals
#

#
# Functions
#


def get_texture_index_by_node_group(export_settings, glTF, name, shader_node_group):
    """
    Return the texture index in the glTF array.
    """

    if shader_node_group is None:
        return -1
    
    if not isinstance(shader_node_group, bpy.types.ShaderNodeGroup) and not isinstance(shader_node_group, bpy.types.ShaderNodeBsdfPrincipled):
        return -1

    if shader_node_group.inputs.get(name) is None:
        return -1
    
    if len(shader_node_group.inputs[name].links) == 0:
        return -1
    
    from_node = shader_node_group.inputs[name].links[0].from_node
    
    #

    if not isinstance(from_node, bpy.types.ShaderNodeTexImage):
        return -1

    if from_node.image is None or from_node.image.size[0] == 0 or from_node.image.size[1] == 0:
        return -1

    return get_texture_index(glTF, from_node.image.name)


def get_texcoord_index_by_node_group(glTF, name, shader_node_group):
    """
    Return the texture coordinate index, if assigend and used.
    """

    if shader_node_group is None:
        return 0
    
    if not isinstance(shader_node_group, bpy.types.ShaderNodeGroup) and not isinstance(shader_node_group, bpy.types.ShaderNodeBsdfPrincipled):
        return 0

    if shader_node_group.inputs.get(name) is None:
        return 0
    
    if len(shader_node_group.inputs[name].links) == 0:
        return 0
    
    from_node = shader_node_group.inputs[name].links[0].from_node
    
    #

    if not isinstance(from_node, bpy.types.ShaderNodeTexImage):
        return 0
    
    #
    
    if len(from_node.inputs['Vector'].links) == 0:
        return 0

    input_node = from_node.inputs['Vector'].links[0].from_node

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
