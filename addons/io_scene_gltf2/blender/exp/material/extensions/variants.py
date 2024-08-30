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

import bpy
from typing import Dict, Any
from .....io.com import variants as gltf2_io_variants
from ...cache import cached


@cached
def gather_variant(variant_idx, export_settings) -> Dict[str, Any]:

    variant = gltf2_io_variants.Variant(
        name=bpy.data.scenes[0].gltf2_KHR_materials_variants_variants[variant_idx].name,
        extensions=None,
        extras=None
    )
    return variant.to_dict()
