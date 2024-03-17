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
from ...blender.com.gltf2_blender_conversion import texture_transform_blender_to_gltf
from ...io.com import gltf2_io_debug
from ..com.gltf2_blender_material_helpers import get_gltf_node_name, get_gltf_node_old_name
from .material import gltf2_blender_search_node_tree

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
