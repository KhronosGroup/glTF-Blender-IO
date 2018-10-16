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
from .gltf2_blender_pbrMetallicRoughness import *
from .gltf2_blender_KHR_materials_pbrSpecularGlossiness import *
from .gltf2_blender_map_emissive import *
from .gltf2_blender_map_normal import *
from .gltf2_blender_map_occlusion import *

class BlenderMaterial():

    @staticmethod
    def create(gltf, material_idx, vertex_color):

        pymaterial = gltf.data.materials[material_idx]

        if pymaterial.name is not None:
            name = pymaterial.name
        else:
            name = "Material_" + str(material_idx)

        mat = bpy.data.materials.new(name)
        pymaterial.blender_material = mat.name

        if pymaterial.extensions is not None and 'KHR_materials_pbrSpecularGlossiness' in pymaterial.extensions.keys():
            BlenderKHR_materials_pbrSpecularGlossiness.create(gltf, pymaterial.extensions['KHR_materials_pbrSpecularGlossiness'], mat.name, vertex_color)
        else:
            # create pbr material
            BlenderPbr.create(gltf, pymaterial.pbr_metallic_roughness, mat.name, vertex_color)

        # add emission map if needed
        if pymaterial.emissive_texture is not None:
            BlenderEmissiveMap.create(gltf, material_idx)

        # add normal map if needed
        if pymaterial.normal_texture is not None:
            BlenderNormalMap.create(gltf, material_idx)

        # add occlusion map if needed
        # will be pack, but not used
        if pymaterial.occlusion_texture is not None:
            BlenderOcclusionMap.create(gltf, material_idx)

    @staticmethod
    def set_uvmap(gltf, material_idx, prim, obj):
        pymaterial = gltf.data.materials[material_idx]

        node_tree = bpy.data.materials[pymaterial.blender_material].node_tree
        uvmap_nodes =  [node for node in node_tree.nodes if node.type in ['UVMAP', 'NORMAL_MAP']]
        for uvmap_node in uvmap_nodes:
            if uvmap_node["gltf2_texcoord"] in prim.blender_texcoord.keys():
                uvmap_node.uv_map = prim.blender_texcoord[uvmap_node["gltf2_texcoord"]]
