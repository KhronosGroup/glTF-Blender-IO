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

def sheen(mh, location_sheen, sheen_socket, sheen_tint_socket):
    x_sheen, x_sheen = location_sheen

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

