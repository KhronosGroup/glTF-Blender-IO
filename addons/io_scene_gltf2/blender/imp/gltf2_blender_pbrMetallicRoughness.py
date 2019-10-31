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


class BlenderPbr():
    """Blender Pbr."""
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("%s should not be instantiated" % cls)

    def create(gltf, pypbr, mat_name, vertex_color):
        """Pbr creation."""
        engine = bpy.context.scene.render.engine
        if engine in ['CYCLES', 'BLENDER_EEVEE']:
            BlenderPbr.create_nodetree(gltf, pypbr, mat_name, vertex_color)

    def create_nodetree(gltf, pypbr, mat_name, vertex_color, nodetype='principled'):
        """Nodetree creation."""
        material = bpy.data.materials[mat_name]
        material.use_nodes = True
        node_tree = material.node_tree

        # If there is no diffuse texture, but only a color, wihtout
        # vertex_color, we set this color in viewport color
        if pypbr.color_type == gltf.SIMPLE and not vertex_color:
            if bpy.app.version < (2, 80, 0):
                material.diffuse_color = pypbr.base_color_factor[:3]
            else:
                # Manage some change in beta version on 20190129
                if len(material.diffuse_color) == 3:
                    material.diffuse_color = pypbr.base_color_factor[:3]
                else:
                    material.diffuse_color = pypbr.base_color_factor

        # delete all nodes except output
        for node in list(node_tree.nodes):
            if not node.type == 'OUTPUT_MATERIAL':
                node_tree.nodes.remove(node)

        output_node = node_tree.nodes[0]
        output_node.location = 1250, 0

        # create Main node
        if nodetype == "principled":
            main_node = node_tree.nodes.new('ShaderNodeBsdfPrincipled')
            main_node.location = 0, 0
        elif nodetype == "unlit":
            main_node = node_tree.nodes.new('ShaderNodeEmission')
            main_node.location = 750, -300

        if pypbr.color_type == gltf.SIMPLE:

            if not vertex_color:

                # change input values
                main_node.inputs[0].default_value = pypbr.base_color_factor
                if nodetype == "principled":
                    # TODO : currently set metallic & specular in same way
                    main_node.inputs[5].default_value = pypbr.metallic_factor
                    main_node.inputs[7].default_value = pypbr.roughness_factor

            else:
                # Create attribute node to get COLOR_0 data
                if bpy.app.version < (2, 81, 8):
                    attribute_node = node_tree.nodes.new('ShaderNodeAttribute')
                    attribute_node.attribute_name = 'COLOR_0'
                    attribute_node.location = -500, 0
                else:
                    vertexcolor_node = node_tree.nodes.new('ShaderNodeVertexColor')
                    vertexcolor_node.layer_name = 'COLOR_0'
                    vertexcolor_node.location = -500, 0

                if nodetype == "principled":
                    # TODO : currently set metallic & specular in same way
                    main_node.inputs[5].default_value = pypbr.metallic_factor
                    main_node.inputs[7].default_value = pypbr.roughness_factor

                # links
                rgb_node = node_tree.nodes.new('ShaderNodeMixRGB')
                rgb_node.blend_type = 'MULTIPLY'
                rgb_node.inputs['Fac'].default_value = 1.0
                rgb_node.inputs['Color1'].default_value = pypbr.base_color_factor
                if bpy.app.version < (2, 81, 8):
                    node_tree.links.new(rgb_node.inputs['Color2'], attribute_node.outputs[0])
                else:
                    node_tree.links.new(rgb_node.inputs['Color2'], vertexcolor_node.outputs[0])
                node_tree.links.new(main_node.inputs[0], rgb_node.outputs[0])

        elif pypbr.color_type == gltf.TEXTURE_FACTOR:

            # TODO alpha ?
            if vertex_color:
                # TODO tree locations
                # Create attribute / separate / math nodes
                if bpy.app.version < (2, 81, 8):
                    attribute_node = node_tree.nodes.new('ShaderNodeAttribute')
                    attribute_node.attribute_name = 'COLOR_0'
                else:
                    vertexcolor_node = node_tree.nodes.new('ShaderNodeVertexColor')
                    vertexcolor_node.layer_name = 'COLOR_0'

                vc_mult_node = node_tree.nodes.new('ShaderNodeMixRGB')
                vc_mult_node.blend_type = 'MULTIPLY'
                vc_mult_node.inputs['Fac'].default_value = 1.0

            BlenderTextureInfo.create(gltf, pypbr.base_color_texture)

            # create UV Map / Mapping / Texture nodes / separate & math and combine
            text_node = node_tree.nodes.new('ShaderNodeTexImage')
            if gltf.data.images[
                gltf.data.textures[pypbr.base_color_texture.index].source
            ].blender_image_name is not None:
                text_node.image = bpy.data.images[gltf.data.images[
                    gltf.data.textures[pypbr.base_color_texture.index].source
                ].blender_image_name]
            text_node.label = 'BASE COLOR'
            text_node.location = -1000, 500

            mult_node = node_tree.nodes.new('ShaderNodeMixRGB')
            mult_node.blend_type = 'MULTIPLY'
            mult_node.inputs['Fac'].default_value = 1.0
            mult_node.inputs['Color2'].default_value = [
                                                        pypbr.base_color_factor[0],
                                                        pypbr.base_color_factor[1],
                                                        pypbr.base_color_factor[2],
                                                        pypbr.base_color_factor[3],
                                                        ]

            mapping = node_tree.nodes.new('ShaderNodeMapping')
            mapping.location = -1500, 500
            mapping.vector_type = 'POINT'
            if text_node.image is not None: # Sometimes images can't be retrieved (bad gltf file ...)
                tex_transform = text_node.image['tex_transform'][str(pypbr.base_color_texture.index)]
                if bpy.app.version < (2, 81, 8):
                    mapping.translation[0] = texture_transform_gltf_to_blender(tex_transform)['offset'][0]
                    mapping.translation[1] = texture_transform_gltf_to_blender(tex_transform)['offset'][1]
                    mapping.rotation[2] = texture_transform_gltf_to_blender(tex_transform)['rotation']
                    mapping.scale[0] = texture_transform_gltf_to_blender(tex_transform)['scale'][0]
                    mapping.scale[1] = texture_transform_gltf_to_blender(tex_transform)['scale'][1]
                else:
                    mapping.inputs['Location'].default_value[0] = texture_transform_gltf_to_blender(tex_transform)['offset'][0]
                    mapping.inputs['Location'].default_value[1] = texture_transform_gltf_to_blender(tex_transform)['offset'][1]
                    mapping.inputs['Rotation'].default_value[2] = texture_transform_gltf_to_blender(tex_transform)['rotation']
                    mapping.inputs['Scale'].default_value[0] = texture_transform_gltf_to_blender(tex_transform)['scale'][0]
                    mapping.inputs['Scale'].default_value[1] = texture_transform_gltf_to_blender(tex_transform)['scale'][1]



            uvmap = node_tree.nodes.new('ShaderNodeUVMap')
            uvmap.location = -2000, 500
            if pypbr.base_color_texture.tex_coord is not None:
                uvmap["gltf2_texcoord"] = pypbr.base_color_texture.tex_coord  # Set custom flag to retrieve TexCoord
            else:
                uvmap["gltf2_texcoord"] = 0  # TODO set in pre_compute instead of here
            # UV Map will be set after object/UVMap creation

            # Create links
            if vertex_color:
                if bpy.app.version < (2, 81, 8):
                    node_tree.links.new(vc_mult_node.inputs[2], attribute_node.outputs[0])
                else:
                    node_tree.links.new(vc_mult_node.inputs[2], vertexcolor_node.outputs[0])
                node_tree.links.new(vc_mult_node.inputs[1], mult_node.outputs[0])
                node_tree.links.new(main_node.inputs[0], vc_mult_node.outputs[0])

            else:
                node_tree.links.new(main_node.inputs[0], mult_node.outputs[0])

            # Common for both mode (non vertex color / vertex color)
            node_tree.links.new(mapping.inputs[0], uvmap.outputs[0])
            node_tree.links.new(text_node.inputs[0], mapping.outputs[0])
            node_tree.links.new(mult_node.inputs[1], text_node.outputs[0])

        elif pypbr.color_type == gltf.TEXTURE:

            BlenderTextureInfo.create(gltf, pypbr.base_color_texture)

            # TODO alpha ?
            if vertex_color:
                # Create attribute / separate / math nodes
                if bpy.app.version < (2, 81, 8):
                    attribute_node = node_tree.nodes.new('ShaderNodeAttribute')
                    attribute_node.attribute_name = 'COLOR_0'
                    attribute_node.location = -2000, 250
                else:
                    vertexcolor_node = node_tree.nodes.new('ShaderNodeVertexColor')
                    vertexcolor_node.layer_name = 'COLOR_0'
                    vertexcolor_node.location = -2000, 250

                vc_mult_node = node_tree.nodes.new('ShaderNodeMixRGB')
                vc_mult_node.blend_type = 'MULTIPLY'
                vc_mult_node.inputs['Fac'].default_value = 1.0

            # create UV Map / Mapping / Texture nodes / separate & math and combine
            text_node = node_tree.nodes.new('ShaderNodeTexImage')
            if gltf.data.images[
                gltf.data.textures[pypbr.base_color_texture.index].source
            ].blender_image_name is not None:
                text_node.image = bpy.data.images[gltf.data.images[
                    gltf.data.textures[pypbr.base_color_texture.index].source
                ].blender_image_name]
            text_node.label = 'BASE COLOR'
            if vertex_color:
                text_node.location = -2000, 500
            else:
                text_node.location = -500, 500

            mapping = node_tree.nodes.new('ShaderNodeMapping')
            if vertex_color:
                mapping.location = -2500, 500
            else:
                mapping.location = -1500, 500
            mapping.vector_type = 'POINT'
            if text_node.image is not None: # Sometimes images can't be retrieved (bad gltf file ...)
                tex_transform = text_node.image['tex_transform'][str(pypbr.base_color_texture.index)]
                if bpy.app.version < (2, 81, 8):
                    mapping.translation[0] = texture_transform_gltf_to_blender(tex_transform)['offset'][0]
                    mapping.translation[1] = texture_transform_gltf_to_blender(tex_transform)['offset'][1]
                    mapping.rotation[2] = texture_transform_gltf_to_blender(tex_transform)['rotation']
                    mapping.scale[0] = texture_transform_gltf_to_blender(tex_transform)['scale'][0]
                    mapping.scale[1] = texture_transform_gltf_to_blender(tex_transform)['scale'][1]
                else:
                    mapping.inputs['Location'].default_value[0] = texture_transform_gltf_to_blender(tex_transform)['offset'][0]
                    mapping.inputs['Location'].default_value[1] = texture_transform_gltf_to_blender(tex_transform)['offset'][1]
                    mapping.inputs['Rotation'].default_value[2] = texture_transform_gltf_to_blender(tex_transform)['rotation']
                    mapping.inputs['Scale'].default_value[0] = texture_transform_gltf_to_blender(tex_transform)['scale'][0]
                    mapping.inputs['Scale'].default_value[1] = texture_transform_gltf_to_blender(tex_transform)['scale'][1]


            uvmap = node_tree.nodes.new('ShaderNodeUVMap')
            if vertex_color:
                uvmap.location = -3000, 500
            else:
                uvmap.location = -2000, 500
            if pypbr.base_color_texture.tex_coord is not None:
                uvmap["gltf2_texcoord"] = pypbr.base_color_texture.tex_coord  # Set custom flag to retrieve TexCoord
            else:
                uvmap["gltf2_texcoord"] = 0  # TODO set in pre_compute instead of here
            # UV Map will be set after object/UVMap creation

            # Create links
            if vertex_color:
                if bpy.app.version < (2, 81, 8):
                    node_tree.links.new(vc_mult_node.inputs[2], attribute_node.outputs[0])
                else:
                    node_tree.links.new(vc_mult_node.inputs[2], vertexcolor_node.outputs[0])
                node_tree.links.new(vc_mult_node.inputs[1], text_node.outputs[0])
                node_tree.links.new(main_node.inputs[0], vc_mult_node.outputs[0])

            else:
                node_tree.links.new(main_node.inputs[0], text_node.outputs[0])

            # Common for both mode (non vertex color / vertex color)

            node_tree.links.new(mapping.inputs[0], uvmap.outputs[0])
            node_tree.links.new(text_node.inputs[0], mapping.outputs[0])

        if nodetype == 'principled':
            # Says metallic, but it means metallic & Roughness values
            if pypbr.metallic_type == gltf.SIMPLE:
                main_node.inputs[4].default_value = pypbr.metallic_factor
                main_node.inputs[7].default_value = pypbr.roughness_factor

            elif pypbr.metallic_type == gltf.TEXTURE:
                BlenderTextureInfo.create(gltf, pypbr.metallic_roughness_texture)
                metallic_text = node_tree.nodes.new('ShaderNodeTexImage')
                metallic_text.image = bpy.data.images[gltf.data.images[
                    gltf.data.textures[pypbr.metallic_roughness_texture.index].source
                ].blender_image_name]
                if bpy.app.version < (2, 80, 0):
                    metallic_text.color_space = 'NONE'
                else:
                    if metallic_text.image:
                        metallic_text.image.colorspace_settings.is_data = True
                metallic_text.label = 'METALLIC ROUGHNESS'
                metallic_text.location = -500, 0

                metallic_separate = node_tree.nodes.new('ShaderNodeSeparateRGB')
                metallic_separate.location = -250, 0

                metallic_mapping = node_tree.nodes.new('ShaderNodeMapping')
                metallic_mapping.location = -1000, 0
                metallic_mapping.vector_type = 'POINT'
                tex_transform = metallic_text.image['tex_transform'][str(pypbr.metallic_roughness_texture.index)]
                if bpy.app.version < (2, 81, 8):
                    metallic_mapping.translation[0] = texture_transform_gltf_to_blender(tex_transform)['offset'][0]
                    metallic_mapping.translation[1] = texture_transform_gltf_to_blender(tex_transform)['offset'][1]
                    metallic_mapping.rotation[2] = texture_transform_gltf_to_blender(tex_transform)['rotation']
                    metallic_mapping.scale[0] = texture_transform_gltf_to_blender(tex_transform)['scale'][0]
                    metallic_mapping.scale[1] = texture_transform_gltf_to_blender(tex_transform)['scale'][1]
                else:
                    metallic_mapping.inputs['Location'].default_value[0] = texture_transform_gltf_to_blender(tex_transform)['offset'][0]
                    metallic_mapping.inputs['Location'].default_value[1] = texture_transform_gltf_to_blender(tex_transform)['offset'][1]
                    metallic_mapping.inputs['Rotation'].default_value[2] = texture_transform_gltf_to_blender(tex_transform)['rotation']
                    metallic_mapping.inputs['Scale'].default_value[0] = texture_transform_gltf_to_blender(tex_transform)['scale'][0]
                    metallic_mapping.inputs['Scale'].default_value[1] = texture_transform_gltf_to_blender(tex_transform)['scale'][1]


                metallic_uvmap = node_tree.nodes.new('ShaderNodeUVMap')
                metallic_uvmap.location = -1500, 0
                if pypbr.metallic_roughness_texture.tex_coord is not None:
                    # Set custom flag to retrieve TexCoord
                    metallic_uvmap["gltf2_texcoord"] = pypbr.metallic_roughness_texture.tex_coord
                else:
                    metallic_uvmap["gltf2_texcoord"] = 0  # TODO set in pre_compute instead of here

                # links
                node_tree.links.new(metallic_separate.inputs[0], metallic_text.outputs[0])
                node_tree.links.new(main_node.inputs[4], metallic_separate.outputs[2])  # metallic
                node_tree.links.new(main_node.inputs[7], metallic_separate.outputs[1])  # Roughness

                node_tree.links.new(metallic_mapping.inputs[0], metallic_uvmap.outputs[0])
                node_tree.links.new(metallic_text.inputs[0], metallic_mapping.outputs[0])

            elif pypbr.metallic_type == gltf.TEXTURE_FACTOR:

                BlenderTextureInfo.create(gltf, pypbr.metallic_roughness_texture)
                metallic_text = node_tree.nodes.new('ShaderNodeTexImage')
                metallic_text.image = bpy.data.images[gltf.data.images[
                    gltf.data.textures[pypbr.metallic_roughness_texture.index].source
                ].blender_image_name]
                if bpy.app.version < (2, 80, 0):
                    metallic_text.color_space = 'NONE'
                else:
                    if metallic_text.image:
                        metallic_text.image.colorspace_settings.is_data = True
                metallic_text.label = 'METALLIC ROUGHNESS'
                metallic_text.location = -1000, 0

                metallic_separate = node_tree.nodes.new('ShaderNodeSeparateRGB')
                metallic_separate.location = -500, 0

                metallic_math = node_tree.nodes.new('ShaderNodeMath')
                metallic_math.operation = 'MULTIPLY'
                metallic_math.inputs[1].default_value = pypbr.metallic_factor
                metallic_math.location = -250, 100

                roughness_math = node_tree.nodes.new('ShaderNodeMath')
                roughness_math.operation = 'MULTIPLY'
                roughness_math.inputs[1].default_value = pypbr.roughness_factor
                roughness_math.location = -250, -100

                metallic_mapping = node_tree.nodes.new('ShaderNodeMapping')
                metallic_mapping.location = -1000, 0
                metallic_mapping.vector_type = 'POINT'
                tex_transform = metallic_text.image['tex_transform'][str(pypbr.metallic_roughness_texture.index)]
                if bpy.app.version < (2, 81, 8):
                    metallic_mapping.translation[0] = texture_transform_gltf_to_blender(tex_transform)['offset'][0]
                    metallic_mapping.translation[1] = texture_transform_gltf_to_blender(tex_transform)['offset'][1]
                    metallic_mapping.rotation[2] = texture_transform_gltf_to_blender(tex_transform)['rotation']
                    metallic_mapping.scale[0] = texture_transform_gltf_to_blender(tex_transform)['scale'][0]
                    metallic_mapping.scale[1] = texture_transform_gltf_to_blender(tex_transform)['scale'][1]
                else:
                    metallic_mapping.inputs['Location'].default_value[0] = texture_transform_gltf_to_blender(tex_transform)['offset'][0]
                    metallic_mapping.inputs['Location'].default_value[1] = texture_transform_gltf_to_blender(tex_transform)['offset'][1]
                    metallic_mapping.inputs['Rotation'].default_value[2] = texture_transform_gltf_to_blender(tex_transform)['rotation']
                    metallic_mapping.inputs['Scale'].default_value[0] = texture_transform_gltf_to_blender(tex_transform)['scale'][0]
                    metallic_mapping.inputs['Scale'].default_value[1] = texture_transform_gltf_to_blender(tex_transform)['scale'][1]

                metallic_uvmap = node_tree.nodes.new('ShaderNodeUVMap')
                metallic_uvmap.location = -1500, 0
                if pypbr.metallic_roughness_texture.tex_coord is not None:
                    # Set custom flag to retrieve TexCoord
                    metallic_uvmap["gltf2_texcoord"] = pypbr.metallic_roughness_texture.tex_coord
                else:
                    metallic_uvmap["gltf2_texcoord"] = 0  # TODO set in pre_compute instead of here

                # links
                node_tree.links.new(metallic_separate.inputs[0], metallic_text.outputs[0])

                # metallic
                node_tree.links.new(metallic_math.inputs[0], metallic_separate.outputs[2])
                node_tree.links.new(main_node.inputs[4], metallic_math.outputs[0])

                # roughness
                node_tree.links.new(roughness_math.inputs[0], metallic_separate.outputs[1])
                node_tree.links.new(main_node.inputs[7], roughness_math.outputs[0])

                node_tree.links.new(metallic_mapping.inputs[0], metallic_uvmap.outputs[0])
                node_tree.links.new(metallic_text.inputs[0], metallic_mapping.outputs[0])

        # link node to output
        if nodetype == 'principled':
            node_tree.links.new(output_node.inputs[0], main_node.outputs[0])
        elif nodetype == 'unlit':
            mix = node_tree.nodes.new('ShaderNodeMixShader')
            mix.location = 1000, 0
            path = node_tree.nodes.new('ShaderNodeLightPath')
            path.location = 500, 300
            if pypbr.color_type != gltf.SIMPLE:
                math = node_tree.nodes.new('ShaderNodeMath')
                math.location = 750, 200
                math.operation = 'MULTIPLY'

                # Set material alpha mode to blend
                # This is needed for Eevee
                if bpy.app.version < (2, 80, 0):
                    pass # Not needed for Cycles
                else:
                    material.blend_method = 'HASHED' # TODO check best result in eevee

            transparent = node_tree.nodes.new('ShaderNodeBsdfTransparent')
            transparent.location = 750, 0

            node_tree.links.new(output_node.inputs[0], mix.outputs[0])
            node_tree.links.new(mix.inputs[2], main_node.outputs[0])
            node_tree.links.new(mix.inputs[1], transparent.outputs[0])
            if pypbr.color_type != gltf.SIMPLE:
                node_tree.links.new(math.inputs[0], path.outputs[0])
                node_tree.links.new(math.inputs[1], text_node.outputs[1])
                node_tree.links.new(mix.inputs[0], math.outputs[0])
            else:
                node_tree.links.new(mix.inputs[0], path.outputs[0])
