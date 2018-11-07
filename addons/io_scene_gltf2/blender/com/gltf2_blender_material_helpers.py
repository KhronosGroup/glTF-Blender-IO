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


def get_output_node(node_tree):
    output = [node for node in node_tree.nodes if node.type == 'OUTPUT_MATERIAL'][0]
    return output


def get_output_surface_input(node_tree):
    output_node = get_output_node(node_tree)
    return output_node.inputs['Surface']


def get_diffuse_texture(node_tree):
    for node in node_tree.nodes:
        print(node.name)
        if node.label == 'BASE COLOR':
            return node

    return None


def get_preoutput_node_output(node_tree):
    output_node = get_output_node(node_tree)
    preoutput_node = output_node.inputs['Surface'].links[0].from_node

    # Pre output node is Principled BSDF or any BSDF => BSDF
    if 'BSDF' in preoutput_node.type:
        return preoutput_node.outputs['BSDF']
    elif 'SHADER' in preoutput_node.type:
        return preoutput_node.outputs['Shader']
    else:
        print(preoutput_node.type)


def get_base_color_node(node_tree):
    """Returns the last node of the diffuse block."""
    for node in node_tree.nodes:
        if node.label == 'BASE COLOR':
            return node

    return None
