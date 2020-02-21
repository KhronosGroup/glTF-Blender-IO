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
from ...io.com.gltf2_io import TextureInfo
from .gltf2_blender_pbrMetallicRoughness import \
    base_color, emission, normal, occlusion, make_output_nodes
from .gltf2_blender_texture import texture


def pbr_specular_glossiness(mh):
    """Creates node tree for pbrSpecularGlossiness materials."""
    # Need to be be in Eevee mode to use the Specular node
    scene = bpy.data.scenes[mh.gltf.blender_scene]
    if scene.render.engine != "BLENDER_EEVEE":
        scene.render.engine = "BLENDER_EEVEE"

    spec_node = mh.node_tree.nodes.new('ShaderNodeEeveeSpecular')
    spec_node.location = 10, 300

    _emission_socket, alpha_socket = make_output_nodes(
        mh,
        location=(250, 260),
        shader_socket=spec_node.outputs[0],
        make_emission_socket=False,
        make_alpha_socket=not mh.is_opaque(),
    )

    emission(
        mh,
        location=(-200, 860),
        color_socket=spec_node.inputs['Emissive Color'],
    )

    base_color(
        mh,
        is_diffuse=True,
        location=(-200, 380),
        color_socket=spec_node.inputs['Base Color'],
        alpha_socket=alpha_socket,
    )

    specular_glossiness(
        mh,
        location=(-200, -100),
        specular_socket=spec_node.inputs['Specular'],
        roughness_socket=spec_node.inputs['Roughness'],
    )

    normal(
        mh,
        location=(-200, -580),
        normal_socket=spec_node.inputs['Normal'],
    )

    occlusion(
        mh,
        location=(-200, -1060),
        occlusion_socket=spec_node.inputs['Ambient Occlusion'],
    )


# [Texture] => [Spec/Gloss Factor] => [Gloss to Rough] =>
def specular_glossiness(mh, location, specular_socket, roughness_socket):
    x, y = location
    spec_factor = mh.pymat.extensions \
        ['KHR_materials_pbrSpecularGlossiness'] \
        .get('specularFactor', [1, 1, 1])
    gloss_factor = mh.pymat.extensions \
        ['KHR_materials_pbrSpecularGlossiness'] \
        .get('glossinessFactor', 1)
    spec_gloss_texture = mh.pymat.extensions \
        ['KHR_materials_pbrSpecularGlossiness'] \
        .get('specularGlossinessTexture', None)
    if spec_gloss_texture is not None:
        spec_gloss_texture = TextureInfo.from_dict(spec_gloss_texture)

    if spec_gloss_texture is None:
        specular_socket.default_value = spec_factor + [1]
        roughness_socket.default_value = 1 - gloss_factor
        return

    # (1 - x) converts glossiness to roughness
    node = mh.node_tree.nodes.new('ShaderNodeInvert')
    node.label = 'Invert (Gloss to Rough)'
    node.location = x - 140, y - 75
    # Outputs
    mh.node_tree.links.new(roughness_socket, node.outputs[0])
    # Inputs
    node.inputs['Fac'].default_value = 1
    glossiness_socket = node.inputs['Color']

    x -= 250

    # Mix in spec/gloss factor
    if spec_factor != [1, 1, 1] or gloss_factor != 1:
        if spec_factor != [1, 1, 1]:
            node = mh.node_tree.nodes.new('ShaderNodeMixRGB')
            node.label = 'Specular Factor'
            node.location = x - 140, y
            node.blend_type = 'MULTIPLY'
            # Outputs
            mh.node_tree.links.new(specular_socket, node.outputs[0])
            # Inputs
            node.inputs['Fac'].default_value = 1.0
            specular_socket = node.inputs['Color1']
            node.inputs['Color2'].default_value = spec_factor + [1]

        if gloss_factor != 1:
            node = mh.node_tree.nodes.new('ShaderNodeMath')
            node.label = 'Glossiness Factor'
            node.location = x - 140, y - 200
            node.operation = 'MULTIPLY'
            # Outputs
            mh.node_tree.links.new(glossiness_socket, node.outputs[0])
            # Inputs
            glossiness_socket = node.inputs[0]
            node.inputs[1].default_value = gloss_factor

        x -= 200

    texture(
        mh,
        tex_info=spec_gloss_texture,
        label='SPECULAR GLOSSINESS',
        location=(x, y),
        color_socket=specular_socket,
        alpha_socket=glossiness_socket,
    )
