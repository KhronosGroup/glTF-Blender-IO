# Copyright 2018-2021 The glTF-Blender-IO authors.
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

from ...io.com.gltf2_io import TextureInfo
from .gltf2_blender_pbrMetallicRoughness import \
    base_color, emission, normal, occlusion, make_output_nodes, make_settings_node
from .gltf2_blender_texture import texture


def pbr_specular_glossiness(mh):
    """Creates node tree for pbrSpecularGlossiness materials."""
    # This does option #1 from
    # https://github.com/KhronosGroup/glTF-Blender-IO/issues/303

    # Sum a Glossy and Diffuse Shader
    glossy_node = mh.node_tree.nodes.new('ShaderNodeBsdfGlossy')
    diffuse_node = mh.node_tree.nodes.new('ShaderNodeBsdfDiffuse')
    add_node = mh.node_tree.nodes.new('ShaderNodeAddShader')
    glossy_node.location = 10, 220
    diffuse_node.location = 10, 0
    add_node.location = 230, 100
    mh.node_tree.links.new(add_node.inputs[0], glossy_node.outputs[0])
    mh.node_tree.links.new(add_node.inputs[1], diffuse_node.outputs[0])

    emission_socket, alpha_socket = make_output_nodes(
        mh,
        location=(370, 250),
        shader_socket=add_node.outputs[0],
        make_emission_socket=mh.needs_emissive(),
        make_alpha_socket=not mh.is_opaque(),
    )

    emission(
        mh,
        location=(-200, 860),
        color_socket=emission_socket,
    )

    base_color(
        mh,
        is_diffuse=True,
        location=(-200, 380),
        color_socket=diffuse_node.inputs['Color'],
        alpha_socket=alpha_socket,
    )

    specular_glossiness(
        mh,
        location=(-200, -100),
        specular_socket=glossy_node.inputs['Color'],
        roughness_socket=glossy_node.inputs['Roughness'],
    )
    copy_socket(
        mh,
        copy_from=glossy_node.inputs['Roughness'],
        copy_to=diffuse_node.inputs['Roughness'],
    )

    normal(
        mh,
        location=(-200, -580),
        normal_socket=glossy_node.inputs['Normal'],
    )
    copy_socket(
        mh,
        copy_from=glossy_node.inputs['Normal'],
        copy_to=diffuse_node.inputs['Normal'],
    )

    if mh.pymat.occlusion_texture is not None:
        node = make_settings_node(mh)
        node.location = (610, -1060)
        occlusion(
            mh,
            location=(510, -970),
            occlusion_socket=node.inputs['Occlusion'],
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


def copy_socket(mh, copy_from, copy_to):
    """Copy the links/default value from one socket to another."""
    copy_to.default_value = copy_from.default_value
    for link in copy_from.links:
        mh.node_tree.links.new(copy_to, link.from_socket)
