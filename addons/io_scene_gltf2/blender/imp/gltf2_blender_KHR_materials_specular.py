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
from .gltf2_blender_texture import texture

def specular(mh, location_specular, location_specular_tint, specular_socket, specular_tint_socket):
    x_specular, y_specular = location_specular
    x_tint, y_tint = location_specular_tint

    try:
        ext = mh.pymat.extensions['KHR_materials_specular']
    except Exception:
        return

    specular_factor = ext.get('specularFactor', 1.0)
    tex_specular_info = ext.get('specularTexture')
    if tex_specular_info is not None:
        tex_specular_info = TextureInfo.from_dict(tex_specular_info)

    if specular_socket is None:
        return

    if tex_specular_info is None:
        specular_socket.default_value = specular_factor
    else:
        # Mix specular factor
        if specular_factor != 1.0:
            node = mh.node_tree.nodes.new('ShaderNodeMath')
            node.label = 'Specular Factor'
            node.location = x_specular - 140, y_specular
            node.operation = 'MULTIPLY'
            # Outputs
            mh.node_tree.links.new(specular_socket, node.outputs[0])
            # Inputs
            specular_socket = node.inputs[0]
            node.inputs[1].default_value = specular_factor

            x_specular -= 200

        texture(
            mh,
            tex_info=tex_specular_info,
            label='SPECULAR',
            location=(x_specular, y_specular),
            is_data=True,
            color_socket=None,
            alpha_socket=specular_socket
        )

    specular_tint_factor = ext.get('specularColorFactor', [1.0, 1.0, 1.0])
    tex_specular_tint_info = ext.get('specularColorTexture')
    if tex_specular_tint_info is not None:
        tex_specular_tint_info = TextureInfo.from_dict(tex_specular_tint_info)

    if specular_tint_socket is None:
        return

    if tex_specular_tint_info is None:
        # Blender does not support RGB tint for specular
        # For now, converting to BW
        luminance = lambda c: 0.3 * c[0] + 0.6 * c[1] + 0.1 * c[2]
        specular_tint_socket.default_value = luminance(specular_tint_factor)
        return

    # Blender does not support RGB tint for specular
    # For now, converting to BW
    node = mh.node_tree.nodes.new('ShaderNodeRGBToBW')
    node.label = 'Specular Color'
    node.location = x_tint - 140, y_tint
    # Outputs
    mh.node_tree.links.new(specular_tint_socket, node.outputs[0])
    # Inputs
    specular_tint_socket = node.inputs[0]

    x_tint -= 200

    # Mix specularColorFactor
    if specular_tint_factor != [1.0, 1.0, 1.0]:
        node = mh.node_tree.nodes.new('ShaderNodeMixRGB')
        node.label = 'Specular Color Factor'
        node.location = x_tint - 140, y_tint
        node.blend_type = 'MULTIPLY'
        # Outputs
        mh.node_tree.links.new(specular_tint_socket, node.outputs[0])
        # Inputs
        node.inputs['Fac'].default_value = 1.0
        specular_tint_socket = node.inputs['Color1']
        node.inputs['Color2'].default_value = specular_tint_factor[:3] + [1]

        x_tint -= 200

    texture(
        mh,
        tex_info=tex_specular_tint_info,
        label='SPECULAR COLOR',
        location=(x_tint, y_tint),
        is_data=True,
        color_socket=specular_tint_socket,
    )