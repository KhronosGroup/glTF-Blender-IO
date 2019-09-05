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
from .gltf2_blender_texture import BlenderTextureInfo
from ..com.gltf2_blender_conversion import texture_transform_gltf_to_blender


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

        BlenderTextureInfo.create(gltf, pymaterial.normal_texture)

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
        mapping = node_tree.nodes.new('ShaderNodeMapping')
        mapping.location = -1000, -500
        uvmap = node_tree.nodes.new('ShaderNodeUVMap')
        uvmap.location = -1500, -500
        if pymaterial.normal_texture.tex_coord is not None:
            uvmap["gltf2_texcoord"] = pymaterial.normal_texture.tex_coord  # Set custom flag to retrieve TexCoord
        else:
            uvmap["gltf2_texcoord"] = 0  # TODO set in pre_compute instead of here

        text = node_tree.nodes.new('ShaderNodeTexImage')
        if gltf.data.images[
            gltf.data.textures[pymaterial.normal_texture.index].source
        ].blender_image_name is not None:
            text.image = bpy.data.images[gltf.data.images[
                gltf.data.textures[pymaterial.normal_texture.index].source
            ].blender_image_name]
        text.label = 'NORMALMAP'
        if bpy.app.version < (2, 80, 0):
            text.color_space = 'NONE'
        else:
            if text.image:
                text.image.colorspace_settings.is_data = True
        text.location = -500, -500
        if text.image is not None: # Sometimes images can't be retrieved (bad gltf file ...)
            tex_transform = text.image['tex_transform'][str(pymaterial.normal_texture.index)]
            mapping.translation[0] = texture_transform_gltf_to_blender(tex_transform)['offset'][0]
            mapping.translation[1] = texture_transform_gltf_to_blender(tex_transform)['offset'][1]
            mapping.rotation[2] = texture_transform_gltf_to_blender(tex_transform)['rotation']
            mapping.scale[0] = texture_transform_gltf_to_blender(tex_transform)['scale'][0]
            mapping.scale[1] = texture_transform_gltf_to_blender(tex_transform)['scale'][1]

        normalmap_node = node_tree.nodes.new('ShaderNodeNormalMap')
        normalmap_node.location = -250, -500
        if pymaterial.normal_texture.tex_coord is not None:
            # Set custom flag to retrieve TexCoord
            normalmap_node["gltf2_texcoord"] = pymaterial.normal_texture.tex_coord
        else:
            normalmap_node["gltf2_texcoord"] = 0  # TODO set in pre_compute instead of here

        # Set strength
        if pymaterial.normal_texture.scale is not None:
            normalmap_node.inputs[0].default_value = pymaterial.normal_texture.scale
        else:
            normalmap_node.inputs[0].default_value = 1.0 # Default

        # create links
        node_tree.links.new(mapping.inputs[0], uvmap.outputs[0])
        node_tree.links.new(text.inputs[0], mapping.outputs[0])
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
