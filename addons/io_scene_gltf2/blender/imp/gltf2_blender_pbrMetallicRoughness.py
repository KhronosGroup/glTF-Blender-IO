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
from ...io.com.gltf2_io import TextureInfo, MaterialPBRMetallicRoughness
from ..com.gltf2_blender_material_helpers import get_gltf_node_name
from .gltf2_blender_texture import texture
from .gltf2_blender_KHR_materials_clearcoat import \
    clearcoat, clearcoat_roughness, clearcoat_normal


class MaterialHelper:
    """Helper class. Stores material stuff to be passed around everywhere."""
    def __init__(self, gltf, pymat, mat, vertex_color):
        self.gltf = gltf
        self.pymat = pymat
        self.mat = mat
        self.node_tree = mat.node_tree
        self.vertex_color = vertex_color
        if pymat.pbr_metallic_roughness is None:
            pymat.pbr_metallic_roughness = \
                MaterialPBRMetallicRoughness.from_dict({})

    def is_opaque(self):
        alpha_mode = self.pymat.alpha_mode
        return alpha_mode is None or alpha_mode == 'OPAQUE'

    def needs_emissive(self):
        return (
            self.pymat.emissive_texture is not None or
            (self.pymat.emissive_factor or [0, 0, 0]) != [0, 0, 0]
        )


def pbr_metallic_roughness(mh: MaterialHelper):
    """Creates node tree for pbrMetallicRoughness materials."""
    pbr_node = mh.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
    pbr_node.location = 10, 300

    make_output_nodes(
        mh,
        location=(250, 260),
        shader_socket=pbr_node.outputs[0],
        make_emission_socket=False,
        make_alpha_socket=False,
    )

    locs = calc_locations(mh)

    emission(
        mh,
        location=locs['emission'],
        color_socket=pbr_node.inputs['Emission'],
    )

    base_color(
        mh,
        location=locs['base_color'],
        color_socket=pbr_node.inputs['Base Color'],
        alpha_socket=pbr_node.inputs['Alpha'] if not mh.is_opaque() else None,
    )

    metallic_roughness(
        mh,
        location=locs['metallic_roughness'],
        metallic_socket=pbr_node.inputs['Metallic'],
        roughness_socket=pbr_node.inputs['Roughness'],
    )

    normal(
        mh,
        location=locs['normal'],
        normal_socket=pbr_node.inputs['Normal'],
    )

    if mh.pymat.occlusion_texture is not None:
        node = make_settings_node(mh)
        node.location = 40, -370
        node.width = 180
        occlusion(
            mh,
            location=locs['occlusion'],
            occlusion_socket=node.inputs['Occlusion'],
        )

    clearcoat(
        mh,
        location=locs['clearcoat'],
        clearcoat_socket=pbr_node.inputs['Clearcoat'],
    )

    clearcoat_roughness(
        mh,
        location=locs['clearcoat_roughness'],
        roughness_socket=pbr_node.inputs['Clearcoat Roughness'],
    )

    clearcoat_normal(
        mh,
        location=locs['clearcoat_normal'],
        normal_socket=pbr_node.inputs['Clearcoat Normal'],
    )


def calc_locations(mh):
    """Calculate locations to place each bit of the node graph at."""
    # Lay the blocks out top-to-bottom, aligned on the right
    x = -200
    y = 0
    height = 460  # height of each block
    locs = {}

    try:
        clearcoat_ext = mh.pymat.extensions['KHR_materials_clearcoat']
    except Exception:
        clearcoat_ext = {}

    locs['base_color'] = (x, y)
    if mh.pymat.pbr_metallic_roughness.base_color_texture is not None or mh.vertex_color:
        y -= height
    locs['metallic_roughness'] = (x, y)
    if mh.pymat.pbr_metallic_roughness.metallic_roughness_texture is not None:
        y -= height
    locs['clearcoat'] = (x, y)
    if 'clearcoatTexture' in clearcoat_ext:
        y -= height
    locs['clearcoat_roughness'] = (x, y)
    if 'clearcoatRoughnessTexture' in clearcoat_ext:
        y -= height
    locs['emission'] = (x, y)
    if mh.pymat.emissive_texture is not None:
        y -= height
    locs['normal'] = (x, y)
    if mh.pymat.normal_texture is not None:
        y -= height
    locs['clearcoat_normal'] = (x, y)
    if 'clearcoatNormalTexture' in clearcoat_ext:
        y -= height
    locs['occlusion'] = (x, y)
    if mh.pymat.occlusion_texture is not None:
        y -= height

    # Center things
    total_height = -y
    y_offset = total_height / 2 - 20
    for key in locs:
        x, y = locs[key]
        locs[key] = (x, y + y_offset)

    return locs


# These functions each create one piece of the node graph, slotting
# their outputs into the given socket, or setting its default value.
# location is roughly the upper-right corner of where to put nodes.


# [Texture] => [Emissive Factor] =>
def emission(mh: MaterialHelper, location, color_socket):
    x, y = location
    emissive_factor = mh.pymat.emissive_factor or [0, 0, 0]

    if color_socket is None:
        return

    if mh.pymat.emissive_texture is None:
        color_socket.default_value = emissive_factor + [1]
        return

    # Mix emissive factor
    if emissive_factor != [1, 1, 1]:
        node = mh.node_tree.nodes.new('ShaderNodeMixRGB')
        node.label = 'Emissive Factor'
        node.location = x - 140, y
        node.blend_type = 'MULTIPLY'
        # Outputs
        mh.node_tree.links.new(color_socket, node.outputs[0])
        # Inputs
        node.inputs['Fac'].default_value = 1.0
        color_socket = node.inputs['Color1']
        node.inputs['Color2'].default_value = emissive_factor + [1]

        x -= 200

    texture(
        mh,
        tex_info=mh.pymat.emissive_texture,
        label='EMISSIVE',
        location=(x, y),
        color_socket=color_socket,
    )


#      [Texture] => [Mix Colors] => [Color Factor] =>
# [Vertex Color] => [Mix Alphas] => [Alpha Factor] =>
def base_color(
    mh: MaterialHelper,
    location,
    color_socket,
    alpha_socket=None,
    is_diffuse=False,
):
    """Handle base color (= baseColorTexture * vertexColor * baseColorFactor)."""
    x, y = location
    pbr = mh.pymat.pbr_metallic_roughness
    if not is_diffuse:
        base_color_factor = pbr.base_color_factor
        base_color_texture = pbr.base_color_texture
    else:
        # Handle pbrSpecularGlossiness's diffuse with this function too,
        # since it's almost exactly the same as base color.
        base_color_factor = \
            mh.pymat.extensions['KHR_materials_pbrSpecularGlossiness'] \
            .get('diffuseFactor', [1, 1, 1, 1])
        base_color_texture = \
            mh.pymat.extensions['KHR_materials_pbrSpecularGlossiness'] \
            .get('diffuseTexture', None)
        if base_color_texture is not None:
            base_color_texture = TextureInfo.from_dict(base_color_texture)

    if base_color_factor is None:
        base_color_factor = [1, 1, 1, 1]

    if base_color_texture is None and not mh.vertex_color:
        color_socket.default_value = base_color_factor
        if alpha_socket is not None:
            alpha_socket.default_value = base_color_factor[3]
        return

    # Mix in base color factor
    needs_color_factor = base_color_factor[:3] != [1, 1, 1]
    needs_alpha_factor = base_color_factor[3] != 1.0 and alpha_socket is not None
    if needs_color_factor or needs_alpha_factor:
        # For now, always create the color factor node because the exporter
        # reads the alpha value from here. Can get rid of "or needs_alpha_factor"
        # when it learns to understand the alpha socket.
        if needs_color_factor or needs_alpha_factor:
            node = mh.node_tree.nodes.new('ShaderNodeMixRGB')
            node.label = 'Color Factor'
            node.location = x - 140, y
            node.blend_type = 'MULTIPLY'
            # Outputs
            mh.node_tree.links.new(color_socket, node.outputs[0])
            # Inputs
            node.inputs['Fac'].default_value = 1.0
            color_socket = node.inputs['Color1']
            node.inputs['Color2'].default_value = base_color_factor

        if needs_alpha_factor:
            node = mh.node_tree.nodes.new('ShaderNodeMath')
            node.label = 'Alpha Factor'
            node.location = x - 140, y - 200
            # Outputs
            mh.node_tree.links.new(alpha_socket, node.outputs[0])
            # Inputs
            node.operation = 'MULTIPLY'
            alpha_socket = node.inputs[0]
            node.inputs[1].default_value = base_color_factor[3]

        x -= 200

    # These are where the texture/vertex color node will put its output.
    texture_color_socket = color_socket
    texture_alpha_socket = alpha_socket
    vcolor_color_socket = color_socket
    vcolor_alpha_socket = alpha_socket

    # Mix texture and vertex color together
    if base_color_texture is not None and mh.vertex_color:
        node = mh.node_tree.nodes.new('ShaderNodeMixRGB')
        node.label = 'Mix Vertex Color'
        node.location = x - 140, y
        node.blend_type = 'MULTIPLY'
        # Outputs
        mh.node_tree.links.new(color_socket, node.outputs[0])
        # Inputs
        node.inputs['Fac'].default_value = 1.0
        texture_color_socket = node.inputs['Color1']
        vcolor_color_socket = node.inputs['Color2']

        if alpha_socket is not None:
            node = mh.node_tree.nodes.new('ShaderNodeMath')
            node.label = 'Mix Vertex Alpha'
            node.location = x - 140, y - 200
            node.operation = 'MULTIPLY'
            # Outputs
            mh.node_tree.links.new(alpha_socket, node.outputs[0])
            # Inputs
            texture_alpha_socket = node.inputs[0]
            vcolor_alpha_socket = node.inputs[1]

        x -= 200

    # Vertex Color
    if mh.vertex_color:
        node = mh.node_tree.nodes.new('ShaderNodeVertexColor')
        node.layer_name = 'Col'
        node.location = x - 250, y - 240
        # Outputs
        mh.node_tree.links.new(vcolor_color_socket, node.outputs['Color'])
        if vcolor_alpha_socket is not None:
            mh.node_tree.links.new(vcolor_alpha_socket, node.outputs['Alpha'])

        x -= 280

    # Texture
    if base_color_texture is not None:
        texture(
            mh,
            tex_info=base_color_texture,
            label='BASE COLOR' if not is_diffuse else 'DIFFUSE',
            location=(x, y),
            color_socket=texture_color_socket,
            alpha_socket=texture_alpha_socket,
        )


# [Texture] => [Separate GB] => [Metal/Rough Factor] =>
def metallic_roughness(mh: MaterialHelper, location, metallic_socket, roughness_socket):
    x, y = location
    pbr = mh.pymat.pbr_metallic_roughness
    metal_factor = pbr.metallic_factor
    rough_factor = pbr.roughness_factor
    if metal_factor is None:
        metal_factor = 1.0
    if rough_factor is None:
        rough_factor = 1.0

    if pbr.metallic_roughness_texture is None:
        metallic_socket.default_value = metal_factor
        roughness_socket.default_value = rough_factor
        return

    if metal_factor != 1.0 or rough_factor != 1.0:
        # Mix metal factor
        if metal_factor != 1.0:
            node = mh.node_tree.nodes.new('ShaderNodeMath')
            node.label = 'Metallic Factor'
            node.location = x - 140, y
            node.operation = 'MULTIPLY'
            # Outputs
            mh.node_tree.links.new(metallic_socket, node.outputs[0])
            # Inputs
            metallic_socket = node.inputs[0]
            node.inputs[1].default_value = metal_factor

        # Mix rough factor
        if rough_factor != 1.0:
            node = mh.node_tree.nodes.new('ShaderNodeMath')
            node.label = 'Roughness Factor'
            node.location = x - 140, y - 200
            node.operation = 'MULTIPLY'
            # Outputs
            mh.node_tree.links.new(roughness_socket, node.outputs[0])
            # Inputs
            roughness_socket = node.inputs[0]
            node.inputs[1].default_value = rough_factor

        x -= 200

    # Separate RGB
    node = mh.node_tree.nodes.new('ShaderNodeSeparateRGB')
    node.location = x - 150, y - 75
    # Outputs
    mh.node_tree.links.new(metallic_socket, node.outputs['B'])
    mh.node_tree.links.new(roughness_socket, node.outputs['G'])
    # Inputs
    color_socket = node.inputs[0]

    x -= 200

    texture(
        mh,
        tex_info=pbr.metallic_roughness_texture,
        label='METALLIC ROUGHNESS',
        location=(x, y),
        is_data=True,
        color_socket=color_socket,
    )


# [Texture] => [Normal Map] =>
def normal(mh: MaterialHelper, location, normal_socket):
    x,y = location
    tex_info = mh.pymat.normal_texture

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
        label='NORMALMAP',
        location=(x, y),
        is_data=True,
        color_socket=color_socket,
    )


# [Texture] => [Separate R] =>
def occlusion(mh: MaterialHelper, location, occlusion_socket):
    x, y = location

    if mh.pymat.occlusion_texture is None:
        return

    # Separate RGB
    node = mh.node_tree.nodes.new('ShaderNodeSeparateRGB')
    node.location = x - 150, y - 75
    # Outputs
    mh.node_tree.links.new(occlusion_socket, node.outputs['R'])
    # Inputs
    color_socket = node.inputs[0]

    x -= 200

    texture(
        mh,
        tex_info=mh.pymat.occlusion_texture,
        label='OCCLUSION',
        location=(x, y),
        is_data=True,
        color_socket=color_socket,
    )


# => [Add Emission] => [Mix Alpha] => [Material Output]
def make_output_nodes(
    mh: MaterialHelper,
    location,
    shader_socket,
    make_emission_socket,
    make_alpha_socket,
):
    """
    Creates the Material Output node and connects shader_socket to it.
    If requested, it can also create places to hookup the emission/alpha
    in between shader_socket and the Output node too.

    :return: a pair containing the sockets you should put emission and alpha
    in (None if not requested).
    """
    x, y = location
    emission_socket = None
    alpha_socket = None

    # Create an Emission node and add it to the shader.
    if make_emission_socket:
        # Emission
        node = mh.node_tree.nodes.new('ShaderNodeEmission')
        node.location = x + 50, y + 250
        # Inputs
        emission_socket = node.inputs[0]
        # Outputs
        emission_output = node.outputs[0]

        # Add
        node = mh.node_tree.nodes.new('ShaderNodeAddShader')
        node.location = x + 250, y + 160
        # Inputs
        mh.node_tree.links.new(node.inputs[0], emission_output)
        mh.node_tree.links.new(node.inputs[1], shader_socket)
        # Outputs
        shader_socket = node.outputs[0]

        if make_alpha_socket:
            x += 200
            y += 175
        else:
            x += 380
            y += 125

    # Mix with a Transparent BSDF. Mixing factor is the alpha value.
    if make_alpha_socket:
        # Transparent BSDF
        node = mh.node_tree.nodes.new('ShaderNodeBsdfTransparent')
        node.location = x + 100, y - 350
        # Outputs
        transparent_out = node.outputs[0]

        # Mix
        node = mh.node_tree.nodes.new('ShaderNodeMixShader')
        node.location = x + 340, y - 180
        # Inputs
        alpha_socket = node.inputs[0]
        mh.node_tree.links.new(node.inputs[1], transparent_out)
        mh.node_tree.links.new(node.inputs[2], shader_socket)
        # Outputs
        shader_socket = node.outputs[0]


        x += 480
        y -= 210

    # Material output
    node = mh.node_tree.nodes.new('ShaderNodeOutputMaterial')
    node.location = x + 70, y + 10
    # Outputs
    mh.node_tree.links.new(node.inputs[0], shader_socket)

    return emission_socket, alpha_socket


def make_settings_node(mh):
    """
    Make a Group node with a hookup for Occlusion. No effect in Blender, but
    used to tell the exporter what the occlusion map should be.
    """
    node = mh.node_tree.nodes.new('ShaderNodeGroup')
    node.node_tree = get_settings_group()
    return node


def get_settings_group():
    gltf_node_group_name = get_gltf_node_name()
    if gltf_node_group_name in bpy.data.node_groups:
        gltf_node_group = bpy.data.node_groups[gltf_node_group_name]
    else:
        # Create a new node group
        gltf_node_group = bpy.data.node_groups.new(gltf_node_group_name, 'ShaderNodeTree')
        gltf_node_group.inputs.new("NodeSocketFloat", "Occlusion")
        gltf_node_group.nodes.new('NodeGroupOutput')
        gltf_node_group_input = gltf_node_group.nodes.new('NodeGroupInput')
        gltf_node_group_input.location = -200, 0
    return gltf_node_group
