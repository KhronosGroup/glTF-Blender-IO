# Copyright 2018-2022 The glTF-Blender-IO authors.
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


# [Texture] => [Separate R] => [Transmission Factor] =>
def transmission(mh, location, transmission_socket):
    x, y = location
    try:
        mh.pymat.extensions['KHR_materials_transmission']['blender_nodetree'] = mh.node_tree # Needed for KHR_animation_pointer
        mh.pymat.extensions['KHR_materials_transmission']['blender_mat'] = mh.mat # Needed for KHR_animation_pointer
        ext = mh.pymat.extensions['KHR_materials_transmission']
    except Exception:
        print("What?????")
        return
    transmission_factor = ext.get('transmissionFactor', 0)

    need_transmission = transmission_factor != 0  # Default value is 0, so no transmission

    # We need transmission if animated by KHR_animation_pointer
    if mh.gltf.data.extensions_used is not None and "KHR_animation_pointer" in mh.gltf.data.extensions_used:
        if len(mh.pymat.extensions["KHR_materials_transmission"]["animations"]) > 0:
            for anim_idx in mh.pymat.extensions["KHR_materials_transmission"]["animations"].keys():
                for channel_idx in mh.pymat.extensions["KHR_materials_transmission"]["animations"][anim_idx]:
                    channel = mh.gltf.data.animations[anim_idx].channels[channel_idx]
                    pointer_tab = channel.target.extensions["KHR_animation_pointer"]["pointer"].split("/")
                    if len(pointer_tab) == 6 and pointer_tab[1] == "materials" and \
                            pointer_tab[3] == "extensions" and \
                            pointer_tab[4] == "KHR_materials_transmission" and \
                            pointer_tab[5] == "transmissionFactor":
                        need_transmission = True

    print("Need Transmission for", mh.mat.name, need_transmission)

    if need_transmission is False:
        return

    # Activate screen refraction (for Eevee)
    mh.mat.use_screen_refraction = True

    tex_info = ext.get('transmissionTexture')
    if tex_info is not None:
        tex_info = TextureInfo.from_dict(tex_info)

    if transmission_socket is None:
        return

    if tex_info is None:
        transmission_socket.default_value = transmission_factor
        return

    # Mix transmission factor
    if transmission_factor != 1 or need_transmission is True:
        node = mh.node_tree.nodes.new('ShaderNodeMath')
        node.label = 'Transmission Factor'
        node.location = x - 140, y
        node.operation = 'MULTIPLY'
        # Outputs
        mh.node_tree.links.new(transmission_socket, node.outputs[0])
        # Inputs
        transmission_socket = node.inputs[0]
        node.inputs[1].default_value = transmission_factor

        x -= 200

    # Separate RGB
    node = mh.node_tree.nodes.new('ShaderNodeSeparateColor')
    node.location = x - 150, y - 75
    # Outputs
    mh.node_tree.links.new(transmission_socket, node.outputs['Red'])
    # Inputs
    transmission_socket = node.inputs[0]

    x -= 200

    texture(
        mh,
        tex_info=tex_info,
        label='TRANSMISSION',
        location=(x, y),
        is_data=True,
        color_socket=transmission_socket,
    )
