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
from typing import Optional, Dict, List, Any
from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached
from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.blender.exp import gltf2_blender_gather_primitives
from io_scene_gltf2.blender.exp import gltf2_blender_generate_extras


@cached
def gather_mesh(blender_mesh: bpy.types.Mesh,
                vertex_groups: Optional[bpy.types.VertexGroups],
                modifiers: Optional[bpy.types.ObjectModifiers],
                export_settings
                ) -> Optional[gltf2_io.Mesh]:
    if not __filter_mesh(blender_mesh, vertex_groups, modifiers, export_settings):
        return None

    mesh = gltf2_io.Mesh(
        extensions=__gather_extensions(blender_mesh, vertex_groups, modifiers, export_settings),
        extras=__gather_extras(blender_mesh, vertex_groups, modifiers, export_settings),
        name=__gather_name(blender_mesh, vertex_groups, modifiers, export_settings),
        primitives=__gather_primitives(blender_mesh, vertex_groups, modifiers, export_settings),
        weights=__gather_weights(blender_mesh, vertex_groups, modifiers, export_settings)
    )

    return mesh


def __filter_mesh(blender_mesh: bpy.types.Mesh,
                  vertex_groups: Optional[bpy.types.VertexGroups],
                  modifiers: Optional[bpy.types.ObjectModifiers],
                  export_settings
                  ) -> bool:
    if blender_mesh.users == 0:
        return False
    return True


def __gather_extensions(blender_mesh: bpy.types.Mesh,
                        vertex_groups: Optional[bpy.types.VertexGroups],
                        modifiers: Optional[bpy.types.ObjectModifiers],
                        export_settings
                        ) -> Any:
    return None


def __gather_extras(blender_mesh: bpy.types.Mesh,
                    vertex_groups: Optional[bpy.types.VertexGroups],
                    modifiers: Optional[bpy.types.ObjectModifiers],
                    export_settings
                    ) -> Optional[Dict[Any, Any]]:
    if export_settings['gltf_extras']:
        return gltf2_blender_generate_extras.generate_extras(blender_mesh)
    return None


def __gather_name(blender_mesh: bpy.types.Mesh,
                  vertex_groups: Optional[bpy.types.VertexGroups],
                  modifiers: Optional[bpy.types.ObjectModifiers],
                  export_settings
                  ) -> str:
    return blender_mesh.name


def __gather_primitives(blender_mesh: bpy.types.Mesh,
                        vertex_groups: Optional[bpy.types.VertexGroups],
                        modifiers: Optional[bpy.types.ObjectModifiers],
                        export_settings
                        ) -> List[gltf2_io.MeshPrimitive]:
    return gltf2_blender_gather_primitives.gather_primitives(blender_mesh, vertex_groups, modifiers, export_settings)


def __gather_weights(blender_mesh: bpy.types.Mesh,
                     vertex_groups: Optional[bpy.types.VertexGroups],
                     modifiers: Optional[bpy.types.ObjectModifiers],
                     export_settings
                     ) -> Optional[List[float]]:
    return None
