"""
 * ***** BEGIN GPL LICENSE BLOCK *****
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License
 * as published by the Free Software Foundation; either version 2
 * of the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software Foundation,
 * Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
 *
 * Contributor(s): Julien Duroure.
 *
 * ***** END GPL LICENSE BLOCK *****
 * This development is done in strong collaboration with Airbus Defence & Space
 """

from .....io.com.gltf2_io_texture import *
import bpy

class KHR_materials_pbrSpecularGlossiness():

    SIMPLE  = 1
    TEXTURE = 2
    TEXTURE_FACTOR = 3

    def __init__(self, json, gltf):
        self.json = json # KHR_materials_pbrSpecularGlossiness json
        self.gltf = gltf # Reference to global glTF instance

        self.diffuse_type   = self.SIMPLE
        self.specgloss_type = self.SIMPLE
        self.vertex_color   = False

        # Default Values
        self.diffuseFactor    = [1.0,1.0,1.0,1.0]
        self.glossinessFactor = 1.0
        self.specularFactor   = [1.0,1.0,1.0]

    def read(self):
        if self.json is None:
            return # will use default values

        if 'diffuseTexture' in self.json.keys():
            self.diffuse_type = self.TEXTURE
            self.diffuseTexture = Texture(self.json['diffuseTexture']['index'], self.gltf.json['textures'][self.json['diffuseTexture']['index']], self.gltf)
            self.diffuseTexture.read()
            self.diffuseTexture.debug_missing()

            if 'texCoord' in self.json['diffuseTexture']:
                self.diffuseTexture.texcoord = int(self.json['diffuseTexture']['texCoord'])
            else:
                self.diffuseTexture.texcoord = 0

        if 'diffuseFactor' in self.json.keys():
            self.diffuseFactor = self.json['diffuseFactor']
            if self.diffuse_type == self.TEXTURE and self.diffuseFactor != [1.0,1.0,1.0,1.0]:
                self.diffuse_type = self.TEXTURE_FACTOR

        if 'specularGlossinessTexture' in self.json.keys():
            self.specgloss_type = self.TEXTURE
            self.specularGlossinessTexture = Texture(self.json['specularGlossinessTexture']['index'], self.gltf.json['textures'][self.json['specularGlossinessTexture']['index']], self.gltf)
            self.specularGlossinessTexture.read()
            self.specularGlossinessTexture.debug_missing()

            if 'texCoord' in self.json['specularGlossinessTexture']:
                self.specularGlossinessTexture.texcoord = int(self.json['specularGlossinessTexture']['texCoord'])
            else:
                self.specularGlossinessTexture.texcoord = 0

        if 'glossinessFactor' in self.json.keys():
            self.glossinessFactor = self.json['glossinessFactor']

        if 'specularFactor' in self.json.keys():
            self.specularFactor = self.json['specularFactor']
            if self.specgloss_type == self.TEXTURE and self.specgloss_type != [1.0,1.0,1.0]:
                self.specgloss_type = self.TEXTURE_FACTOR


    def use_vertex_color(self):
        self.vertex_color = True

    def create_blender(self, mat_name):
        engine = bpy.context.scene.render.engine
        if engine == 'CYCLES':
            self.create_blender_cycles(mat_name)
        else:
            pass #TODO for internal / Eevee in future 2.8

    def create_blender_cycles(self, mat_name):
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

        glossy.inputs[1].default_value = 1 - self.glossinessFactor

        if self.diffuse_type == self.SIMPLE:
            if not self.vertex_color:
                # change input values
                diffuse.inputs[0].default_value = self.diffuseFactor

            else:
                # Create attribute node to get COLOR_0 data
                attribute_node = node_tree.nodes.new('ShaderNodeAttribute')
                attribute_node.attribute_name = 'COLOR_0'
                attribute_node.location = -500,0

                # links
                node_tree.links.new(diffuse.inputs[0], attribute_node.outputs[1])

        elif self.diffuse_type == self.TEXTURE_FACTOR:

            #TODO alpha ?
            if self.vertex_color:
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

            self.diffuseTexture.blender_create()

            # create UV Map / Mapping / Texture nodes / separate & math and combine
            text_node = node_tree.nodes.new('ShaderNodeTexImage')
            text_node.image = bpy.data.images[self.diffuseTexture.image.blender_image_name]
            text_node.location = -1000,500

            combine = node_tree.nodes.new('ShaderNodeCombineRGB')
            combine.location = -250,500

            math_R  = node_tree.nodes.new('ShaderNodeMath')
            math_R.location = -500, 750
            math_R.operation = 'MULTIPLY'
            math_R.inputs[1].default_value = self.diffuseFactor[0]

            math_G  = node_tree.nodes.new('ShaderNodeMath')
            math_G.location = -500, 500
            math_G.operation = 'MULTIPLY'
            math_G.inputs[1].default_value = self.diffuseFactor[1]

            math_B  = node_tree.nodes.new('ShaderNodeMath')
            math_B.location = -500, 250
            math_B.operation = 'MULTIPLY'
            math_B.inputs[1].default_value = self.diffuseFactor[2]

            separate = node_tree.nodes.new('ShaderNodeSeparateRGB')
            separate.location = -750, 500

            mapping = node_tree.nodes.new('ShaderNodeMapping')
            mapping.location = -1500, 500

            uvmap = node_tree.nodes.new('ShaderNodeUVMap')
            uvmap.location = -2000, 500
            uvmap["gltf2_texcoord"] = self.diffuseTexture.texcoord # Set custom flag to retrieve TexCoord
            # UV Map will be set after object/UVMap creation

            # Create links
            if self.vertex_color:
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

        elif self.diffuse_type == self.TEXTURE:

            self.diffuseTexture.blender_create()

            #TODO alpha ?
            if self.vertex_color:
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
            text_node.image = bpy.data.images[self.diffuseTexture.image.blender_image_name]
            if self.vertex_color:
                text_node.location = -2000,500
            else:
                text_node.location = -500,500

            mapping = node_tree.nodes.new('ShaderNodeMapping')
            if self.vertex_color:
                mapping.location = -2500,500
            else:
                mapping.location = -1500,500

            uvmap = node_tree.nodes.new('ShaderNodeUVMap')
            if self.vertex_color:
                uvmap.location = -3000,500
            else:
                uvmap.location = -2000,500
            uvmap["gltf2_texcoord"] = self.diffuseTexture.texcoord # Set custom flag to retrieve TexCoord
            # UV Map will be set after object/UVMap creation

            # Create links
            if self.vertex_color:
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


        if self.specgloss_type == self.SIMPLE:

            combine = node_tree.nodes.new('ShaderNodeCombineRGB')
            combine.inputs[0].default_value = self.specularFactor[0]
            combine.inputs[1].default_value = self.specularFactor[1]
            combine.inputs[2].default_value = self.specularFactor[2]

            # links
            node_tree.links.new(glossy.inputs[0], combine.outputs[0])

        elif self.specgloss_type == self.TEXTURE:
            self.specularGlossinessTexture.blender_create()
            spec_text = node_tree.nodes.new('ShaderNodeTexImage')
            spec_text.image = bpy.data.images[self.specularGlossinessTexture.image.blender_image_name]
            spec_text.color_space = 'NONE'
            spec_text.location = -500,0

            spec_mapping = node_tree.nodes.new('ShaderNodeMapping')
            spec_mapping.location = -1000,0

            spec_uvmap = node_tree.nodes.new('ShaderNodeUVMap')
            spec_uvmap.location = -1500,0
            spec_uvmap["gltf2_texcoord"] = self.specularGlossinessTexture.texcoord # Set custom flag to retrieve TexCoord

            # links
            node_tree.links.new(glossy.inputs[0], spec_text.outputs[0])
            node_tree.links.new(mix.inputs[0], spec_text.outputs[1])

            node_tree.links.new(spec_mapping.inputs[0], spec_uvmap.outputs[0])
            node_tree.links.new(spec_text.inputs[0], spec_mapping.outputs[0])

        elif self.specgloss_type == self.TEXTURE_FACTOR:

            self.specularGlossinessTexture.blender_create()

            spec_text = node_tree.nodes.new('ShaderNodeTexImage')
            spec_text.image = bpy.data.images[self.specularGlossinessTexture.image.blender_image_name]
            spec_text.color_space = 'NONE'
            spec_text.location = -1000,0

            spec_math     = node_tree.nodes.new('ShaderNodeMath')
            spec_math.operation = 'MULTIPLY'
            spec_math.inputs[0].default_value = self.glossinessFactor
            spec_math.location = -250,100

            spec_mapping = node_tree.nodes.new('ShaderNodeMapping')
            spec_mapping.location = -1000,0

            spec_uvmap = node_tree.nodes.new('ShaderNodeUVMap')
            spec_uvmap.location = -1500,0
            spec_uvmap["gltf2_texcoord"] = self.specularGlossinessTexture.texcoord # Set custom flag to retrieve TexCoord


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


    def debug_missing(self):
        if self.json is None:
            return
        keys = [

                ]

        for key in self.json.keys():
            if key not in keys:
                self.gltf.log.debug("KHR_materials_pbrSpecularGlossiness MISSING " + key)
