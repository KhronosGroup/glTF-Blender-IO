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

# Get compatibility at export with old files


def get_gltf_node_old_name():
    return "glTF Settings"

# Old group name


def get_gltf_old_group_node_name():
    return "glTF Metallic Roughness"


def get_gltf_node_name():
    return "glTF Material Output"


def create_settings_group(name):
    gltf_node_group = bpy.data.node_groups.new(name, 'ShaderNodeTree')
    gltf_node_group.interface.new_socket("Occlusion", socket_type="NodeSocketFloat")
    thicknessFactor = gltf_node_group.interface.new_socket("Thickness", socket_type="NodeSocketFloat", )
    thicknessFactor.default_value = 0.0
    gltf_node_group.nodes.new('NodeGroupOutput')
    gltf_node_group_input = gltf_node_group.nodes.new('NodeGroupInput')
    gltf_node_group_input.location = -200, 0
    return gltf_node_group
