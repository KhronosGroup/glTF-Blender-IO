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

from .gltf2_blender_image import BlenderImage


class BlenderTextureInfo():
    """Blender Texture info."""
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("%s should not be instantiated" % cls)

    @staticmethod
    def create(gltf, pytextureinfo, dict_=False):
        """Create Texture info."""
        extension_text_transform_used = {}

        if dict_ is True: # coming from KHR_materials_pbrSpecularGlossiness
            if 'extensions' in pytextureinfo.keys() \
            and 'KHR_texture_transform' in pytextureinfo['extensions'].keys():
                extension_text_transform_used = pytextureinfo['extensions']['KHR_texture_transform']
            BlenderTexture.create(gltf, pytextureinfo['index'], extension_text_transform_used)
        else:
            if pytextureinfo.extensions is not None \
            and 'KHR_texture_transform' in pytextureinfo.extensions.keys():
                extension_text_transform_used = pytextureinfo.extensions['KHR_texture_transform']
            BlenderTexture.create(gltf, pytextureinfo.index, extension_text_transform_used)

class BlenderTexture():
    """Blender Texture."""
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("%s should not be instantiated" % cls)

    @staticmethod
    def create(gltf, pytexture_idx, tex_transform):
        """Create texture."""
        pytexture = gltf.data.textures[pytexture_idx]
        BlenderImage.create(gltf, pytexture.source, pytexture_idx, tex_transform)
