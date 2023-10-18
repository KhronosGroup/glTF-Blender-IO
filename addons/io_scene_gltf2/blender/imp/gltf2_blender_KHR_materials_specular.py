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

import bpy
from ...io.com.gltf2_io import TextureInfo
from .gltf2_blender_texture import texture
from ...io.com.gltf2_io_constants import GLTF_IOR
from ..exp.material.extensions.gltf2_blender_image import TmpImageGuard, make_temp_image_copy #TODO move to com


def specular(mh, location_specular,
                 location_specular_tint,
                 specular_socket,
                 specular_tint_socket):

    if specular_socket is None:
        return
    if specular_tint_socket is None:
        return

    try:
        ext = mh.pymat.extensions['KHR_materials_specular']
    except Exception:
        return

    # First check if we need a texture or not -> retrieve all info needed
    specular_factor = ext.get('specularFactor', 1.0)
    tex_specular_info = ext.get('specularTexture')
    if tex_specular_info is not None:
        tex_specular_info = TextureInfo.from_dict(tex_specular_info)

    specular_tint_factor = ext.get('specularColorFactor', [1.0, 1.0, 1.0])[:3]
    tex_specular_tint_info = ext.get('specularColorTexture')
    if tex_specular_tint_info is not None:
        tex_specular_tint_info = TextureInfo.from_dict(tex_specular_tint_info)

    x_specular, y_specular = location_specular
    x_specularcolor, y_specularcolor = location_specular_tint

    if tex_specular_info is None:
        specular_socket.default_value = specular_factor / 2.0
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
            node.inputs[1].default_value = specular_factor / 2.0
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

    if tex_specular_tint_info is None:
        specular_tint_factor = list(specular_tint_factor)
        specular_tint_factor.extend([1.0])
        specular_tint_socket.default_value = specular_tint_factor
    else:
            specular_tint_factor = list(specular_tint_factor) + [1.0]
            if specular_tint_factor != [1.0, 1.0, 1.0, 1.0]:
                # Mix specularColorFactor
                node = mh.node_tree.nodes.new('ShaderNodeMix')
                node.label = 'SpecularColor Factor'
                node.data_type = 'RGBA'
                node.location = x_specularcolor - 140, y_specularcolor
                node.blend_type = 'MULTIPLY'
                # Outputs
                mh.node_tree.links.new(specular_tint_socket, node.outputs[2])
                # Inputs
                node.inputs['Factor'].default_value = 1.0
                specular_tint_socket = node.inputs[6]
                node.inputs[7].default_value = specular_tint_factor
                x_specularcolor -= 200

            texture(
                mh,
                tex_info=tex_specular_tint_info,
                label='SPECULAR COLOR',
                location=(x_specularcolor, y_specularcolor),
                color_socket=specular_tint_socket,
                )
