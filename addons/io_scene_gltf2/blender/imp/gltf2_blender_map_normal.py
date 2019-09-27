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


class BlenderNormalMap():
    """Blender Normal map."""
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("%s should not be instantiated" % cls)

    @staticmethod
    def create(gltf, material_idx, vertex_color):
        """Creation of Normal map."""
        engine = bpy.context.scene.render.engine
        if engine in ['CYCLES', 'BLENDER_EEVEE']:
            BlenderNormalMap.create_nodetree(gltf, material_idx, vertex_color)

    def create_nodetree(gltf, material_idx, vertex_color):
        """Creation of Nodetree."""
        pymaterial = gltf.data.materials[material_idx]

        material = bpy.data.materials[pymaterial.blender_material[vertex_color]]
        node_tree = material.node_tree

        # retrieve principled node and output node
        principled = None
        diffuse = None
        glossy = None
        if len([node for node in node_tree.nodes if node.type == "BSDF_PRINCIPLED"]) != 0:
            principled = [node for node in node_tree.nodes if node.type == "BSDF_PRINCIPLED"][0]
        else:
            # No principled, we are probably coming from extension
            diffuse = [node for node in node_tree.nodes if node.type == "BSDF_DIFFUSE"][0]
            glossy = [node for node in node_tree.nodes if node.type == "BSDF_GLOSSY"][0]

        # add nodes
        text = make_texture_block(
            gltf,
            node_tree,
            pymaterial.normal_texture,
            location=(-500, -500),
            label='NORMALMAP',
            name='normalTexture',
            colorspace='NONE',
        )

        normalmap_node = node_tree.nodes.new('ShaderNodeNormalMap')
        normalmap_node.location = -250, -500

        tex_info = pymaterial.normal_texture
        texcoord_idx = tex_info.tex_coord or 0
        if tex_info.extensions and 'KHR_texture_transform' in tex_info.extensions:
            if 'texCoord' in tex_info.extensions['KHR_texture_transform']:
                texcoord_idx = tex_info.extensions['KHR_texture_transform']['texCoord']

        normalmap_node.uv_map = 'TEXCOORD_%d' % texcoord_idx

        # Set strength
        if pymaterial.normal_texture.scale is not None:
            normalmap_node.inputs[0].default_value = pymaterial.normal_texture.scale
        else:
            normalmap_node.inputs[0].default_value = 1.0 # Default

        # create links
        node_tree.links.new(normalmap_node.inputs[1], text.outputs[0])

        # following links will modify PBR node tree
        if principled:
            if bpy.app.version < (2, 80, 0):
                node_tree.links.new(principled.inputs[17], normalmap_node.outputs[0])
            else:
                node_tree.links.new(principled.inputs[19], normalmap_node.outputs[0])
        if diffuse:
            node_tree.links.new(diffuse.inputs[2], normalmap_node.outputs[0])
        if glossy:
            node_tree.links.new(glossy.inputs[2], normalmap_node.outputs[0])
