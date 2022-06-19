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

def get_gltf_node_name():
    return "glTF Settings"

def create_settings_group(name):
    gltf_node_group = bpy.data.node_groups.new(name, 'ShaderNodeTree')
    gltf_node_group.inputs.new("NodeSocketFloat", "Occlusion")
    thicknessFactor  = gltf_node_group.inputs.new("NodeSocketFloat", "Thickness")
    thicknessFactor.default_value = 1.0
    gltf_node_group.nodes.new('NodeGroupOutput')
    gltf_node_group_input = gltf_node_group.nodes.new('NodeGroupInput')
    gltf_node_group_input.location = -200, 0
    return gltf_node_group

def get_gltf_pbr_non_converted_name():
    return "glTF Non Converted BPR Extensions"

def create_gltf_pbr_non_converted_group(name):
    gltf_node_group = bpy.data.node_groups.new(name, 'ShaderNodeTree')

    specularTexture = gltf_node_group.inputs.new("NodeSocketFloat", "specularTexture")
    specularTexture.default_value = 1.0
    specularColorTexture = gltf_node_group.inputs.new("NodeSocketColor", "specularColorTexture")
    specularColorTexture.default_value = [1.0,1.0,1.0,1.0]

    sheenColorTexture = gltf_node_group.inputs.new("NodeSocketColor", "sheenColorTexture")
    sheenColorTexture.default_value = [0.0,0.0,0.0,1.0]
    sheenRoughnessTexture = gltf_node_group.inputs.new("NodeSocketFloat", "sheenRoughnessTexture")
    specularTexture.default_value = 0.0

    gltf_node_group.nodes.new('NodeGroupOutput')
    gltf_node_group_input = gltf_node_group.nodes.new('NodeGroupInput')
    gltf_node_group_input.location = -400, 0
    return gltf_node_group    