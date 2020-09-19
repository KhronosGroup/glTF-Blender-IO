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

import bpy
from typing import Optional, Dict, List, Any, Tuple
from collections import namedtuple

from .gltf2_blender_export_keys import MORPH, APPLY, SKINS, MATERIALS
from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached, cached_by_key
from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.blender.exp import gltf2_blender_gather_primitives
from ..com.gltf2_blender_extras import generate_extras
from io_scene_gltf2.io.com.gltf2_io_debug import print_console
from io_scene_gltf2.io.exp.gltf2_io_user_extensions import export_user_extensions


# Reuse the same glTF mesh for instance with the same cache key.
CacheKey = namedtuple('MeshCacheKey', [
    'data', 'arma_ob', 'vertex_groups', 'modifiers', 'materials',
])


@cached
def get_mesh_cache_key(ob: bpy.types.Object, export_settings):
    # Because mesh data will be transforms to skeleton space,
    # we can't instantiate multiple object at different location, skined by same armature
    arma_ob = None
    if export_settings[SKINS]:
        for modifier in ob.modifiers:
            if modifier.type == 'ARMATURE':
                arma_ob = ob
                break

    vgroups = None
    if export_settings[SKINS]:
        if any(mod.type == "ARMATURE" for mod in ob.modifiers):
            vgroups = tuple(group.name for group in ob.vertex_groups)

    modifiers = None
    if export_settings[APPLY]:
        for mod in ob.modifiers:
            # Ignore Armature modifiers if skinning
            if export_settings[SKINS] and mod.type == "ARMATURE":
                continue

            # Don't reuse for objects with different modifier stacks.
            if mod.show_viewport:
                modifiers = object
                break

    materials = None
    if export_settings[MATERIALS] != 'NONE':
        materials = tuple(ms.material for ms in ob.material_slots)

    return CacheKey(
        data=ob.data,
        arma_ob=arma_ob,
        vertex_groups=vgroups,
        modifiers=modifiers,
        materials=materials,
    )


@cached_by_key(key=get_mesh_cache_key)
def gather_mesh(ob: bpy.types.Object,
                  export_settings
                  ) -> Optional[gltf2_io.Mesh]:
    if not __filter_mesh(ob, export_settings):
        return None

    mesh = gltf2_io.Mesh(
        extensions=__gather_extensions(ob, export_settings),
        extras=__gather_extras(ob, export_settings),
        name=__gather_name(ob, export_settings),
        weights=__gather_weights(ob, export_settings),
        primitives=__gather_primitives(ob, export_settings),
    )

    if not mesh.primitives:
        print_console("WARNING", "'{}' has no primitives and will be omitted.".format(ob.data.name))
        return None

    export_user_extensions('gather_mesh_hook',
                           export_settings,
                           ob)

    return mesh


def __filter_mesh(ob: bpy.types.Object,
                  export_settings
                  ) -> bool:
    if ob.data.users == 0:
        return False
    return True


def __gather_extensions(ob: bpy.types.Object,
                        export_settings
                        ) -> Any:
    return None


def __gather_extras(ob: bpy.types.Object,
                    export_settings
                    ) -> Optional[Dict[Any, Any]]:
    extras = {}

    if export_settings['gltf_extras']:
        extras = generate_extras(ob.data) or {}

    if export_settings[MORPH] and not export_settings[APPLY] and \
            ob.type == 'MESH' and ob.data.shape_keys:
        morph_max = len(ob.data.shape_keys.key_blocks) - 1
        if morph_max > 0:
            target_names = []
            for blender_shape_key in ob.data.shape_keys.key_blocks:
                if blender_shape_key != blender_shape_key.relative_key:
                    if blender_shape_key.mute is False:
                        target_names.append(blender_shape_key.name)
            extras['targetNames'] = target_names

    if extras:
        return extras

    return None


def __gather_name(ob: bpy.types.Object,
                  export_settings
                  ) -> str:
    return ob.data.name


def __gather_primitives(ob: bpy.types.Object,
                        export_settings
                        ) -> List[gltf2_io.MeshPrimitive]:
    return gltf2_blender_gather_primitives.gather_primitives(ob, export_settings)


def __gather_weights(ob: bpy.types.Object,
                     export_settings
                     ) -> Optional[List[float]]:
    if ob.type != 'MESH':
        return None

    blender_mesh = ob.data

    if not export_settings[MORPH] or export_settings[APPLY] \
            or not blender_mesh.shape_keys:
        return None

    morph_max = len(blender_mesh.shape_keys.key_blocks) - 1
    if morph_max <= 0:
        return None

    weights = []

    for blender_shape_key in blender_mesh.shape_keys.key_blocks:
        if blender_shape_key != blender_shape_key.relative_key:
            if blender_shape_key.mute is False:
                weights.append(blender_shape_key.value)

    return weights or None
