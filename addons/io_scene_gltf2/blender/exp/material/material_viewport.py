# Copyright 2018-2024 The glTF-Blender-IO authors.
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

from ....io.com import gltf2_io
from .material_utils import gather_extras, gather_name

def export_viewport_material(blender_material, export_settings):

    pbr_metallic_roughness = gltf2_io.MaterialPBRMetallicRoughness(
        base_color_factor=list(blender_material.diffuse_color),
        base_color_texture=None,
        metallic_factor=blender_material.metallic,
        roughness_factor=blender_material.roughness,
        metallic_roughness_texture=None,
        extensions=None,
        extras=None
    )

    return gltf2_io.Material(
        alpha_cutoff=None,
        alpha_mode=None,
        double_sided=None,
        emissive_factor=None,
        emissive_texture=None,
        extensions=None,
        extras=gather_extras(blender_material, export_settings),
        name=gather_name(blender_material, export_settings),
        normal_texture=None,
        occlusion_texture=None,
        pbr_metallic_roughness=pbr_metallic_roughness
    )
