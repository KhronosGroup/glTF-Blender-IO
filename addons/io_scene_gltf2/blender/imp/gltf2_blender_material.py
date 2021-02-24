# Copyright 2018-2021 The glTF-Blender-IO authors.
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

from ..com.gltf2_blender_extras import set_extras
from .gltf2_blender_pbrMetallicRoughness import MaterialHelper, pbr_metallic_roughness
from .gltf2_blender_KHR_materials_pbrSpecularGlossiness import pbr_specular_glossiness
from .gltf2_blender_KHR_materials_unlit import unlit


class BlenderMaterial():
    """Blender Material."""
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("%s should not be instantiated" % cls)

    @staticmethod
    def create(gltf, material_idx, vertex_color):
        """Material creation."""
        pymaterial = gltf.data.materials[material_idx]

        name = pymaterial.name
        if name is None:
            name = "Material_" + str(material_idx)

        mat = bpy.data.materials.new(name)
        pymaterial.blender_material[vertex_color] = mat.name

        set_extras(mat, pymaterial.extras)
        BlenderMaterial.set_double_sided(pymaterial, mat)
        BlenderMaterial.set_alpha_mode(pymaterial, mat)
        BlenderMaterial.set_viewport_color(pymaterial, mat, vertex_color)

        mat.use_nodes = True
        while mat.node_tree.nodes:  # clear all nodes
            mat.node_tree.nodes.remove(mat.node_tree.nodes[0])

        mh = MaterialHelper(gltf, pymaterial, mat, vertex_color)

        exts = pymaterial.extensions or {}
        if 'KHR_materials_unlit' in exts:
            unlit(mh)
        elif 'KHR_materials_pbrSpecularGlossiness' in exts:
            pbr_specular_glossiness(mh)
        else:
            pbr_metallic_roughness(mh)

    @staticmethod
    def set_double_sided(pymaterial, mat):
        mat.use_backface_culling = (pymaterial.double_sided != True)

    @staticmethod
    def set_alpha_mode(pymaterial, mat):
        alpha_mode = pymaterial.alpha_mode
        if alpha_mode == 'BLEND':
            mat.blend_method = 'BLEND'
        elif alpha_mode == 'MASK':
            mat.blend_method = 'CLIP'
            alpha_cutoff = pymaterial.alpha_cutoff
            alpha_cutoff = alpha_cutoff if alpha_cutoff is not None else 0.5
            mat.alpha_threshold = alpha_cutoff

    @staticmethod
    def set_viewport_color(pymaterial, mat, vertex_color):
        # If there is no texture and no vertex color, use the base color as
        # the color for the Solid view.
        if vertex_color:
            return

        exts = pymaterial.extensions or {}
        if 'KHR_materials_pbrSpecularGlossiness' in exts:
            # TODO
            return
        else:
            pbr = pymaterial.pbr_metallic_roughness
            if pbr is None or pbr.base_color_texture is not None:
                return
            color = pbr.base_color_factor or [1, 1, 1, 1]

        mat.diffuse_color = color
