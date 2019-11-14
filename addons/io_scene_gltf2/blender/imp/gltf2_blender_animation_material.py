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

import json
import math
import re

import bpy
from mathutils import Matrix

from ...io.imp.gltf2_io_binary import BinaryData
from .gltf2_blender_animation_utils import simulate_stash, restore_animation_on_object, make_fcurve


class BlenderMaterialAnim():
    """Blender Material Animation."""
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("%s should not be instantiated" % cls)

    @staticmethod
    def first_match(patterns, s):
        for pattern in patterns:
            match = re.match(pattern, s)
            if match:
                return match
        return None

    @staticmethod
    def anim(gltf, anim_idx):
        """Import animation channels that affect materials.
        Only KHR_texture_transform/offset right now.
        """
        animation = gltf.data.animations[anim_idx]

        try:
            channels = animation.extensions['EXT_property_animation']['channels']
        except Exception:
            return

        # Create table to look up the sampler that affects a particular target.
        # Ex. sampler_table[material id]['baseColorTexture']['offset'] = sampler id
        sampler_table = {}
        for channel in channels:
            sampler_idx = channel['sampler']
            target = channel['target']

            patterns = [
                r'^/materials/(\d+)/(normalTexture|occlusionTexture|emissiveTexture)/extensions/KHR_texture_transform/(offset|rotation|scale)$',
                r'^/materials/(\d+)/pbrMetallicRoughness/(baseColorTexture|metallicRoughnessTexture)/extensions/KHR_texture_transform/(offset|rotation|scale)$',
                r'^/materials/(\d+)/extensions/KHR_materials_pbrSpecularGlossiness/(diffuseTexture|specularGlossinessTexture)/extensions/KHR_texture_transform/(offset|rotation|scale)$',
            ]
            match = BlenderMaterialAnim.first_match(patterns, target)
            if match:
                material_idx, texture_type, path = match.groups()
                (sampler_table
                    .setdefault(int(material_idx), {})
                    .setdefault(texture_type, {})
                )[path] = sampler_idx
                continue

        # Material idx -> action all channels affecting that material should use
        gltf.material_action_cache = {}

        for material_idx in sampler_table:
            # Skip any materials that didn't get created
            if not gltf.data.materials[material_idx].blender_material:
                continue

            for texture_type in sampler_table[material_idx]:
                BlenderMaterialAnim.tex_transform(
                    gltf,
                    anim_idx,
                    sampler_table,
                    material_idx,
                    texture_type,
                )

        BlenderMaterialAnim.stash_material_actions(gltf, anim_idx)

    @staticmethod
    def stash_material_actions(gltf, anim_idx):
        """Stash all materials in gltf.material_action_cache onto the
        materials they affect.
        """
        animation = gltf.data.animations[anim_idx]

        for material_idx, action in gltf.material_action_cache.items():
            # One glTF material may become multiple Blender materials
            for blender_material_name in gltf.data.materials[material_idx].blender_material.values():
                blender_material = bpy.data.materials[blender_material_name]

                if not blender_material.node_tree.animation_data:
                    blender_material.node_tree.animation_data_create()

                simulate_stash(
                    blender_material.node_tree,
                    animation.track_name,
                    action,
                )

    @staticmethod
    def tex_transform(gltf, anim_idx, sampler_table, material_idx, texture_type):
        paths = list(sampler_table[material_idx][texture_type].keys())
        if paths == ['offset']:
            BlenderMaterialAnim.tex_transform_offset_only(
                gltf,
                anim_idx,
                sampler_table,
                material_idx,
                texture_type,
            )

        else:
            # Currently unimplemented. Variable rotation/scale will require
            # resampling the offset curve in order to do the change in UV space.
            return

    @staticmethod
    def tex_transform_offset_only(gltf, anim_idx, sampler_table, material_idx, texture_type):
        """Handles a texture transform animation when only offset is animated
        (rotation and scale are constant).
        """
        animation = gltf.data.animations[anim_idx]
        material = gltf.data.materials[material_idx]
        fps = bpy.context.scene.render.fps

        action = gltf.material_action_cache.get(material_idx)
        if not action:
            material_name = material.name or 'Material_%d' % material_idx
            name = animation.track_name + "_" + material_name
            action = bpy.data.actions.new(name)
            gltf.material_action_cache[material_idx] = action

        sampler_idx = sampler_table[material_idx][texture_type]['offset']
        sampler = animation.samplers[sampler_idx]

        keys = BinaryData.get_data_from_accessor(gltf, sampler.input)
        values = BinaryData.get_data_from_accessor(gltf, sampler.output)

        if sampler.interpolation == "CUBICSPLINE":
            # Ignore tangents for now
            values = values[1::3]

        # Formula for glTF offset -> Blender offset depends on the (constant)
        # value of the rotation and scale too; fetch those.
        default_transform = BlenderMaterialAnim.get_default_texture_transform(
            material,
            texture_type,
        )
        rotation = default_transform['rotation']
        scale_v = default_transform['scale'][1]

        coords = [0] * (2 * len(keys))
        coords[::2] = (key[0] * fps for key in keys)

        if bpy.app.version < (2, 81, 8):
            data_path = 'nodes["%s.mapping"].translation' % texture_type
        else:
            data_path = 'nodes["%s.mapping"].inputs["Location"].default_value' % texture_type

        for i in range(0, 2):
            # See texture_transform_gltf_to_blender for formulas.
            if i == 0:
                # blender_offset[0] = gltf_offset[0] + gltf_scale[1] * sin(gltf_rotation)
                const = scale_v * math.sin(rotation)
                coords[1::2] = (vals[i] + const for vals in values)
            else:
                # blender_offset[1] = 1 - gltf_offset[1] - gltf_scale[1] * cos(gltf_rotation),
                const = 1.0 - scale_v * math.cos(rotation)
                coords[1::2] = (const - vals[i] for vals in values)

            make_fcurve(
                action,
                coords,
                data_path,
                index=i,
                group_name='UV Scroll',
                interpolation=sampler.interpolation,
            )

    @staticmethod
    def get_default_texture_transform(material, texture_type):
        try:
            if texture_type == 'emissiveTexture':
                exts = material.emissive_texture.extensions
            elif texture_type == 'normalTexture':
                exts = material.normal_texture.extensions
            elif texture_type == 'occlusionTexture':
                exts = material.occlusion_texture.extensions
            elif texture_type == 'baseColorTexture':
                exts = material.pbr_metallic_roughness.base_color_texture.extensions
            elif texture_type == 'metallicRoughnessTexture':
                exts = material.pbr_metallic_roughness.metallic_roughness_texture.extensions
            elif texture_type == 'diffuseTexture':
                exts = material.extensions['KHR_materials_pbrSpecularGlossiness'] \
                    ['diffuseTexture']['extensions']
            elif texture_type == 'specularGlossinessTexture':
                exts = material.extensions['KHR_materials_pbrSpecularGlossiness'] \
                    ['specularGlossinessTexture']['extensions']

            transform = exts['KHR_texture_transform']

        except Exception:
            transform = {}

        transform.setdefault('offset', [0, 0])
        transform.setdefault('rotation', 0)
        transform.setdefault('scale', [1, 1])

        return transform

    @staticmethod
    def restore_animation(gltf, anim_name):
        for material in gltf.data.materials:
            for blender_material_name in material.blender_material.values():
                blender_material = bpy.data.materials[blender_material_name]
                restore_animation_on_object(blender_material.node_tree, anim_name)
