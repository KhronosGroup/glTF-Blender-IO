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

def make_texture_block(gltf, node_tree, tex_info, location, label, name=None, colorspace=None):
    """Creates a block of Shader Nodes for the given TextureInfo.
    Will look like this:
        [UV Map] -> [Mapping] -> [Image Texture]
    The [Image Texture] node is placed at the given location.
    The [Image Texture] node is given the given label.
    The [Image Texture] node is returned.
    """
    # Image Texture (samples image)

    tex_img = node_tree.nodes.new('ShaderNodeTexImage')
    if name:
        tex_img.name = name + '.tex_img'
    tex_img.location = location
    tex_img.label = label

    pytexture = gltf.data.textures[tex_info.index]

    if pytexture.source is not None:
        BlenderImage.create(gltf, pytexture.source)
        pyimg = gltf.data.images[pytexture.source]
        blender_image_name = pyimg.blender_image_name
        if blender_image_name:
            tex_img.image = bpy.data.images[blender_image_name]

    if colorspace == 'NONE':
        if bpy.app.version < (2, 80, 0):
            tex_img.color_space = 'NONE'
        else:
            if tex_img.image:
                tex_img.image.colorspace_settings.is_data = True

    # TODO do sampler

    # Mapping (transforms UVs for KHR_texture_transform)

    mapping = node_tree.nodes.new('ShaderNodeMapping')
    if name:
        mapping.name = name + '.mapping'
    mapping.location = location[0] - 500, location[1]
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

    # UV Map (retrieves UV)

    uv_map = node_tree.nodes.new('ShaderNodeUVMap')
    if name:
        uv_map.name = name + '.uv_map'
    uv_map.location = location[0] - 1000, location[1]

    texcoord_idx = tex_info.tex_coord or 0
    if tex_info.extensions and 'KHR_texture_transform' in tex_info.extensions:
        if 'texCoord' in tex_info.extensions['KHR_texture_transform']:
            texcoord_idx = tex_info.extensions['KHR_texture_transform']['texCoord']

    uv_map.uv_map = 'TEXCOORD_%d' % texcoord_idx

    # Links
    node_tree.links.new(mapping.inputs[0], uv_map.outputs[0])
    node_tree.links.new(tex_img.inputs[0], mapping.outputs[0])

    return tex_img
