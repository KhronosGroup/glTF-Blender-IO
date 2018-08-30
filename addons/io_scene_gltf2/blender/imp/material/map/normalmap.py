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

from .map import *
from ...gltf2_blender_texture import *

class NormalMap(Map):
    def __init__(self, json, factor, gltf):
        super(NormalMap, self).__init__(json, factor, gltf)

    def create_blender(self, mat_name):
        engine = bpy.context.scene.render.engine
        if engine == 'CYCLES':
            self.create_blender_cycles(mat_name)
        else:
            pass #TODO for internal / Eevee in future 2.8

    def create_blender_cycles(self, mat_name):
        material = bpy.data.materials[mat_name]
        node_tree = material.node_tree

        BlenderTexture.create(self.texture)

        # retrieve principled node and output node
        principled = None
        diffuse   = None
        glossy    = None
        if len([node for node in node_tree.nodes if node.type == "BSDF_PRINCIPLED"]) != 0:
            principled = [node for node in node_tree.nodes if node.type == "BSDF_PRINCIPLED"][0]
        else:
            #No principled, we are probably coming from extension
            diffuse = [node for node in node_tree.nodes if node.type == "BSDF_DIFFUSE"][0]
            glossy  = [node for node in node_tree.nodes if node.type == "BSDF_GLOSSY"][0]

        # add nodes
        mapping = node_tree.nodes.new('ShaderNodeMapping')
        mapping.location = -1000,-500
        uvmap = node_tree.nodes.new('ShaderNodeUVMap')
        uvmap.location = -1500, -500
        uvmap["gltf2_texcoord"] = self.texCoord # Set custom flag to retrieve TexCoord

        text  = node_tree.nodes.new('ShaderNodeTexImage')
        text.image = bpy.data.images[self.texture.image.blender_image_name]
        text.color_space = 'NONE'
        text.location = -500, -500

        normalmap_node = node_tree.nodes.new('ShaderNodeNormalMap')
        normalmap_node.location = -250,-500


        # create links
        node_tree.links.new(mapping.inputs[0], uvmap.outputs[0])
        node_tree.links.new(text.inputs[0], mapping.outputs[0])
        node_tree.links.new(normalmap_node.inputs[1], text.outputs[0])

        # following  links will modify PBR node tree
        if principled:
            node_tree.links.new(principled.inputs[17], normalmap_node.outputs[0])
        if diffuse:
            node_tree.links.new(diffuse.inputs[2], normalmap_node.outputs[0])
        if glossy:
            node_tree.links.new(glossy.inputs[2], normalmap_node.outputs[0])
