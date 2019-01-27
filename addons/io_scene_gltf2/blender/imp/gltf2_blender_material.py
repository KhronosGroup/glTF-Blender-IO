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
from .gltf2_blender_pbrMetallicRoughness import BlenderPbr
from .gltf2_blender_KHR_materials_pbrSpecularGlossiness import BlenderKHR_materials_pbrSpecularGlossiness
from .gltf2_blender_KHR_materials_unlit import BlenderKHR_materials_unlit
from .gltf2_blender_map_emissive import BlenderEmissiveMap
from .gltf2_blender_map_normal import BlenderNormalMap
from .gltf2_blender_map_occlusion import BlenderOcclusionMap
from ..com.gltf2_blender_material_helpers import get_output_surface_input
from ..com.gltf2_blender_material_helpers import get_preoutput_node_output
from ..com.gltf2_blender_material_helpers import get_base_color_node
from ...io.com.gltf2_io import MaterialPBRMetallicRoughness


class BlenderMaterial():
    """Blender Material."""
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("%s should not be instantiated" % cls)

    @staticmethod
    def create(gltf, material_idx, vertex_color):
        """Material creation."""
        pymaterial = gltf.data.materials[material_idx]

        if vertex_color is None:
            if pymaterial.name is not None:
                name = pymaterial.name
            else:
                name = "Material_" + str(material_idx)
        else:
            if pymaterial.name is not None:
                name = pymaterial.name + "_" + vertex_color
            else:
                name = "Material_" + str(material_idx) + "_" + vertex_color

        mat = bpy.data.materials.new(name)
        pymaterial.blender_material[vertex_color] = mat.name

        ignore_map = False

        if pymaterial.extensions is not None :
            if 'KHR_materials_unlit' in pymaterial.extensions.keys():
                ignore_map = True
                BlenderKHR_materials_unlit.create(
                    gltf, material_idx,
                    pymaterial.extensions['KHR_materials_unlit'],
                    mat.name,
                    vertex_color
                )
            elif 'KHR_materials_pbrSpecularGlossiness' in pymaterial.extensions.keys():
                BlenderKHR_materials_pbrSpecularGlossiness.create(
                    gltf, pymaterial.extensions['KHR_materials_pbrSpecularGlossiness'], mat.name, vertex_color
                )
        else:
            # create pbr material
            if pymaterial.pbr_metallic_roughness is None:
                # If no pbr material is set, we need to apply all default of pbr
                pbr = {}
                pbr["baseColorFactor"] = [1.0, 1.0, 1.0, 1.0]
                pbr["metallicFactor"] = 1.0
                pbr["roughnessFactor"] = 1.0
                pymaterial.pbr_metallic_roughness = MaterialPBRMetallicRoughness.from_dict(pbr)
                pymaterial.pbr_metallic_roughness.color_type = gltf.SIMPLE
                pymaterial.pbr_metallic_roughness.metallic_type = gltf.SIMPLE

            BlenderPbr.create(gltf, pymaterial.pbr_metallic_roughness, mat.name, vertex_color)

        if ignore_map == False:
            # add emission map if needed
            if pymaterial.emissive_texture is not None:
                BlenderEmissiveMap.create(gltf, material_idx, vertex_color)

            # add normal map if needed
            if pymaterial.normal_texture is not None:
                BlenderNormalMap.create(gltf, material_idx, vertex_color)

            # add occlusion map if needed
            # will be pack, but not used
            if pymaterial.occlusion_texture is not None:
                BlenderOcclusionMap.create(gltf, material_idx, vertex_color)

            if pymaterial.alpha_mode is not None and pymaterial.alpha_mode != 'OPAQUE':
                BlenderMaterial.blender_alpha(gltf, material_idx, vertex_color, pymaterial.alpha_mode)

        mat.gltf_double_sided = bool(pymaterial.double_sided)
        
    @staticmethod
    def set_uvmap(gltf, material_idx, prim, obj, vertex_color):
        """Set UV Map."""
        pymaterial = gltf.data.materials[material_idx]

        node_tree = bpy.data.materials[pymaterial.blender_material[vertex_color]].node_tree
        uvmap_nodes = [node for node in node_tree.nodes if node.type in ['UVMAP', 'NORMAL_MAP']]
        for uvmap_node in uvmap_nodes:
            if uvmap_node["gltf2_texcoord"] in prim.blender_texcoord.keys():
                uvmap_node.uv_map = prim.blender_texcoord[uvmap_node["gltf2_texcoord"]]

    @staticmethod
    def blender_alpha(gltf, material_idx, vertex_color, alpha_mode):
        """Set alpha."""
        pymaterial = gltf.data.materials[material_idx]
        material = bpy.data.materials[pymaterial.blender_material[vertex_color]]

        # Set alpha value in material
        if bpy.app.version < (2, 80, 0):
            material.game_settings.alpha_blend = 'ALPHA'
        else:
            if alpha_mode == 'BLEND':
                material.blend_method = 'BLEND'
            elif alpha_mode == "MASK":
                material.blend_method = 'CLIP'
                alpha_cutoff = 1.0 - pymaterial.alpha_cutoff if pymaterial.alpha_cutoff is not None else 0.5
                material.alpha_threshold = alpha_cutoff

        node_tree = material.node_tree
        # Add nodes for basic transparency
        # Add mix shader between output and Principled BSDF
        trans = node_tree.nodes.new('ShaderNodeBsdfTransparent')
        trans.location = 750, -500
        mix = node_tree.nodes.new('ShaderNodeMixShader')
        mix.location = 1000, 0

        output_surface_input = get_output_surface_input(node_tree)
        preoutput_node_output = get_preoutput_node_output(node_tree)

        link = output_surface_input.links[0]
        node_tree.links.remove(link)

        # PBR => Mix input 1
        node_tree.links.new(preoutput_node_output, mix.inputs[1])

        # Trans => Mix input 2
        node_tree.links.new(trans.outputs['BSDF'], mix.inputs[2])

        # Mix => Output
        node_tree.links.new(mix.outputs['Shader'], output_surface_input)

        # alpha blend factor
        add = node_tree.nodes.new('ShaderNodeMath')
        add.operation = 'ADD'
        add.location = 750, -250

        diffuse_factor = 1.0
        if pymaterial.extensions is not None and 'KHR_materials_pbrSpecularGlossiness' in pymaterial.extensions:
            diffuse_factor = pymaterial.extensions['KHR_materials_pbrSpecularGlossiness']['diffuseFactor'][3]
        elif pymaterial.pbr_metallic_roughness:
            diffuse_factor = pymaterial.pbr_metallic_roughness.base_color_factor[3]

        add.inputs[0].default_value = abs(1.0 - diffuse_factor)
        add.inputs[1].default_value = 0.0
        node_tree.links.new(add.outputs['Value'], mix.inputs[0])

        # Take diffuse texture alpha into account if any
        diffuse_texture = get_base_color_node(node_tree)
        if diffuse_texture:
            inverter = node_tree.nodes.new('ShaderNodeInvert')
            inverter.location = 250, -250
            inverter.inputs[1].default_value = (1.0, 1.0, 1.0, 1.0)
            node_tree.links.new(diffuse_texture.outputs['Alpha'], inverter.inputs[0])

            mult = node_tree.nodes.new('ShaderNodeMath')
            mult.operation = 'MULTIPLY' if pymaterial.alpha_mode == 'BLEND' else 'GREATER_THAN'
            mult.location = 500, -250
            alpha_cutoff = 1.0 if pymaterial.alpha_mode == 'BLEND' else \
                1.0 - pymaterial.alpha_cutoff if pymaterial.alpha_cutoff is not None else 0.5
            mult.inputs[1].default_value = alpha_cutoff
            node_tree.links.new(inverter.outputs['Color'], mult.inputs[0])
            node_tree.links.new(mult.outputs['Value'], add.inputs[0])
