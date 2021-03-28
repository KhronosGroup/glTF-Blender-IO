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


# [Texture] => [Separate R] => [Clearcoat Factor] =>
def clearcoat(mh, location, clearcoat_socket):
    x, y = location
    try:
        ext = mh.pymat.extensions['KHR_materials_clearcoat']
    except Exception:
        return
    clearcoat_factor = ext.get('clearcoatFactor', 0)
    tex_info = ext.get('clearcoatTexture')
    if tex_info is not None:
        tex_info = TextureInfo.from_dict(tex_info)

    if clearcoat_socket is None:
        return

    if tex_info is None:
        clearcoat_socket.default_value = clearcoat_factor
        return

    # Mix clearcoat factor
    if clearcoat_factor != 1:
        node = mh.node_tree.nodes.new('ShaderNodeMath')
        node.label = 'Clearcoat Factor'
        node.location = x - 140, y
        node.operation = 'MULTIPLY'
        # Outputs
        mh.node_tree.links.new(clearcoat_socket, node.outputs[0])
        # Inputs
        clearcoat_socket = node.inputs[0]
        node.inputs[1].default_value = clearcoat_factor

        x -= 200

    # Separate RGB
    node = mh.node_tree.nodes.new('ShaderNodeSeparateRGB')
    node.location = x - 150, y - 75
    # Outputs
    mh.node_tree.links.new(clearcoat_socket, node.outputs['R'])
    # Inputs
    clearcoat_socket = node.inputs[0]

    x -= 200

    texture(
        mh,
        tex_info=tex_info,
        label='CLEARCOAT',
        location=(x, y),
        is_data=True,
        color_socket=clearcoat_socket,
    )


# [Texture] => [Seperate G] => [Roughness Factor] =>
def clearcoat_roughness(mh, location, roughness_socket):
    x, y = location
    try:
        ext = mh.pymat.extensions['KHR_materials_clearcoat']
    except Exception:
        return
    roughness_factor = ext.get('clearcoatRoughnessFactor', 0)
    tex_info = ext.get('clearcoatRoughnessTexture')
    if tex_info is not None:
        tex_info = TextureInfo.from_dict(tex_info)

    if roughness_socket is None:
        return

    if tex_info is None:
        roughness_socket.default_value = roughness_factor
        return

    # Mix roughness factor
    if roughness_factor != 1:
        node = mh.node_tree.nodes.new('ShaderNodeMath')
        node.label = 'Clearcoat Roughness Factor'
        node.location = x - 140, y
        node.operation = 'MULTIPLY'
        # Outputs
        mh.node_tree.links.new(roughness_socket, node.outputs[0])
        # Inputs
        roughness_socket = node.inputs[0]
        node.inputs[1].default_value = roughness_factor

        x -= 200

    # Separate RGB (roughness is in G)
    node = mh.node_tree.nodes.new('ShaderNodeSeparateRGB')
    node.location = x - 150, y - 75
    # Outputs
    mh.node_tree.links.new(roughness_socket, node.outputs['G'])
    # Inputs
    color_socket = node.inputs[0]

    x -= 200

    texture(
        mh,
        tex_info=tex_info,
        label='CLEARCOAT ROUGHNESS',
        location=(x, y),
        is_data=True,
        color_socket=color_socket,
    )


# [Texture] => [Normal Map] =>
def clearcoat_normal(mh, location, normal_socket):
    x,y = location
    try:
        ext = mh.pymat.extensions['KHR_materials_clearcoat']
    except Exception:
        return
    tex_info = ext.get('clearcoatNormalTexture')
    if tex_info is not None:
        tex_info = MaterialNormalTextureInfoClass.from_dict(tex_info)

    if tex_info is None:
        return

    # Normal map
    node = mh.node_tree.nodes.new('ShaderNodeNormalMap')
    node.location = x - 150, y - 40
    # Set UVMap
    uv_idx = tex_info.tex_coord or 0
    try:
        uv_idx = tex_info.extensions['KHR_texture_transform']['texCoord']
    except Exception:
        pass
    node.uv_map = 'UVMap' if uv_idx == 0 else 'UVMap.%03d' % uv_idx
    # Set strength
    scale = tex_info.scale
    scale = scale if scale is not None else 1
    node.inputs['Strength'].default_value = scale
    # Outputs
    mh.node_tree.links.new(normal_socket, node.outputs['Normal'])
    # Inputs
    color_socket = node.inputs['Color']

    x -= 200

    texture(
        mh,
        tex_info=tex_info,
        label='CLEARCOAT NORMAL',
        location=(x, y),
        is_data=True,
        color_socket=color_socket,
    )
