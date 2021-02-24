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


from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached
from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.io.com import gltf2_io_constants
from io_scene_gltf2.io.exp import gltf2_io_binary_data


@cached
def gather_accessor(buffer_view: gltf2_io_binary_data.BinaryData,
                    component_type: gltf2_io_constants.ComponentType,
                    count,
                    max,
                    min,
                    type: gltf2_io_constants.DataType,
                    export_settings) -> gltf2_io.Accessor:
    return gltf2_io.Accessor(
        buffer_view=buffer_view,
        byte_offset=None,
        component_type=component_type,
        count=count,
        extensions=None,
        extras=None,
        max=list(max) if max is not None else None,
        min=list(min) if min is not None else None,
        name=None,
        normalized=None,
        sparse=None,
        type=type
    )
