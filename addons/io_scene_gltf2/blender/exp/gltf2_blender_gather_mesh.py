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
from typing import Optional, Dict, List, Any, Tuple
from .gltf2_blender_export_keys import MORPH
from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached, cached_by_key
from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.blender.exp import gltf2_blender_gather_primitives
from ..com.gltf2_blender_extras import generate_extras
from io_scene_gltf2.io.com.gltf2_io_debug import print_console
from io_scene_gltf2.io.exp.gltf2_io_user_extensions import export_user_extensions


@cached
def get_mesh_cache_key(blender_mesh,
                blender_object,
                vertex_groups,
                modifiers,
                skip_filter,
                materials,
                export_settings):
    # Use id of mesh
    # Do not use bpy.types that can be unhashable
    # Do not use mesh name, that can be not unique (when linked)

    # If materials are not exported, no need to cache by material
    if export_settings['gltf_materials'] is None:
        mats = None
    else:
        mats = tuple(id(m) if m is not None else None for m in materials)

    # TODO check what is really needed for modifiers

    return (
        (id(blender_mesh),),
        (modifiers,),
        (skip_filter,),             #TODO to check if still needed
        mats
    )

@cached_by_key(key=get_mesh_cache_key)
def gather_mesh(blender_mesh: bpy.types.Mesh,
                uuid_for_skined_data,
                vertex_groups: Optional[bpy.types.VertexGroups],
                modifiers: Optional[bpy.types.ObjectModifiers],
                skip_filter: bool,
                materials: Tuple[bpy.types.Material],
                export_settings
                ) -> Optional[gltf2_io.Mesh]:
    if not skip_filter and not __filter_mesh(blender_mesh, vertex_groups, modifiers, export_settings):
        return None

    mesh = gltf2_io.Mesh(
        extensions=__gather_extensions(blender_mesh, vertex_groups, modifiers, export_settings),
        extras=__gather_extras(blender_mesh, vertex_groups, modifiers, export_settings),
        name=__gather_name(blender_mesh, vertex_groups, modifiers, export_settings),
        weights=__gather_weights(blender_mesh, vertex_groups, modifiers, export_settings),
        primitives=__gather_primitives(blender_mesh, uuid_for_skined_data, vertex_groups, modifiers, materials, export_settings),
    )

    if len(mesh.primitives) == 0:
        print_console("WARNING", "Mesh '{}' has no primitives and will be omitted.".format(mesh.name))
        return None

    blender_object = None
    if uuid_for_skined_data:
        blender_object = export_settings['vtree'].nodes[uuid_for_skined_data].blender_object


    export_user_extensions('gather_mesh_hook',
                           export_settings,
                           mesh,
                           blender_mesh,
                           blender_object,
                           vertex_groups,
                           modifiers,
                           skip_filter,
                           materials)

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

    extras = {}

    if export_settings['gltf_extras']:
        extras = generate_extras(blender_mesh) or {}

    if export_settings[MORPH] and blender_mesh.shape_keys:
        morph_max = len(blender_mesh.shape_keys.key_blocks) - 1
        if morph_max > 0:
            target_names = []
            for blender_shape_key in blender_mesh.shape_keys.key_blocks:
                if blender_shape_key != blender_shape_key.relative_key:
                    if blender_shape_key.mute is False:
                        target_names.append(blender_shape_key.name)
            extras['targetNames'] = target_names

    if extras:
        return extras

    return None


def __gather_name(blender_mesh: bpy.types.Mesh,
                  vertex_groups: Optional[bpy.types.VertexGroups],
                  modifiers: Optional[bpy.types.ObjectModifiers],
                  export_settings
                  ) -> str:
    return blender_mesh.name


def __gather_primitives(blender_mesh: bpy.types.Mesh,
                        uuid_for_skined_data,
                        vertex_groups: Optional[bpy.types.VertexGroups],
                        modifiers: Optional[bpy.types.ObjectModifiers],
                        materials: Tuple[bpy.types.Material],
                        export_settings
                        ) -> List[gltf2_io.MeshPrimitive]:
    return gltf2_blender_gather_primitives.gather_primitives(blender_mesh,
                                                             uuid_for_skined_data,
                                                             vertex_groups,
                                                             modifiers,
                                                             materials,
                                                             export_settings)


def __gather_weights(blender_mesh: bpy.types.Mesh,
                     vertex_groups: Optional[bpy.types.VertexGroups],
                     modifiers: Optional[bpy.types.ObjectModifiers],
                     export_settings
                     ) -> Optional[List[float]]:
    if not export_settings[MORPH] or not blender_mesh.shape_keys:
        return None

    morph_max = len(blender_mesh.shape_keys.key_blocks) - 1
    if morph_max <= 0:
        return None

    weights = []

    for blender_shape_key in blender_mesh.shape_keys.key_blocks:
        if blender_shape_key != blender_shape_key.relative_key:
            if blender_shape_key.mute is False:
                weights.append(blender_shape_key.value)

    return weights
