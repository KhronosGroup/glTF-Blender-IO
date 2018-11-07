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
from .gltf2_blender_texture import BlenderTextureInfo
from ..com.gltf2_blender_material_helpers import get_preoutput_node_output


class BlenderEmissiveMap():

    @staticmethod
    def create(gltf, material_idx):
        engine = bpy.context.scene.render.engine
        if engine in ['CYCLES', 'BLENDER_EEVEE']:
            BlenderEmissiveMap.create_nodetree(gltf, material_idx)

    def create_nodetree(gltf, material_idx):

        pymaterial = gltf.data.materials[material_idx]

        material = bpy.data.materials[pymaterial.blender_material]
        node_tree = material.node_tree

        BlenderTextureInfo.create(gltf, pymaterial.emissive_texture.index)

        # check if there is some emssive_factor on material
        if pymaterial.emissive_factor is None:
            pymaterial.emissive_factor = [1.0, 1.0, 1.0]

        # retrieve principled node and output node
        principled = get_preoutput_node_output(node_tree)
        output = [node for node in node_tree.nodes if node.type == 'OUTPUT_MATERIAL'][0]

        # add nodes
        emit = node_tree.nodes.new('ShaderNodeEmission')
        emit.location = 0, 1000
        if pymaterial.emissive_factor != [1.0, 1.0, 1.0]:
            separate = node_tree.nodes.new('ShaderNodeSeparateRGB')
            separate.location = -750, 1000
            combine = node_tree.nodes.new('ShaderNodeCombineRGB')
            combine.location = -250, 1000
        mapping = node_tree.nodes.new('ShaderNodeMapping')
        mapping.location = -1500, 1000
        uvmap = node_tree.nodes.new('ShaderNodeUVMap')
        uvmap.location = -2000, 1000
        if pymaterial.emissive_texture.tex_coord is not None:
            uvmap["gltf2_texcoord"] = pymaterial.emissive_texture.tex_coord  # Set custom flag to retrieve TexCoord
        else:
            uvmap["gltf2_texcoord"] = 0  # TODO: set in precompute instead of here?

        text = node_tree.nodes.new('ShaderNodeTexImage')
        text.image = bpy.data.images[gltf.data.images[
            gltf.data.textures[pymaterial.emissive_texture.index].source
        ].blender_image_name]
        text.label = 'EMISSIVE'
        text.location = -1000, 1000
        add = node_tree.nodes.new('ShaderNodeAddShader')
        add.location = 500, 500

        if pymaterial.emissive_factor != [1.0, 1.0, 1.0]:
            math_R = node_tree.nodes.new('ShaderNodeMath')
            math_R.location = -500, 1500
            math_R.operation = 'MULTIPLY'
            math_R.inputs[1].default_value = pymaterial.emissive_factor[0]

            math_G = node_tree.nodes.new('ShaderNodeMath')
            math_G.location = -500, 1250
            math_G.operation = 'MULTIPLY'
            math_G.inputs[1].default_value = pymaterial.emissive_factor[1]

            math_B = node_tree.nodes.new('ShaderNodeMath')
            math_B.location = -500, 1000
            math_B.operation = 'MULTIPLY'
            math_B.inputs[1].default_value = pymaterial.emissive_factor[2]

        # create links
        node_tree.links.new(mapping.inputs[0], uvmap.outputs[0])
        node_tree.links.new(text.inputs[0], mapping.outputs[0])
        if pymaterial.emissive_factor != [1.0, 1.0, 1.0]:
            node_tree.links.new(separate.inputs[0], text.outputs[0])
            node_tree.links.new(math_R.inputs[0], separate.outputs[0])
            node_tree.links.new(math_G.inputs[0], separate.outputs[1])
            node_tree.links.new(math_B.inputs[0], separate.outputs[2])
            node_tree.links.new(combine.inputs[0], math_R.outputs[0])
            node_tree.links.new(combine.inputs[1], math_G.outputs[0])
            node_tree.links.new(combine.inputs[2], math_B.outputs[0])
            node_tree.links.new(emit.inputs[0], combine.outputs[0])
        else:
            node_tree.links.new(emit.inputs[0], text.outputs[0])

        # following  links will modify PBR node tree
        node_tree.links.new(add.inputs[0], emit.outputs[0])
        node_tree.links.new(add.inputs[1], principled)
        node_tree.links.new(output.inputs[0], add.outputs[0])
