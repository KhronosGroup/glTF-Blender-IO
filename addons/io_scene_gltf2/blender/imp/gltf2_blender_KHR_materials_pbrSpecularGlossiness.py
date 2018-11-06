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
from .gltf2_blender_texture import *

class BlenderKHR_materials_pbrSpecularGlossiness():


    @staticmethod
    def create(gltf, pbrSG, mat_name, vertex_color):
        engine = bpy.context.scene.render.engine
        if engine == 'CYCLES':
            BlenderKHR_materials_pbrSpecularGlossiness.create_nodetree(gltf, pbrSG, mat_name, vertex_color)
        else:
            pass #TODO for internal / Eevee in future 2.8

    @staticmethod
    def create_nodetree(gltf, pbrSG, mat_name, vertex_color):
        material = bpy.data.materials[mat_name]
        material.use_nodes = True
        node_tree = material.node_tree

        # delete all nodes except output
        for node in list(node_tree.nodes):
            if not node.type == 'OUTPUT_MATERIAL':
                node_tree.nodes.remove(node)

        output_node = node_tree.nodes[0]
        output_node.location = 1000,0

        # create PBR node
        diffuse    = node_tree.nodes.new('ShaderNodeBsdfDiffuse')
        diffuse.location = 0,0
        glossy     = node_tree.nodes.new('ShaderNodeBsdfGlossy')
        glossy.location  = 0,100
        mix        = node_tree.nodes.new('ShaderNodeMixShader')
        mix.location     = 500,0

        glossy.inputs[1].default_value = 1 - pbrSG['glossinessFactor']

        if pbrSG['diffuse_type'] == gltf.SIMPLE:
            if not vertex_color:
                # change input values
                diffuse.inputs[0].default_value = pbrSG['diffuseFactor']

            else:
                # Create attribute node to get COLOR_0 data
                attribute_node = node_tree.nodes.new('ShaderNodeAttribute')
                attribute_node.attribute_name = 'COLOR_0'
                attribute_node.location = -500,0

                # links
                node_tree.links.new(diffuse.inputs[0], attribute_node.outputs[1])

        elif pbrSG['diffuse_type'] == gltf.TEXTURE_FACTOR:

            #TODO alpha ?
            if vertex_color:
                # TODO tree locations
                # Create attribute / separate / math nodes
                attribute_node = node_tree.nodes.new('ShaderNodeAttribute')
                attribute_node.attribute_name = 'COLOR_0'

                separate_vertex_color = node_tree.nodes.new('ShaderNodeSeparateRGB')
                math_vc_R = node_tree.nodes.new('ShaderNodeMath')
                math_vc_R.operation = 'MULTIPLY'

                math_vc_G = node_tree.nodes.new('ShaderNodeMath')
                math_vc_G.operation = 'MULTIPLY'

                math_vc_B = node_tree.nodes.new('ShaderNodeMath')
                math_vc_B.operation = 'MULTIPLY'

            BlenderTextureInfo.create(gltf, pbrSG['diffuseTexture']['index'])

            # create UV Map / Mapping / Texture nodes / separate & math and combine
            text_node = node_tree.nodes.new('ShaderNodeTexImage')
            text_node.image = bpy.data.images[gltf.data.images[gltf.data.textures[pbrSG['diffuseTexture']['index']].source].blender_image_name]
            text_node.location = -1000,500

            combine = node_tree.nodes.new('ShaderNodeCombineRGB')
            combine.location = -250,500

            math_R  = node_tree.nodes.new('ShaderNodeMath')
            math_R.location = -500, 750
            math_R.operation = 'MULTIPLY'
            math_R.inputs[1].default_value = pbrSG['diffuseFactor'][0]

            math_G  = node_tree.nodes.new('ShaderNodeMath')
            math_G.location = -500, 500
            math_G.operation = 'MULTIPLY'
            math_G.inputs[1].default_value = pbrSG['diffuseFactor'][1]

            math_B  = node_tree.nodes.new('ShaderNodeMath')
            math_B.location = -500, 250
            math_B.operation = 'MULTIPLY'
            math_B.inputs[1].default_value = pbrSG['diffuseFactor'][2]

            separate = node_tree.nodes.new('ShaderNodeSeparateRGB')
            separate.location = -750, 500

            mapping = node_tree.nodes.new('ShaderNodeMapping')
            mapping.location = -1500, 500

            uvmap = node_tree.nodes.new('ShaderNodeUVMap')
            uvmap.location = -2000, 500
            if 'texCoord' in pbrSG['diffuseTexture'].keys():
                uvmap["gltf2_texcoord"] = pbrSG['diffuseTexture']['texCoord'] # Set custom flag to retrieve TexCoord
            else:
                uvmap["gltf2_texcoord"] = 0 #TODO: set in precompute instead of here?
            # UV Map will be set after object/UVMap creation

            # Create links
            if vertex_color:
                node_tree.links.new(separate_vertex_color.inputs[0], attribute_node.outputs[0])
                node_tree.links.new(math_vc_R.inputs[1], separate_vertex_color.outputs[0])
                node_tree.links.new(math_vc_G.inputs[1], separate_vertex_color.outputs[1])
                node_tree.links.new(math_vc_B.inputs[1], separate_vertex_color.outputs[2])
                node_tree.links.new(math_vc_R.inputs[0], math_R.outputs[0])
                node_tree.links.new(math_vc_G.inputs[0], math_G.outputs[0])
                node_tree.links.new(math_vc_B.inputs[0], math_B.outputs[0])
                node_tree.links.new(combine.inputs[0], math_vc_R.outputs[0])
                node_tree.links.new(combine.inputs[1], math_vc_G.outputs[0])
                node_tree.links.new(combine.inputs[2], math_vc_B.outputs[0])

            else:
                node_tree.links.new(combine.inputs[0], math_R.outputs[0])
                node_tree.links.new(combine.inputs[1], math_G.outputs[0])
                node_tree.links.new(combine.inputs[2], math_B.outputs[0])

            # Common for both mode (non vertex color / vertex color)
            node_tree.links.new(math_R.inputs[0], separate.outputs[0])
            node_tree.links.new(math_G.inputs[0], separate.outputs[1])
            node_tree.links.new(math_B.inputs[0], separate.outputs[2])

            node_tree.links.new(mapping.inputs[0], uvmap.outputs[0])
            node_tree.links.new(text_node.inputs[0], mapping.outputs[0])
            node_tree.links.new(separate.inputs[0], text_node.outputs[0])


            node_tree.links.new(diffuse.inputs[0], combine.outputs[0])

        elif pbrSG['diffuse_type'] == gltf.TEXTURE:

            BlenderTextureInfo.create(gltf, pbrSG['diffuseTexture']['index'])

            #TODO alpha ?
            if vertex_color:
                # Create attribute / separate / math nodes
                attribute_node = node_tree.nodes.new('ShaderNodeAttribute')
                attribute_node.attribute_name = 'COLOR_0'
                attribute_node.location = -2000,250

                separate_vertex_color = node_tree.nodes.new('ShaderNodeSeparateRGB')
                separate_vertex_color.location = -1500, 250

                math_vc_R = node_tree.nodes.new('ShaderNodeMath')
                math_vc_R.operation = 'MULTIPLY'
                math_vc_R.location = -1000,750

                math_vc_G = node_tree.nodes.new('ShaderNodeMath')
                math_vc_G.operation = 'MULTIPLY'
                math_vc_G.location = -1000,500

                math_vc_B = node_tree.nodes.new('ShaderNodeMath')
                math_vc_B.operation = 'MULTIPLY'
                math_vc_B.location = -1000,250


                combine = node_tree.nodes.new('ShaderNodeCombineRGB')
                combine.location = -500,500

                separate = node_tree.nodes.new('ShaderNodeSeparateRGB')
                separate.location = -1500, 500

            # create UV Map / Mapping / Texture nodes / separate & math and combine
            text_node = node_tree.nodes.new('ShaderNodeTexImage')
            text_node.image = bpy.data.images[gltf.data.images[gltf.data.textures[pbrSG['diffuseTexture']['index']].source].blender_image_name]
            if vertex_color:
                text_node.location = -2000,500
            else:
                text_node.location = -500,500

            mapping = node_tree.nodes.new('ShaderNodeMapping')
            if vertex_color:
                mapping.location = -2500,500
            else:
                mapping.location = -1500,500

            uvmap = node_tree.nodes.new('ShaderNodeUVMap')
            if vertex_color:
                uvmap.location = -3000,500
            else:
                uvmap.location = -2000,500
            if 'texCoord' in pbrSG['diffuseTexture'].keys():
                uvmap["gltf2_texcoord"] = pbrSG['diffuseTexture']['texCoord'] # Set custom flag to retrieve TexCoord
            else:
                uvmap["gltf2_texcoord"] = 0 #TODO: set in precompute instead of here?
            # UV Map will be set after object/UVMap creation

            # Create links
            if vertex_color:
                node_tree.links.new(separate_vertex_color.inputs[0], attribute_node.outputs[0])

                node_tree.links.new(math_vc_R.inputs[1], separate_vertex_color.outputs[0])
                node_tree.links.new(math_vc_G.inputs[1], separate_vertex_color.outputs[1])
                node_tree.links.new(math_vc_B.inputs[1], separate_vertex_color.outputs[2])

                node_tree.links.new(combine.inputs[0], math_vc_R.outputs[0])
                node_tree.links.new(combine.inputs[1], math_vc_G.outputs[0])
                node_tree.links.new(combine.inputs[2], math_vc_B.outputs[0])

                node_tree.links.new(separate.inputs[0], text_node.outputs[0])

                node_tree.links.new(principled.inputs[0], combine.outputs[0])

                node_tree.links.new(math_vc_R.inputs[0], separate.outputs[0])
                node_tree.links.new(math_vc_G.inputs[0], separate.outputs[1])
                node_tree.links.new(math_vc_B.inputs[0], separate.outputs[2])

            else:
                node_tree.links.new(diffuse.inputs[0], text_node.outputs[0])

            # Common for both mode (non vertex color / vertex color)

            node_tree.links.new(mapping.inputs[0], uvmap.outputs[0])
            node_tree.links.new(text_node.inputs[0], mapping.outputs[0])


        if pbrSG['specgloss_type'] == gltf.SIMPLE:

            combine = node_tree.nodes.new('ShaderNodeCombineRGB')
            combine.inputs[0].default_value = pbrSG['specularFactor'][0]
            combine.inputs[1].default_value = pbrSG['specularFactor'][1]
            combine.inputs[2].default_value = pbrSG['specularFactor'][2]

            # links
            node_tree.links.new(glossy.inputs[0], combine.outputs[0])

        elif pbrSG['specgloss_type'] == gltf.TEXTURE:
            BlenderTextureInfo.create(gltf, pbrSG['specularGlossinessTexture']['index'])
            spec_text = node_tree.nodes.new('ShaderNodeTexImage')
            spec_text.image = bpy.data.images[gltf.data.images[gltf.data.textures[pbrSG['specularGlossinessTexture']['index']].source].blender_image_name]
            spec_text.color_space = 'NONE'
            spec_text.location = -500,0

            spec_mapping = node_tree.nodes.new('ShaderNodeMapping')
            spec_mapping.location = -1000,0

            spec_uvmap = node_tree.nodes.new('ShaderNodeUVMap')
            spec_uvmap.location = -1500,0
            if 'texCoord' in pbrSG['specularGlossinessTexture'].keys():
                spec_uvmap["gltf2_texcoord"] = pbrSG['specularGlossinessTexture']['texCoord'] # Set custom flag to retrieve TexCoord
            else:
                spec_uvmap["gltf2_texcoord"] = 0 #TODO: set in precompute instead of here?

            # links
            node_tree.links.new(glossy.inputs[0], spec_text.outputs[0])
            node_tree.links.new(mix.inputs[0], spec_text.outputs[1])

            node_tree.links.new(spec_mapping.inputs[0], spec_uvmap.outputs[0])
            node_tree.links.new(spec_text.inputs[0], spec_mapping.outputs[0])

        elif pbrSG['specgloss_type'] == gltf.TEXTURE_FACTOR:

            BlenderTextureInfo.create(gltf, pbrSG['specularGlossinessTexture']['index'])

            spec_text = node_tree.nodes.new('ShaderNodeTexImage')
            spec_text.image = bpy.data.images[gltf.data.images[gltf.data.textures[pbrSG['specularGlossinessTexture']['index']].source].blender_image_name]
            spec_text.color_space = 'NONE'
            spec_text.location = -1000,0

            spec_math     = node_tree.nodes.new('ShaderNodeMath')
            spec_math.operation = 'MULTIPLY'
            spec_math.inputs[0].default_value = pbrSG['glossinessFactor']
            spec_math.location = -250,100

            spec_mapping = node_tree.nodes.new('ShaderNodeMapping')
            spec_mapping.location = -1000,0

            spec_uvmap = node_tree.nodes.new('ShaderNodeUVMap')
            spec_uvmap.location = -1500,0
            if 'texCoord' in pbrSG['specularGlossinessTexture'].keys():
                spec_uvmap["gltf2_texcoord"] = pbrSG['specularGlossinessTexture']['texCoord'] # Set custom flag to retrieve TexCoord
            else:
                spec_uvmap["gltf2_texcoord"] = 0 #TODO: set in precompute instead of here?


            # links

            node_tree.links.new(spec_math.inputs[1], spec_text.outputs[0])
            node_tree.links.new(mix.inputs[0], spec_text.outputs[1])
            node_tree.links.new(glossy.inputs[1], spec_math.outputs[0])
            node_tree.links.new(glossy.inputs[0], spec_text.outputs[0])

            node_tree.links.new(spec_mapping.inputs[0], spec_uvmap.outputs[0])
            node_tree.links.new(spec_text.inputs[0], spec_mapping.outputs[0])

        # link node to output
        node_tree.links.new(mix.inputs[2], diffuse.outputs[0])
        node_tree.links.new(mix.inputs[1], glossy.outputs[0])
        node_tree.links.new(output_node.inputs[0], mix.outputs[0])
