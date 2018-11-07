# Copyright 2018 The glTF-Blender-IO authors.
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
from .gltf2_blender_texture import BlenderTextureInfo


class BlenderOcclusionMap():

    @staticmethod
    def create(gltf, material_idx):
        engine = bpy.context.scene.render.engine
        if engine in ['CYCLES', 'BLENDER_EEVEE']:
            BlenderOcclusionMap.create_nodetree(gltf, material_idx)

    def create_nodetree(gltf, material_idx):

        pymaterial = gltf.data.materials[material_idx]

        BlenderTextureInfo.create(gltf, pymaterial.occlusion_texture.index)

        # Pack texture, but doesn't use it for now. Occlusion is calculated from Cycles.
        bpy.data.images[gltf.data.images[gltf.data.textures[
            pymaterial.occlusion_texture.index
        ].source].blender_image_name].use_fake_user = True
