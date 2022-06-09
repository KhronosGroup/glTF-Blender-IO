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

def sheen(mh, location_sheen, sheen_socket, sheen_tint_socket):
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

    if not use_texture:
        #TODOExt approximation must be discussed
        luminance = lambda c: 0.3 * c[0] + 0.6 * c[1] + 0.1 * c[2]
        sheen_socket.default_value = 1.0
        sheen_tint_socket.default_value = luminance(sheen_color_factor)
    else:
        # Need to create a texture
        # First, retrieve and create all images needed
        # Base Color is already created
        # SheenColorTexture --> Need to be created
        sheencolor_image_name = None
        if sheen_color_texture is not None:
            tex_sheen_color = mh.gltf.data.textures[sheen_color_texture.index]
            if tex_sheen_color.source is not None:
                BlenderImage.create(mh.gltf, tex_sheen_color.source)

                # Retrieve image just created
                pyimg = mh.gltf.data.images[tex_sheen_color.source]
                sheencolor_image_name = pyimg.blender_image_name

        stack3 = lambda v: np.dstack([v]*3)

        # SheenRoughnessTexture --> Not used for now
        
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