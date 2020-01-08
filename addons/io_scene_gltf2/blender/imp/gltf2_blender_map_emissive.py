# Copyright 2018-2019 The glTF-Blender-IO authors.
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
from .gltf2_blender_material_utils import make_texture_block
from ..com.gltf2_blender_material_helpers import get_preoutput_node_output


class BlenderEmissiveMap():
    """Blender Emissive Map."""
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("%s should not be instantiated" % cls)

    @staticmethod
    def create(gltf, material_idx, vertex_color, factor_only=False):
        """Create emissive map."""
        engine = bpy.context.scene.render.engine
        if engine in ['CYCLES', 'BLENDER_EEVEE']:
            BlenderEmissiveMap.create_nodetree(gltf, material_idx, vertex_color, factor_only)

    def create_nodetree(gltf, material_idx, vertex_color, factor_only=False):
        """Create node tree."""
        pymaterial = gltf.data.materials[material_idx]

        material = bpy.data.materials[pymaterial.blender_material[vertex_color]]
        node_tree = material.node_tree

        # check if there is some emissive_factor on material
        if pymaterial.emissive_factor is None:
            # Default in glTF specification is 0/0/0 --> No emission
            pymaterial.emissive_factor = [0.0, 0.0, 0.0]

        # retrieve principled node and output node
        principled = get_preoutput_node_output(node_tree)
        output = [node for node in node_tree.nodes if node.type == 'OUTPUT_MATERIAL'][0]

        # add nodes
        emit = node_tree.nodes.new('ShaderNodeEmission')
        emit.location = 0, 1000

        if factor_only is False:
            if pymaterial.emissive_factor != [1.0, 1.0, 1.0]:
                mult_node = node_tree.nodes.new('ShaderNodeMixRGB')
                mult_node.blend_type = 'MULTIPLY'
                mult_node.inputs['Fac'].default_value = 1.0
                mult_node.location = -500, 1000
                mult_node.inputs['Color2'].default_value = [
                                                            pymaterial.emissive_factor[0],
                                                            pymaterial.emissive_factor[1],
                                                            pymaterial.emissive_factor[2],
                                                            1.0,
                                                            ]
            text = make_texture_block(
                gltf,
                node_tree,
                pymaterial.emissive_texture,
                location=(-1000, 1000),
                label='EMISSIVE',
                name='emissiveTexture',
            )

            # create links
            if pymaterial.emissive_factor != [1.0, 1.0, 1.0]:
                node_tree.links.new(mult_node.inputs[1], text.outputs[0])
                node_tree.links.new(emit.inputs[0], mult_node.outputs[0])
            else:
                node_tree.links.new(emit.inputs[0], text.outputs[0])

        else:
            emissive_color = pymaterial.emissive_factor + [1] # add alpha
            emit.inputs[0].default_value = emissive_color


        add = node_tree.nodes.new('ShaderNodeAddShader')
        add.location = 500, 500

        # following links will modify PBR node tree
        node_tree.links.new(add.inputs[0], emit.outputs[0])
        node_tree.links.new(add.inputs[1], principled)
        node_tree.links.new(output.inputs[0], add.outputs[0])
