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
from .gltf2_blender_texture import BlenderTextureInfo
from ...io.com.gltf2_io import MaterialPBRMetallicRoughness
from .gltf2_blender_pbrMetallicRoughness import BlenderPbr

class BlenderKHR_materials_unlit():
    """Blender KHR_materials_unlit extension."""
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("%s should not be instantiated" % cls)

    @staticmethod
    def create(gltf, material_index, unlit, mat_name, vertex_color):
        """KHR_materials_unlit creation."""
        engine = bpy.context.scene.render.engine
        if engine in ['CYCLES', 'BLENDER_EEVEE']:
            BlenderKHR_materials_unlit.create_nodetree(gltf, material_index, unlit, mat_name, vertex_color)

    @staticmethod
    def create_nodetree(gltf, material_index, unlit, mat_name, vertex_color):
        """Node tree creation."""
        material = bpy.data.materials[mat_name]
        material.use_nodes = True
        node_tree = material.node_tree

        pymaterial = gltf.data.materials[material_index]
        if pymaterial.pbr_metallic_roughness is None:
            # If no pbr material is set, we need to apply all default of pbr
            pbr = {}
            pbr["baseColorFactor"] = [1.0, 1.0, 1.0, 1.0]
            pbr["metallicFactor"] = 1.0
            pbr["roughnessFactor"] = 1.0
            pymaterial.pbr_metallic_roughness = MaterialPBRMetallicRoughness.from_dict(pbr)
            pymaterial.pbr_metallic_roughness.color_type = gltf.SIMPLE
            pymaterial.pbr_metallic_roughness.metallic_type = gltf.SIMPLE

        BlenderPbr.create_nodetree(gltf, pymaterial.pbr_metallic_roughness, mat_name, vertex_color, nodetype='unlit')
