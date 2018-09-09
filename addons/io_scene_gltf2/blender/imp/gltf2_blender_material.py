"""
 * ***** BEGIN GPL LICENSE BLOCK *****
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License
 * as published by the Free Software Foundation; either version 2
 * of the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software Foundation,
 * Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
 *
 * Contributor(s): Julien Duroure.
 *
 * ***** END GPL LICENSE BLOCK *****
 """

import bpy
from .gltf2_blender_pbrMetallicRoughness import *
from .gltf2_blender_KHR_materials_pbrSpecularGlossiness import *
from .gltf2_blender_map_emissive import *
from .gltf2_blender_map_normal import *
from .gltf2_blender_map_occlusion import *

class BlenderMaterial():

    @staticmethod
    def create(gltf, material_idx):

        pymaterial = gltf.data.materials[material_idx]

        if pymaterial.name is not None:
            name = pymaterial.name
        else:
            name = "Material_" + str(pymaterial.index)

        mat = bpy.data.materials.new(name)
        pymaterial.blender_material = mat.name

        if hasattr(pymaterial, 'KHR_materials_pbrSpecularGlossiness'): #TODO_SPLIT
            BlenderKHR_materials_pbrSpecularGlossiness.create(pymaterial.KHR_materials_pbrSpecularGlossiness, mat.name)
        else:
            # create pbr material
            BlenderPbr.create(gltf, pymaterial.pbr_metallic_roughness, mat.name)

        # add emission map if needed
        if pymaterial.emissivemap:
            BlenderEmissiveMap.create(pymaterial.emissivemap, mat.name)

        # add normal map if needed
        if pymaterial.normalmap:
            BlenderNormalMap.create(pymaterial.normalmap, mat.name)

        # add occlusion map if needed
        # will be pack, but not used
        if pymaterial.occlusionmap:
            BlenderOcclusionMap.create(pymaterial.occlusionmap, mat.name)

    @staticmethod
    def set_uvmap(pymaterial, prim, obj):
        node_tree = bpy.data.materials[pymaterial.blender_material].node_tree
        uvmap_nodes =  [node for node in node_tree.nodes if node.type == 'UVMAP']
        for uvmap_node in uvmap_nodes:
            if uvmap_node["gltf2_texcoord"] in prim.blender_texcoord.keys():
                uvmap_node.uv_map = prim.blender_texcoord[uvmap_node["gltf2_texcoord"]]
