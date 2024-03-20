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

from re import M
import bpy
from ...io.com.gltf2_io_constants import GLTF_IOR
from ...io.com.gltf2_io import TextureInfo, MaterialPBRMetallicRoughness
from ..com.gltf2_blender_material_helpers import get_gltf_node_name, create_settings_group
from .gltf2_blender_texture import texture
from .gltf2_blender_KHR_materials_anisotropy import anisotropy
from .gltf2_blender_material_utils import \
    MaterialHelper, scalar_factor_and_texture, color_factor_and_texture, normal_map


def pbr_metallic_roughness(mh: MaterialHelper):
    """Creates node tree for pbrMetallicRoughness materials."""
    pbr_node = mh.nodes.new('ShaderNodeBsdfPrincipled')
    out_node = mh.nodes.new('ShaderNodeOutputMaterial')
    pbr_node.location = 10, 300
    out_node.location = 300, 300
    mh.links.new(pbr_node.outputs[0], out_node.inputs[0])

    need_volume_node = False  # need a place to attach volume?
    need_settings_node = False  # need a place to attach occlusion/thickness?

    if mh.pymat.occlusion_texture is not None:
        need_settings_node = True

    if volume_ext := mh.get_ext('KHR_materials_volume'):
        if volume_ext.get('thicknessFactor', 0) != 0:
            need_volume_node = True
            need_settings_node = True

    if need_settings_node:
        mh.settings_node = make_settings_node(mh)
        mh.settings_node.location = 40, -370
        mh.settings_node.width = 180

    if need_volume_node:
        volume_node = mh.nodes.new('ShaderNodeVolumeAbsorption')
        volume_node.location = 40, -520 if need_settings_node else -370
        mh.links.new(out_node.inputs[1], volume_node.outputs[0])

    locs = calc_locations(mh)

    emission(
        mh,
        location=locs['emission'],
        color_socket=pbr_node.inputs['Emission Color'],
        strength_socket=pbr_node.inputs['Emission Strength'],
    )

    base_color(
        mh,
        location=locs['base_color'],
        color_socket=pbr_node.inputs['Base Color'],
        alpha_socket=pbr_node.inputs['Alpha'],
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
        occlusion(
            mh,
            location=locs['occlusion'],
            occlusion_socket=mh.settings_node.inputs['Occlusion'],
        )

    clearcoat(mh, locs, pbr_node)

    transmission(mh, locs, pbr_node)

    if need_volume_node:
        volume(
            mh,
            location=locs['volume_thickness'],
            volume_node=volume_node,
            thickness_socket=mh.settings_node.inputs[1] if mh.settings_node else None
        )

    specular(mh, locs, pbr_node)

    anisotropy(
        mh,
        location=locs['anisotropy'],
        anisotropy_socket=pbr_node.inputs['Anisotropic'],
        anisotropy_rotation_socket=pbr_node.inputs['Anisotropic Rotation'],
        anisotropy_tangent_socket=pbr_node.inputs['Tangent']
    )

    sheen(mh, locs, pbr_node)

    # IOR
    ior_ext = mh.get_ext('KHR_materials_ior', {})
    ior = ior_ext.get('ior', GLTF_IOR)
    pbr_node.inputs['IOR'].default_value = ior


def clearcoat(mh, locs, pbr_node):
    ext = mh.get_ext('KHR_materials_clearcoat', {})

    scalar_factor_and_texture(
        mh,
        location=locs['clearcoat'],
        label='Clearcoat',
        socket=pbr_node.inputs['Coat Weight'],
        factor=ext.get('clearcoatFactor', 0),
        tex_info=ext.get('clearcoatTexture'),
        channel=0,  # Red
    )

    scalar_factor_and_texture(
        mh,
        location=locs['clearcoat_roughness'],
        label='Clearcoat Roughness',
        socket=pbr_node.inputs['Coat Roughness'],
        factor=ext.get('clearcoatRoughnessFactor', 0),
        tex_info=ext.get('clearcoatRoughnessTexture'),
        channel=1,  # Green
    )

    normal_map(
        mh,
        location=locs['clearcoat_normal'],
        label='Clearcoat Normal',
        socket=pbr_node.inputs['Coat Normal'],
        tex_info=ext.get('clearcoatNormalTexture'),
    )


def transmission(mh, locs, pbr_node):
    ext = mh.get_ext('KHR_materials_transmission', {})
    factor = ext.get('transmissionFactor', 0)

    if factor > 0:
        # Activate screen refraction (for Eevee)
        mh.mat.use_screen_refraction = True

    scalar_factor_and_texture(
        mh,
        location=locs['transmission'],
        label='Transmission',
        socket=pbr_node.inputs['Transmission Weight'],
        factor=factor,
        tex_info=ext.get('transmissionTexture'),
        channel=0,  # Red
    )


def volume(mh, location, volume_node, thickness_socket):
    # Based on https://github.com/KhronosGroup/glTF-Blender-IO/issues/1454#issuecomment-928319444
    ext = mh.get_ext('KHR_materials_volume', {})

    color = ext.get('attenuationColor', [1, 1, 1])
    volume_node.inputs[0].default_value = [*color, 1]

    distance = ext.get('attenuationDistance', float('inf'))
    density = 1 / distance
    volume_node.inputs[1].default_value = density

    scalar_factor_and_texture(
        mh,
        location=location,
        label='Thickness',
        socket=thickness_socket,
        factor=ext.get('thicknessFactor', 0),
        tex_info=ext.get('thicknessTexture'),
        channel=1,  # Green
    )


def specular(mh, locs, pbr_node):
    ext = mh.get_ext('KHR_materials_specular', {})

    # blender.IORLevel = 0.5 * gltf.specular
    scalar_factor_and_texture(
        mh,
        location=locs['specularTexture'],
        label='Specular',
        socket=pbr_node.inputs['Specular IOR Level'],
        factor=0.5 * ext.get('specularFactor', 1),
        tex_info=ext.get('specularTexture'),
        channel=4,  # Alpha
    )

    color_factor_and_texture(
        mh,
        location=locs['specularColorTexture'],
        label='Specular Color',
        socket=pbr_node.inputs['Specular Tint'],
        factor=ext.get('specularColorFactor', [1, 1, 1]),
        tex_info=ext.get('specularColorTexture'),
    )


def sheen(mh, locs, pbr_node):
    ext = mh.get_ext('KHR_materials_sheen')
    if ext is None:
        return

    pbr_node.inputs['Sheen Weight'].default_value = 1

    color_factor_and_texture(
        mh,
        location=locs['sheenColorTexture'],
        label='Sheen Color',
        socket=pbr_node.inputs['Sheen Tint'],
        factor=ext.get('sheenColorFactor', [0, 0, 0]),
        tex_info=ext.get('sheenColorTexture'),
    )

    scalar_factor_and_texture(
        mh,
        location=locs['sheenRoughnessTexture'],
        label='Sheen Roughness',
        socket=pbr_node.inputs['Sheen Roughness'],
        factor=ext.get('sheenRoughnessFactor', 0),
        tex_info=ext.get('sheenRoughnessTexture'),
        channel=4,  # Alpha
    )


def calc_locations(mh):
    """Calculate locations to place each bit of the node graph at."""
    # Lay the blocks out top-to-bottom, aligned on the right
    x = -200
    y = 0
    height = 460  # height of each block
    locs = {}

    clearcoat_ext = mh.get_ext('KHR_materials_clearcoat', {})
    transmission_ext = mh.get_ext('KHR_materials_transmission', {})
    volume_ext = mh.get_ext('KHR_materials_volume', {})
    specular_ext = mh.get_ext('KHR_materials_specular', {})
    anisotropy_ext = mh.get_ext('KHR_materials_anisotropy', {})
    sheen_ext = mh.get_ext('KHR_materials_sheen', {})

    locs['base_color'] = (x, y)
    if mh.pymat.pbr_metallic_roughness.base_color_texture is not None or mh.vertex_color:
        y -= height
    locs['metallic_roughness'] = (x, y)
    if mh.pymat.pbr_metallic_roughness.metallic_roughness_texture is not None:
        y -= height
    locs['transmission'] = (x, y)
    if 'transmissionTexture' in transmission_ext:
        y -= height
    locs['normal'] = (x, y)
    if mh.pymat.normal_texture is not None:
        y -= height
    locs['specularTexture'] = (x, y)
    if 'specularTexture' in specular_ext:
        y -= height
    locs['specularColorTexture'] = (x, y)
    if 'specularColorTexture' in specular_ext:
        y -= height
    locs['anisotropy'] = (x, y)
    if 'anisotropyTexture' in anisotropy_ext:
        y -= height
    locs['sheenRoughnessTexture'] = (x, y)
    if 'sheenRoughnessTexture' in sheen_ext:
        y -= height
    locs['sheenColorTexture'] = (x, y)
    if 'sheenColorTexture' in sheen_ext:
        y -= height
    locs['clearcoat'] = (x, y)
    if 'clearcoatTexture' in clearcoat_ext:
        y -= height
    locs['clearcoat_roughness'] = (x, y)
    if 'clearcoatRoughnessTexture' in clearcoat_ext:
        y -= height
    locs['clearcoat_normal'] = (x, y)
    if 'clearcoatNormalTexture' in clearcoat_ext:
        y -= height
    locs['emission'] = (x, y)
    if mh.pymat.emissive_texture is not None:
        y -= height
    locs['occlusion'] = (x, y)
    if mh.pymat.occlusion_texture is not None:
        y -= height
    locs['volume_thickness'] = (x, y)
    if 'thicknessTexture' in volume_ext:
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
def emission(mh: MaterialHelper, location, color_socket, strength_socket):
    factor = mh.pymat.emissive_factor or [0, 0, 0]
    ext = mh.get_ext('KHR_materials_emissive_strength', {})
    strength = ext.get('emissiveStrength', 1)

    if factor[0] == factor[1] == factor[2]:
        # Fold greyscale factor into strength
        strength *= factor[0]
        factor = [1, 1, 1]

    color_factor_and_texture(
        mh,
        location,
        label='Emissive',
        socket=color_socket,
        factor=factor,
        tex_info=mh.pymat.emissive_texture,
    )
    strength_socket.default_value = strength


#      [Texture] => [Mix Colors] => [Color Factor] =>
# [Vertex Color] => [Mix Alphas] => [Alpha Factor] => [Alpha Clip] =>
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
        base_color_factor = pbr.base_color_factor or [1, 1, 1, 1]
        base_color_texture = pbr.base_color_texture
    else:
        # Handle pbrSpecularGlossiness's diffuse with this function too,
        # since it's almost exactly the same as base color.
        ext = mh.get_ext('KHR_materials_pbrSpecularGlossiness')
        base_color_factor = ext.get('diffuseFactor', [1, 1, 1, 1])
        base_color_texture = ext.get('diffuseTexture')
        if base_color_texture is not None:
            base_color_texture = TextureInfo.from_dict(base_color_texture)

    color_factor = base_color_factor[:3]
    alpha_factor = base_color_factor[3]

    alpha_mode = mh.pymat.alpha_mode or 'OPAQUE'
    alpha_cutoff = mh.pymat.alpha_cutoff
    alpha_cutoff = 0.5 if alpha_cutoff is None else alpha_cutoff

    # Only factor
    if base_color_texture is None and not mh.vertex_color:
        color_socket.default_value = [*color_factor, 1]

        if alpha_socket:
            if alpha_mode == 'OPAQUE':
                alpha_factor = 1
            elif alpha_mode == 'MASK':
                alpha_factor = 1 if alpha_factor >= alpha_cutoff else 0

            alpha_socket.default_value = alpha_factor

        return

    # Opaque materials don't use the alpha socket
    if alpha_socket and alpha_mode == 'OPAQUE':
        alpha_socket.default_value = 1
        alpha_socket = None

    # Perform alpha clipping
    # alpha = if alpha >= cutoff then 1 else 0
    if alpha_socket and alpha_mode == 'MASK':
        if alpha_cutoff == 0:
            alpha_socket.default_value = 1
            alpha_socket = None
        elif alpha_cutoff > 1:
            alpha_socket.default_value = 0
            alpha_socket = None
        else:
            # Do 1 - (alpha < cutoff), since there's no >= node

            frame = mh.node_tree.nodes.new('NodeFrame')
            frame.label = 'Alpha Clip'

            node = mh.node_tree.nodes.new('ShaderNodeMath')
            node.location = x - 140, y - 230
            node.parent = frame
            # Outputs
            mh.node_tree.links.new(alpha_socket, node.outputs[0])
            # Inputs
            node.operation = 'SUBTRACT'
            node.inputs[0].default_value = 1
            alpha_socket = node.inputs[1]

            x -= 200

            node = mh.node_tree.nodes.new('ShaderNodeMath')
            node.location = x - 140, y - 230
            node.parent = frame
            # Outputs
            mh.node_tree.links.new(alpha_socket, node.outputs[0])
            # Inputs
            node.operation = 'LESS_THAN'
            alpha_socket = node.inputs[0]
            node.inputs[1].default_value = alpha_cutoff

            x -= 200

    # Mix in base color factor
    needs_color_factor = color_factor != [1, 1, 1]
    needs_alpha_factor = alpha_factor != 1 and alpha_socket
    if needs_color_factor or needs_alpha_factor:
        if needs_color_factor:
            node = mh.node_tree.nodes.new('ShaderNodeMix')
            node.label = 'Color Factor'
            node.data_type = "RGBA"
            node.location = x - 140, y
            node.blend_type = 'MULTIPLY'
            # Outputs
            mh.node_tree.links.new(color_socket, node.outputs[2])
            # Inputs
            node.inputs['Factor'].default_value = 1.0
            color_socket = node.inputs[6]
            node.inputs[7].default_value = [*color_factor, 1]

        if needs_alpha_factor:
            node = mh.node_tree.nodes.new('ShaderNodeMath')
            node.label = 'Alpha Factor'
            node.location = x - 140, y - 230
            # Outputs
            mh.node_tree.links.new(alpha_socket, node.outputs[0])
            # Inputs
            node.operation = 'MULTIPLY'
            alpha_socket = node.inputs[0]
            node.inputs[1].default_value = alpha_factor

        x -= 200

    # These are where the texture/vertex color node will put its output.
    texture_color_socket = color_socket
    texture_alpha_socket = alpha_socket
    vcolor_color_socket = color_socket
    vcolor_alpha_socket = alpha_socket

    # Mix texture and vertex color together
    if base_color_texture is not None and mh.vertex_color:
        node = mh.node_tree.nodes.new('ShaderNodeMix')
        node.label = 'Mix Vertex Color'
        node.data_type = 'RGBA'
        node.location = x - 140, y
        node.blend_type = 'MULTIPLY'
        # Outputs
        mh.node_tree.links.new(color_socket, node.outputs[2])
        # Inputs
        node.inputs['Factor'].default_value = 1.0
        texture_color_socket = node.inputs[6]
        vcolor_color_socket = node.inputs[7]

        if alpha_socket is not None:
            node = mh.node_tree.nodes.new('ShaderNodeMath')
            node.label = 'Mix Vertex Alpha'
            node.location = x - 140, y - 230
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
        # Do not set the layer name, so rendered one will be used (At import => The first one)
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
    node = mh.node_tree.nodes.new('ShaderNodeSeparateColor')
    node.location = x - 150, y - 75
    # Outputs
    mh.node_tree.links.new(metallic_socket, node.outputs['Blue'])
    mh.node_tree.links.new(roughness_socket, node.outputs['Green'])
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
    normal_map(
        mh,
        location=location,
        label='Normal Map',
        socket=normal_socket,
        tex_info=mh.pymat.normal_texture,
    )


# [Texture] => [Separate R] => [Mix Strength] =>
def occlusion(mh: MaterialHelper, location, occlusion_socket):
    x, y = location

    if mh.pymat.occlusion_texture is None:
        return

    strength = mh.pymat.occlusion_texture.strength
    if strength is None: strength = 1.0
    if strength != 1.0:
        # Mix with white
        node = mh.node_tree.nodes.new('ShaderNodeMix')
        node.label = 'Occlusion Strength'
        node.data_type = 'RGBA'
        node.location = x - 140, y
        node.blend_type = 'MIX'
        # Outputs
        mh.node_tree.links.new(occlusion_socket, node.outputs[0])
        # Inputs
        node.inputs['Factor'].default_value = strength
        node.inputs[6].default_value = [1, 1, 1, 1]
        occlusion_socket = node.inputs[7]

        x -= 200

    # Separate RGB
    node = mh.node_tree.nodes.new('ShaderNodeSeparateColor')
    node.location = x - 150, y - 75
    # Outputs
    mh.node_tree.links.new(occlusion_socket, node.outputs['Red'])
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
        gltf_node_group = create_settings_group(gltf_node_group_name)
    return gltf_node_group
