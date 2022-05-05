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

from ...io.com.gltf2_io import TextureInfo, MaterialNormalTextureInfoClass
from .gltf2_blender_texture import texture

def volume(mh, location, volume_socket, thickness_socket):
    try:
        ext = mh.pymat.extensions['KHR_materials_volume']
    except Exception:
        return

    # Attenuation Color
    attenuationColor = \
            mh.pymat.extensions['KHR_materials_volume'] \
            .get('attenuationColor')
    # glTF is color3, Blender adds alpha
    if attenuationColor is None:
        attenuationColor = [1.0, 1.0, 1.0, 1.0]
    else:
        attenuationColor.extend([1.0])
    volume_socket.node.inputs[0].default_value = attenuationColor

    # Attenuation Distance / Density
    attenuationDistance = mh.pymat.extensions['KHR_materials_volume'].get('attenuationDistance')
    if attenuationDistance is None:
        density = 0
    else:
        density = 1.0 / attenuationDistance
    volume_socket.node.inputs[1].default_value = density

    # thicknessFactor / thicknessTexture
    x, y = location
    try:
        ext = mh.pymat.extensions['KHR_materials_volume']
    except Exception:
        return
    thickness_factor = ext.get('thicknessFactor', 0)
    tex_info = ext.get('thicknessTexture')
    if tex_info is not None:
        tex_info = TextureInfo.from_dict(tex_info)

    if thickness_socket is None:
        return

    if tex_info is None:
        thickness_socket.default_value = thickness_factor
        return

    # Mix thickness factor
    if thickness_factor != 1:
        node = mh.node_tree.nodes.new('ShaderNodeMath')
        node.label = 'Thickness Factor'
        node.location = x - 140, y
        node.operation = 'MULTIPLY'
        # Outputs
        mh.node_tree.links.new(thickness_socket, node.outputs[0])
        # Inputs
        thickness_socket = node.inputs[0]
        node.inputs[1].default_value = thickness_factor

        x -= 200

    # Separate RGB
    node = mh.node_tree.nodes.new('ShaderNodeSeparateRGB')
    node.location = x - 150, y - 75
    # Outputs
    mh.node_tree.links.new(thickness_socket, node.outputs['G'])
    # Inputs
    thickness_socket = node.inputs[0]

    x -= 200

    texture(
        mh,
        tex_info=tex_info,
        label='THICKNESS',
        location=(x, y),
        is_data=True,
        color_socket=thickness_socket,
    )
