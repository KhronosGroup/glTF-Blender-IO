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

from ...io.common.gltf2_io_debug import *

#
# Globals
#

#
# Functions
#

def get_material_index(glTF, name):
    """
    Return the material index in the glTF array.
    """

    if name is None:
        return -1

    if glTF.get('materials') is None:
        return -1

    index = 0
    for material in glTF['materials']:
        if material['name'] == name:
            return index
        
        index += 1

    return -1


def get_mesh_index(glTF, name):
    """
    Return the mesh index in the glTF array.
    """

    if glTF.get('meshes') is None:
        return -1

    index = 0
    for mesh in glTF['meshes']:
        if mesh['name'] == name:
            return index
        
        index += 1

    return -1


def get_skin_index(glTF, name, index_offset):
    """
    Return the skin index in the glTF array.
    """

    if glTF.get('skins') is None:
        return -1
    
    skeleton = get_node_index(glTF, name)

    index = 0
    for skin in glTF['skins']:
        if skin['skeleton'] == skeleton:
            return index + index_offset
        
        index += 1

    return -1


def get_camera_index(glTF, name):
    """
    Return the camera index in the glTF array.
    """

    if glTF.get('cameras') is None:
        return -1

    index = 0
    for camera in glTF['cameras']:
        if camera['name'] == name:
            return index
        
        index += 1

    return -1


def get_light_index(glTF, name):
    """
    Return the light index in the glTF array.
    """

    if glTF.get('extensions') is None:
        return -1
    
    extensions = glTF['extensions']
        
    if extensions.get('KHR_lights') is None:
        return -1
    
    khr_lights = extensions['KHR_lights']

    if khr_lights.get('lights') is None:
        return -1

    lights = khr_lights['lights']

    index = 0
    for light in lights:
        if light['name'] == name:
            return index
        
        index += 1

    return -1


def get_node_index(glTF, name):
    """
    Return the node index in the glTF array.
    """

    if glTF.get('nodes') is None:
        return -1

    index = 0
    for node in glTF['nodes']:
        if node['name'] == name:
            return index
        
        index += 1

    return -1


def get_scene_index(glTF, name):
    """
    Return the scene index in the glTF array.
    """

    if glTF.get('scenes') is None:
        return -1

    index = 0
    for scene in glTF['scenes']:
        if scene['name'] == name:
            return index
        
        index += 1

    return -1


def get_image_index(glTF, image):
    """
    Return the image index in the glTF array.
    """

    if glTF.get('images') is None:
        return -1

    image_name = get_image_name(image)

    for index, current_image in enumerate(glTF['images']):
        if image_name == current_image['name']:
            return index

    return -1


def get_scalar(default_value, init_value = 0.0):
    """
    Return scalar with a given default/fallback value.
    """

    return_value = init_value

    if default_value is None:
        return return_value

    return_value = default_value 

    return return_value


def get_vec2(default_value, init_value = [0.0, 0.0]):
    """
    Return vec2 with a given default/fallback value.
    """

    return_value = init_value

    if default_value is None or len(default_value) < 2:
        return return_value

    index = 0
    for number in default_value:
        return_value[index] = number 

        index += 1
        if index == 2:
            return return_value

    return return_value


def get_vec3(default_value, init_value = [0.0, 0.0, 0.0]):
    """
    Return vec3 with a given default/fallback value.
    """

    return_value = init_value

    if default_value is None or len(default_value) < 3:
        return return_value

    index = 0
    for number in default_value:
        return_value[index] = number 

        index += 1
        if index == 3:
            return return_value

    return return_value


def get_vec4(default_value, init_value = [0.0, 0.0, 0.0, 1.0]):
    """
    Return vec4 with a given default/fallback value.
    """

    return_value = init_value

    if default_value is None or len(default_value) < 4:
        return return_value

    index = 0
    for number in default_value:
        return_value[index] = number 

        index += 1
        if index == 4:
            return return_value

    return return_value


def get_index(elements, name):
    """
    Return index of a glTF element by a given name.
    """

    if elements is None or name is None:
        return -1
    
    index = 0
    for element in elements:
        if element.get('name') is None:
            return -1
    
        if element['name'] == name:
            return index
        
        index += 1
    
    return -1

