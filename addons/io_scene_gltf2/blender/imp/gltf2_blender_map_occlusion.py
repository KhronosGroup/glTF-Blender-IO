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
from .gltf2_blender_image import BlenderImage
from .gltf2_blender_material_utils import make_texture_block
from ..com.gltf2_blender_material_helpers import get_gltf_node_name


class BlenderOcclusionMap():
    """Blender Occlusion map."""
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("%s should not be instantiated" % cls)

    @staticmethod
    def create(gltf, material_idx, vertex_color):
        """Occlusion map creation."""
        engine = bpy.context.scene.render.engine
        if engine in ['CYCLES', 'BLENDER_EEVEE']:
            BlenderOcclusionMap.create_nodetree(gltf, material_idx, vertex_color)

    def create_nodetree(gltf, material_idx, vertex_color):
        """Nodetree creation."""
        pymaterial = gltf.data.materials[material_idx]
        pytexture = gltf.data.textures[pymaterial.occlusion_texture.index]

        material = bpy.data.materials[pymaterial.blender_material[vertex_color]]
        node_tree = material.node_tree

        # Pack texture. Occlusion is calculated from Cycles or Eevee, so do nothing
        blender_image_name = None
        if pytexture.source is not None:
            BlenderImage.create(gltf, pytexture.source)
            pyimg = gltf.data.images[pytexture.source]
            blender_image_name = pyimg.blender_image_name
            bpy.data.images[blender_image_name].use_fake_user = True

        # Create a fake node group for exporter
        gltf_node_group_name = get_gltf_node_name()
        if gltf_node_group_name in bpy.data.node_groups:
            gltf_node_group = bpy.data.node_groups[gltf_node_group_name]
        else:
            # Create a new node group
            gltf_node_group = bpy.data.node_groups.new(gltf_node_group_name, 'ShaderNodeTree')
            gltf_node_group.inputs.new("NodeSocketFloat", "Occlusion")
            gltf_node_group.nodes.new('NodeGroupOutput')
            gltf_node_group_input = gltf_node_group.nodes.new('NodeGroupInput')
            gltf_node_group_input.location = -200, 0

        # Set the node group inside material node tree
        ao_node = node_tree.nodes.new('ShaderNodeGroup')
        ao_node.node_tree = gltf_node_group
        ao_node.location = 0, 200

        # Check if the texture node already exists (if used by other parameter metal / roughness)
        found = False
        if blender_image_name is not None:
            for node in [node for node in node_tree.nodes if node.type == "TEX_IMAGE"]:
                if node.image and blender_image_name == node.image.name:
                    # This is our image !
                    # Retrieve separate node if found
                    if node.outputs['Color'].is_linked:
                        for link in node.outputs['Color'].links:
                            if link.to_node.type == 'SEPRGB':
                                node_tree.links.new(ao_node.inputs[0], link.to_node.outputs[0])
                                found = True
                                break

                    if found:
                        break

        if not found:
            # Need to create the texture node & separate node
            separate = node_tree.nodes.new('ShaderNodeSeparateRGB')
            text = make_texture_block(
                gltf,
                node_tree,
                pymaterial.occlusion_texture,
                location=(0, 0),
                label='OCCLUSION',
                name='occlusionTexture',
            )

            # Links
            node_tree.links.new(separate.inputs[0], text.outputs[0])
            node_tree.links.new(ao_node.inputs[0], separate.outputs[0])
