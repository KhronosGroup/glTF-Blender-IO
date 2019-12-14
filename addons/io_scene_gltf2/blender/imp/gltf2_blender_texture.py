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
from .gltf2_blender_image import BlenderImage
from ..com.gltf2_blender_conversion import texture_transform_gltf_to_blender
from io_scene_gltf2.io.com.gltf2_io import Sampler
from io_scene_gltf2.io.com.gltf2_io_debug import print_console
from io_scene_gltf2.io.com.gltf2_io_constants import TextureFilter, TextureWrap

def texture(
    mh,
    tex_info,
    location, # Upper-right corner of the TexImage node
    label, # Label for the TexImg node
    color_socket,
    alpha_socket=None,
    is_data=False,
):
    """Creates nodes for a TextureInfo and hooks up the color/alpha outputs."""
    x, y = location

    # Image Texture
    tex_img = mh.node_tree.nodes.new('ShaderNodeTexImage')
    tex_img.location = x - 240, y
    tex_img.label = label
    # Get image
    pytexture = mh.gltf.data.textures[tex_info.index]
    if pytexture.source is not None:
        BlenderImage.create(mh.gltf, pytexture.source)
        pyimg = mh.gltf.data.images[pytexture.source]
        blender_image_name = pyimg.blender_image_name
        if blender_image_name:
            tex_img.image = bpy.data.images[blender_image_name]
    # Set colorspace for data images
    if is_data:
        if bpy.app.version < (2, 80, 0):
            tex_img.color_space = 'NONE'
        else:
            if tex_img.image:
                tex_img.image.colorspace_settings.is_data = True
    # Set wrapping/filtering
    if pytexture.sampler is not None:
        pysampler = mh.gltf.data.samplers[pytexture.sampler]
    else:
        pysampler = Sampler.from_dict({})
    set_filtering(tex_img, pysampler)
    set_wrap_mode(tex_img, pysampler)
    # Outputs
    mh.node_tree.links.new(color_socket, tex_img.outputs['Color'])
    if alpha_socket is not None:
        mh.node_tree.links.new(alpha_socket, tex_img.outputs['Alpha'])
    # Inputs
    uv_socket = tex_img.inputs[0]

    x -= 340

    # UV Transform (for KHR_texture_transform)
    mapping = mh.node_tree.nodes.new('ShaderNodeMapping')
    if bpy.app.version < (2, 81, 8):
        mapping.location = x - 320, y
    else:
        mapping.location = x - 160, y + 30
    mapping.vector_type = 'POINT'
    if tex_info.extensions and 'KHR_texture_transform' in tex_info.extensions:
        transform = tex_info.extensions['KHR_texture_transform']
        transform = texture_transform_gltf_to_blender(transform)
        if bpy.app.version < (2, 81, 8):
            mapping.translation[0] = transform['offset'][0]
            mapping.translation[1] = transform['offset'][1]
            mapping.rotation[2] = transform['rotation']
            mapping.scale[0] = transform['scale'][0]
            mapping.scale[1] = transform['scale'][1]
        else:
            mapping.inputs['Location'].default_value[0] = transform['offset'][0]
            mapping.inputs['Location'].default_value[1] = transform['offset'][1]
            mapping.inputs['Rotation'].default_value[2] = transform['rotation']
            mapping.inputs['Scale'].default_value[0] = transform['scale'][0]
            mapping.inputs['Scale'].default_value[1] = transform['scale'][1]
    # Outputs
    mh.node_tree.links.new(uv_socket, mapping.outputs[0])
    # Inputs
    uv_socket = mapping.inputs[0]

    if bpy.app.version < (2, 81, 8):
        x -= 420
    else:
        x -= 260

    # UV Map
    uv_map = mh.node_tree.nodes.new('ShaderNodeUVMap')
    uv_map.location = x - 160, y - 70
    # Get UVMap
    uv_idx = tex_info.tex_coord or 0
    try:
        uv_idx = tex_info.extensions['KHR_texture_transform']['texCoord']
    except Exception:
        pass
    uv_map.uv_map = 'UVMap' if uv_idx == 0 else 'UVMap.%03d' % uv_idx
    # Outputs
    mh.node_tree.links.new(uv_socket, uv_map.outputs[0])

def set_filtering(tex_img, pysampler):
    """Set the filtering/interpolation on an Image Texture from the glTf sampler."""
    minf = pysampler.min_filter
    magf = pysampler.mag_filter

    # Ignore mipmapping
    if minf in [TextureFilter.NearestMipmapNearest, TextureFilter.NearestMipmapLinear]:
        minf = TextureFilter.Nearest
    elif minf in [TextureFilter.LinearMipmapNearest, TextureFilter.LinearMipmapLinear]:
        minf = TextureFilter.Linear

    # If both are nearest or the only specified one was nearest, use nearest.
    if (minf, magf) in [
        (TextureFilter.Nearest, TextureFilter.Nearest),
        (TextureFilter.Nearest, None),
        (None, TextureFilter.Nearest),
    ]:
        tex_img.interpolation = 'Closest'
    else:
        tex_img.interpolation = 'Linear'

def set_wrap_mode(tex_img, pysampler):
    """Set the extension on an Image Texture node from the pysampler."""
    wrap_s = pysampler.wrap_s
    wrap_t = pysampler.wrap_t

    if wrap_s is None:
        wrap_s = TextureWrap.Repeat
    if wrap_t is None:
        wrap_t = TextureWrap.Repeat

    # The extension property on the Image Texture node can only handle the case
    # where both directions are the same and are either REPEAT or CLAMP_TO_EDGE.
    if (wrap_s, wrap_t) == (TextureWrap.Repeat, TextureWrap.Repeat):
        extension = TextureWrap.Repeat
    elif (wrap_s, wrap_t) == (TextureWrap.ClampToEdge, TextureWrap.ClampToEdge):
        extension = TextureWrap.ClampToEdge
    else:
        print_console('WARNING',
            'texture wrap mode unsupported: (%s, %s)' % (wrap_name(wrap_s), wrap_name(wrap_t)),
        )
        # Default to repeat
        extension = TextureWrap.Repeat

    if extension == TextureWrap.Repeat:
        tex_img.extension = 'REPEAT'
    elif extension == TextureWrap.ClampToEdge:
        tex_img.extension = 'EXTEND'

def wrap_name(wrap):
    if wrap == TextureWrap.ClampToEdge: return 'CLAMP_TO_EDGE'
    if wrap == TextureWrap.MirroredRepeat: return 'MIRRORED_REPEAT'
    if wrap == TextureWrap.Repeat: return 'REPEAT'
    return 'UNKNOWN (%s)' % wrap
