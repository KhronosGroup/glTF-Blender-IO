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

def volume(mh, location, volume_socket, thickness_socket):
    # implementation based on https://github.com/KhronosGroup/glTF-Blender-IO/issues/1454#issuecomment-928319444
    try:
        mh.pymat.extensions['KHR_materials_volume']['blender_nodetree'] = mh.node_tree # Needed for KHR_animation_pointer
        mh.pymat.extensions['KHR_materials_volume']['blender_mat'] = mh.mat # Needed for KHR_animation_pointer
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

    math_node_needed = thickness_factor != 1

    # We also need math node if thickness factor is animated in KHR_animation_pointer
    if mh.gltf.data.extensions_used is not None and "KHR_animation_pointer" in mh.gltf.data.extensions_used:
        if len(mh.pymat.extensions["KHR_materials_volume"]["animations"]) > 0:
            for anim_idx in mh.pymat.extensions["KHR_materials_volume"]["animations"].keys():
                for channel_idx in mh.pymat.extensions["KHR_materials_volume"]["animations"][anim_idx]:
                    channel = mh.gltf.data.animations[anim_idx].channels[channel_idx]
                    pointer_tab = channel.target.extensions["KHR_animation_pointer"]["pointer"].split("/")
                    if len(pointer_tab) == 6 and pointer_tab[1] == "materials" and \
                            pointer_tab[3] == "extensions" and \
                            pointer_tab[4] == "KHR_materials_volume" and \
                            pointer_tab[5] == "thicknessFactor":
                        math_node_needed = True

    if math_node_needed is True:
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
    node = mh.node_tree.nodes.new('ShaderNodeSeparateColor')
    node.location = x - 150, y - 75
    # Outputs
    mh.node_tree.links.new(thickness_socket, node.outputs['Green'])
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

    # Because extensions are dict, they are not passed by reference
    # So we need to update the dict of the KHR_texture_transform extension if needed
    if tex_info.extensions is not None and "KHR_texture_transform" in tex_info.extensions:
        mh.pymat.extensions['KHR_materials_volume']['thicknessTexture']['extensions']['KHR_texture_transform'] = tex_info.extensions["KHR_texture_transform"]

