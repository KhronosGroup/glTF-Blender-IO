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
        mh.pymat.extensions['KHR_materials_clearcoat']['blender_nodetree'] = mh.node_tree # Needed for KHR_animation_pointer
        mh.pymat.extensions['KHR_materials_clearcoat']['blender_mat'] = mh.mat # Needed for KHR_animation_pointer
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

    # We will need clearcoat factor (Mix node) if animated by KHR_animation_pointer (and standard case if clearcoatFactor != 1)
    need_clearcoat_factor = clearcoat_factor != 1  # Default value is 1, so no clearcoat factor
    if need_clearcoat_factor is False:
        # Check if animated by KHR_animation_pointer
        if mh.gltf.data.extensions_used is not None and "KHR_animation_pointer" in mh.gltf.data.extensions_used:
            if len(mh.pymat.extensions["KHR_materials_clearcoat"]["animations"]) > 0:
                for anim_idx in mh.pymat.extensions["KHR_materials_clearcoat"]["animations"].keys():
                    for channel_idx in mh.pymat.extensions["KHR_materials_clearcoat"]["animations"][anim_idx]:
                        channel = mh.gltf.data.animations[anim_idx].channels[channel_idx]
                        pointer_tab = channel.target.extensions["KHR_animation_pointer"]["pointer"].split("/")
                        if len(pointer_tab) == 6 and pointer_tab[1] == "materials" and \
                                pointer_tab[3] == "extensions" and \
                                pointer_tab[4] == "KHR_materials_clearcoat" and \
                                pointer_tab[5] == "clearcoatFactor":
                            need_clearcoat_factor = True

    # Mix clearcoat factor
    if need_clearcoat_factor is True:
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
    node = mh.node_tree.nodes.new('ShaderNodeSeparateColor')
    node.location = x - 150, y - 75
    # Outputs
    mh.node_tree.links.new(clearcoat_socket, node.outputs['Red'])
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

    # Because extensions are dict, they are not passed by reference
    # So we need to update the dict of the KHR_texture_transform extension if needed
    if tex_info.extensions is not None and "KHR_texture_transform" in tex_info.extensions:
        mh.pymat.extensions['KHR_materials_clearcoat']['clearcoatTexture']['extensions']['KHR_texture_transform'] = tex_info.extensions["KHR_texture_transform"]



# [Texture] => [Separate G] => [Roughness Factor] =>
def clearcoat_roughness(mh, location, roughness_socket):
    x, y = location
    try:
        ext = mh.pymat.extensions['KHR_materials_clearcoat']
        mh.pymat.extensions['KHR_materials_clearcoat']['blender_nodetree'] = mh.node_tree # Needed for KHR_animation_pointer
        mh.pymat.extensions['KHR_materials_clearcoat']['blender_mat'] = mh.mat # Needed for KHR_animation_pointer
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

    # We will need clearcoatRoughness factor (Mix node) if animated by KHR_animation_pointer (and standard case if clearcoatRoughnessFactor != 1)
    need_clearcoat_roughness_factor = roughness_factor != 1  # Default value is 1, so no clearcoatRoughness factor
    if need_clearcoat_roughness_factor is False:
        # Check if animated by KHR_animation_pointer
        if mh.gltf.data.extensions_used is not None and "KHR_animation_pointer" in mh.gltf.data.extensions_used:
            if len(mh.pymat.extensions["KHR_materials_clearcoat"]["animations"]) > 0:
                for anim_idx in mh.pymat.extensions["KHR_materials_clearcoat"]["animations"].keys():
                    for channel_idx in mh.pymat.extensions["KHR_materials_clearcoat"]["animations"][anim_idx]:
                        channel = mh.gltf.data.animations[anim_idx].channels[channel_idx]
                        pointer_tab = channel.target.extensions["KHR_animation_pointer"]["pointer"].split("/")
                        if len(pointer_tab) == 6 and pointer_tab[1] == "materials" and \
                                pointer_tab[3] == "extensions" and \
                                pointer_tab[4] == "KHR_materials_clearcoat" and \
                                pointer_tab[5] == "clearcoatRoughnessFactor":
                            need_clearcoat_roughness_factor = True

    # Mix roughness factor
    if need_clearcoat_roughness_factor is True:
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
    node = mh.node_tree.nodes.new('ShaderNodeSeparateColor')
    node.location = x - 150, y - 75
    # Outputs
    mh.node_tree.links.new(roughness_socket, node.outputs['Green'])
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

    # Because extensions are dict, they are not passed by reference
    # So we need to update the dict of the KHR_texture_transform extension if needed
    if tex_info.extensions is not None and "KHR_texture_transform" in tex_info.extensions:
        mh.pymat.extensions['KHR_materials_clearcoat']['clearcoatRoughnessTexture']['extensions']['KHR_texture_transform'] = tex_info.extensions["KHR_texture_transform"]



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

    # Because extensions are dict, they are not passed by reference
    # So we need to update the dict of the KHR_texture_transform extension if needed
    if tex_info.extensions is not None and "KHR_texture_transform" in tex_info.extensions:
        mh.pymat.extensions['KHR_materials_clearcoat']['clearcoatNormalTexture']['extensions']['KHR_texture_transform'] = tex_info.extensions["KHR_texture_transform"]

