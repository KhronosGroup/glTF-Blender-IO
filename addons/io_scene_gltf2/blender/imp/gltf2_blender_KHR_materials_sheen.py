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
from .gltf2_blender_image import BlenderImage
from ..exp.gltf2_blender_image import TmpImageGuard, make_temp_image_copy
import numpy as np
import bpy

def sheen(  mh, 
            location_sheen, 
            sheen_socket, 
            sheen_tint_socket,
            original_sheenColor_socket,
            original_sheenRoughness_socket,
            location_original_sheenColor,
            location_original_sheenRoughness
            ):
    x_sheen, y_sheen = location_sheen

    try:
        ext = mh.pymat.extensions['KHR_materials_sheen']
    except Exception:
        return

    sheen_color_factor = ext.get('sheenColorFactor', [0.0, 0.0, 0.0])
    sheen_color_texture = ext.get('sheenColorTexture')
    if sheen_color_texture is not None:
        sheen_color_texture = TextureInfo.from_dict(sheen_color_texture)

    sheen_roughness_factor = ext.get('sheenRoughnessFactor', 0.0)
    sheen_roughness_texture = ext.get('sheenRoughnessTexture')
    if sheen_roughness_texture is not None:
        sheen_roughness_texture = TextureInfo.from_dict(sheen_roughness_texture)

    # Retrieve base color image name
    try:
        tex_info = mh.pymat.pbr_metallic_roughness.base_color_texture
        pytexture = mh.gltf.data.textures[tex_info.index]
        pyimg = mh.gltf.data.images[pytexture.source]
        base_color_image_name = pyimg.blender_image_name
    except:
        base_color_image_name =  None

    base_color_not_linked = base_color_image_name is None
    base_color = np.array(mh.pymat.pbr_metallic_roughness.base_color_factor or [1, 1, 1])
    tex_base_color = mh.pymat.pbr_metallic_roughness.base_color_texture
    base_color = base_color[:3]

    # Currently, sheen roughness is not taken into account
    use_texture = sheen_color_texture is not None or base_color_not_linked is False

    # Before creating converted textures,
    # Also plug non converted data into glTF PBR Non Converted Extensions node
    original_sheen(  mh,
                        sheen_color_factor, 
                        sheen_color_texture, 
                        sheen_roughness_factor, 
                        sheen_roughness_texture,
                        original_sheenColor_socket,
                        original_sheenRoughness_socket,
                        location_original_sheenColor,
                        location_original_sheenRoughness
                        )

    if not use_texture:
        #TODOExt approximation must be discussed
        luminance = lambda c: 0.3 * c[0] + 0.6 * c[1] + 0.1 * c[2]
        sheen_socket.default_value = 1.0
        sheen_tint_socket.default_value = luminance(sheen_color_factor)
    else:
        # Need to create a texture
        # First, retrieve and create all images needed
        # Base Color is already created
        # SheenColorTexture is just created by original specular function
        sheencolor_image_name = None
        try:
            pytexture = mh.gltf.data.textures[sheen_color_texture.index]
            pyimg = mh.gltf.data.images[pytexture.source]
            sheencolor_image_name = pyimg.blender_image_name
        except:
            sheencolor_image_name =  None

        # SheenRoughnessTexture --> Not used for now

        stack3 = lambda v: np.dstack([v]*3)

        texts = {
            base_color_image_name : 'basecolor',
            sheencolor_image_name : 'sheen',
        }
        
        images = [(name, bpy.data.images[name]) for name in [base_color_image_name, sheencolor_image_name] if name is not None]
        if len(images) == 0:
            # So this is the sheen texture...
            width = bpy.data.images[sheencolor_image_name].size[0]
            height = bpy.data.images[sheencolor_image_name].size[1]
        else:
            width = max(image[1].size[0] for image in images)
            height = max(image[1].size[1] for image in images)

        buffers = {}
        for name, image in images:
            tmp_buf = np.empty(width * height * 4, np.float32)
            
            if image.size[0] == width and image.size[1] == height:
                image.pixels.foreach_get(tmp_buf)
            else:
                # Image is the wrong size; make a temp copy and scale it.
                with TmpImageGuard() as guard:
                    make_temp_image_copy(guard, src_image=image)
                    tmp_image = guard.image
                    tmp_image.scale(width, height)
                    tmp_image.pixels.foreach_get(tmp_buf)

            buffers[texts[name]] = np.reshape(tmp_buf, [width, height, 4])
            buffers[texts[name]] = buffers[texts[name]][:,:,:3]

            # Manage factors
            if name == base_color_image_name:
                buffers[texts[name]] *= base_color

            elif name == sheencolor_image_name:
                buffers[texts[name]] *= sheen_color_factor

        # Create buffer if there is no image
        if 'basecolor' not in buffers.keys():
            buffers['basecolor'] = np.full((width, height, 3), base_color)
        if 'sheen' not in buffers.keys():
            buffers['sheen'] = np.full((width, height, 3), sheen_color_factor)


        # Calculation
        #TODOExt approximation must be discussed
        luminance = lambda c: 0.3 * c[:,:,0] + 0.6 * c[:,:,1] + 0.1 * c[:,:,2]
        stack3 = lambda v: np.dstack([v]*3)
        lerp = lambda a, b, v: (1-v)*a + v*b

        sheen_socket.default_value = 1.0
        blender_sheen_tint = stack3(luminance(buffers['sheen']) * luminance(buffers['basecolor']))

        
        blender_sheen_tint = np.dstack((blender_sheen_tint, np.ones((height, width)))) # Set alpha to 1
        blender_sheen_tint = np.reshape(blender_sheen_tint, width * height * 4)
        # Create images in Blender, width and height are dummy values, then set packed file data
        blender_image_sheen_tint = bpy.data.images.new('Sheen Tint', width, height)
        blender_image_sheen_tint.pixels.foreach_set(np.float32(blender_sheen_tint))
        blender_image_sheen_tint.pack()

        # Create Textures in Blender
        tex_info = sheen_color_texture
        if tex_info is None:
            tex_info = tex_base_color
        if tex_info is None:
            tex_info = sheen_roughness_texture

        texture(
            mh,
            tex_info=tex_info,
            label='SHEEN TINT',
            location=(x_sheen, y_sheen),
            is_data=True,
            color_socket=sheen_tint_socket,
            forced_image=blender_image_sheen_tint
        )

def original_sheen(  mh,
                        sheenColorFactor,
                        tex_sheencolor_info, 
                        sheenRoughnessFactor, 
                        tex_sheenRoughness_info,
                        original_sheenColor_socket,
                        original_sheenRoughness_socket,
                        location_original_sheenColor,
                        location_original_sheenRoughness
                        ):

    x_sheenColor, y_sheenColor = location_original_sheenColor
    x_sheenRoughness, y_sheenRoughness = location_original_sheenRoughness

    if tex_sheencolor_info is None:
        sheenColorFactor = list(sheenColorFactor)
        sheenColorFactor.extend([1.0])
        original_sheenColor_socket.default_value = sheenColorFactor
    else:
        # Mix sheenColor factor
        sheenColorFactor = list(sheenColorFactor) + [1.0]
        if sheenColorFactor != [1.0, 1.0, 1.0, 1.0]:
            node = mh.node_tree.nodes.new('ShaderNodeMixRGB')
            node.label = 'sheenColor Factor'
            node.location = x_sheenColor - 140, y_sheenColor
            node.blend_type = 'MULTIPLY'
            # Outputs
            mh.node_tree.links.new(original_sheenColor_socket, node.outputs[0])
            # Inputs
            node.inputs['Fac'].default_value = 1.0
            original_sheenColor_socket = node.inputs['Color1']
            node.inputs['Color2'].default_value = sheenColorFactor
            x_sheenColor -= 200

        texture(
            mh,
            tex_info=tex_sheencolor_info,
            label='SHEEN COLOR',
            location=(x_sheenColor, y_sheenColor),
            color_socket=original_sheenColor_socket
            )

    if tex_sheenRoughness_info is None:
        original_sheenRoughness_socket.default_value = sheenRoughnessFactor
    else:
         # Mix sheenRoughness factor
        if sheenRoughnessFactor != 1.0:
            node = mh.node_tree.nodes.new('ShaderNodeMath')
            node.label = 'shennRoughness Factor'
            node.location = x_sheenRoughness - 140, y_sheenRoughness
            node.operation = 'MULTIPLY'
            # Outputs
            mh.node_tree.links.new(original_sheenRoughness_socket, node.outputs[0])
            # Inputs
            original_sheenRoughness_socket = node.inputs[0]
            node.inputs[1].default_value = sheenRoughnessFactor
            x_sheenRoughness -= 200

        texture(
            mh,
            tex_info=tex_sheenRoughness_info,
            label='SHEEN ROUGHNESS',
            location=(x_sheenRoughness, y_sheenRoughness),
            is_data=True,
            color_socket=None,
            alpha_socket=original_sheenRoughness_socket
            )