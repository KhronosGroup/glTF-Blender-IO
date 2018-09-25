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
 """

import bpy
from .gltf2_blender_texture import *

class BlenderEmissiveMap():

    @staticmethod
    def create(gltf, material_idx):
        engine = bpy.context.scene.render.engine
        if engine == 'CYCLES':
            BlenderEmissiveMap.create_cycles(gltf, material_idx)
        else:
            pass #TODO for internal / Eevee in future 2.8

    def create_cycles(gltf, material_idx):

        pymaterial = gltf.data.materials[material_idx]

        material = bpy.data.materials[pymaterial.blender_material]
        node_tree = material.node_tree

        BlenderTextureInfo.create(gltf, pymaterial.emissive_texture.index)

        # retrieve principled node and output node
        if len([node for node in node_tree.nodes if node.type == "BSDF_PRINCIPLED"]) != 0:
            fix = [node for node in node_tree.nodes if node.type == "BSDF_PRINCIPLED"][0]
        else:
            # No principled, we are coming from an extenstion, probably
            fix = [node for node in node_tree.nodes if node.type == "MIX_SHADER"][0]

        output = [node for node in node_tree.nodes if node.type == 'OUTPUT_MATERIAL'][0]

        # add nodes
        emit = node_tree.nodes.new('ShaderNodeEmission')
        emit.location = 0,1000
        if pymaterial.emissive_factor != [1.0,1.0,1.0]:
            separate = node_tree.nodes.new('ShaderNodeSeparateRGB')
            separate.location = -750, 1000
            combine = node_tree.nodes.new('ShaderNodeCombineRGB')
            combine.location = -250, 1000
        mapping = node_tree.nodes.new('ShaderNodeMapping')
        mapping.location = -1500, 1000
        uvmap = node_tree.nodes.new('ShaderNodeUVMap')
        uvmap.location = -2000,1000
        if pymaterial.emissive_texture.tex_coord is not None:
            uvmap["gltf2_texcoord"] = pymaterial.emissive_texture.tex_coord # Set custom flag to retrieve TexCoord
        else:
            uvmap["gltf2_texcoord"] = 0 #TODO: set in precompute instead of here?

        text  = node_tree.nodes.new('ShaderNodeTexImage')
        text.image = bpy.data.images[gltf.data.images[gltf.data.textures[pymaterial.emissive_texture.index].source].blender_image_name]
        text.location = -1000,1000
        add = node_tree.nodes.new('ShaderNodeAddShader')
        add.location = 500,500

        if pymaterial.emissive_factor != [1.0,1.0,1.0]:
            math_R  = node_tree.nodes.new('ShaderNodeMath')
            math_R.location = -500, 1500
            math_R.operation = 'MULTIPLY'
            math_R.inputs[1].default_value = pymaterial.emissive_factor[0]

            math_G  = node_tree.nodes.new('ShaderNodeMath')
            math_G.location = -500, 1250
            math_G.operation = 'MULTIPLY'
            math_G.inputs[1].default_value = pymaterial.emissive_factor[1]

            math_B  = node_tree.nodes.new('ShaderNodeMath')
            math_B.location = -500, 1000
            math_B.operation = 'MULTIPLY'
            math_B.inputs[1].default_value = pymaterial.emissive_factor[2]

        # create links
        node_tree.links.new(mapping.inputs[0], uvmap.outputs[0])
        node_tree.links.new(text.inputs[0], mapping.outputs[0])
        if pymaterial.emissive_factor != [1.0,1.0,1.0]:
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
        node_tree.links.new(add.inputs[1], fix.outputs[0])
        node_tree.links.new(output.inputs[0], add.outputs[0])
