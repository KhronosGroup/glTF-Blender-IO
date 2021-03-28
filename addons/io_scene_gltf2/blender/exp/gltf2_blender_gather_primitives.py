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
from typing import List, Optional, Tuple
import numpy as np

from .gltf2_blender_export_keys import NORMALS, MORPH_NORMAL, TANGENTS, MORPH_TANGENT, MORPH

from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached
from io_scene_gltf2.blender.exp import gltf2_blender_extract
from io_scene_gltf2.blender.exp import gltf2_blender_gather_accessors
from io_scene_gltf2.blender.exp import gltf2_blender_gather_primitive_attributes
from io_scene_gltf2.blender.exp import gltf2_blender_gather_materials

from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.io.exp import gltf2_io_binary_data
from io_scene_gltf2.io.com import gltf2_io_constants
from io_scene_gltf2.io.com.gltf2_io_debug import print_console


@cached
def gather_primitives(
        blender_mesh: bpy.types.Mesh,
        library: Optional[str],
        blender_object: Optional[bpy.types.Object],
        vertex_groups: Optional[bpy.types.VertexGroups],
        modifiers: Optional[bpy.types.ObjectModifiers],
        material_names: Tuple[str],
        export_settings
        ) -> List[gltf2_io.MeshPrimitive]:
    """
    Extract the mesh primitives from a blender object

    :return: a list of glTF2 primitives
    """
    primitives = []

    blender_primitives = __gather_cache_primitives(blender_mesh, library, blender_object,
        vertex_groups, modifiers, export_settings)

    for internal_primitive in blender_primitives:
        material_idx = internal_primitive['material']
        material = None

        if export_settings['gltf_materials'] == "EXPORT" and material_idx is not None:
            blender_material = None
            if material_names:
                i = material_idx if material_idx < len(material_names) else -1
                material_name = material_names[i]
                if material_name is not None:
                    blender_material = bpy.data.materials[material_name]
            if blender_material is not None:
                material = gltf2_blender_gather_materials.gather_material(
                    blender_material,
                    export_settings,
                )

        primitive = gltf2_io.MeshPrimitive(
            attributes=internal_primitive['attributes'],
            extensions=None,
            extras=None,
            indices=internal_primitive['indices'],
            material=material,
            mode=internal_primitive['mode'],
            targets=internal_primitive['targets']
        )
        primitives.append(primitive)

    return primitives

@cached
def __gather_cache_primitives(
        blender_mesh: bpy.types.Mesh,
        library: Optional[str],
        blender_object: Optional[bpy.types.Object],
        vertex_groups: Optional[bpy.types.VertexGroups],
        modifiers: Optional[bpy.types.ObjectModifiers],
        export_settings
) -> List[dict]:
    """
    Gather parts that are identical for instances, i.e. excluding materials
    """
    primitives = []

    blender_primitives = gltf2_blender_extract.extract_primitives(
        None, blender_mesh, library, blender_object, vertex_groups, modifiers, export_settings)

    for internal_primitive in blender_primitives:
        primitive = {
            "attributes": __gather_attributes(internal_primitive, blender_mesh, modifiers, export_settings),
            "indices": __gather_indices(internal_primitive, blender_mesh, modifiers, export_settings),
            "mode": internal_primitive.get('mode'),
            "material": internal_primitive.get('material'),
            "targets": __gather_targets(internal_primitive, blender_mesh, modifiers, export_settings)
        }
        primitives.append(primitive)

    return primitives

def __gather_indices(blender_primitive, blender_mesh, modifiers, export_settings):
    indices = blender_primitive.get('indices')
    if indices is None:
        return None

    # NOTE: Values used by some graphics APIs as "primitive restart" values are disallowed.
    # Specifically, the values 65535 (in UINT16) and 4294967295 (in UINT32) cannot be used as indices.
    # https://github.com/KhronosGroup/glTF/issues/1142
    # https://github.com/KhronosGroup/glTF/pull/1476/files
    # Also, UINT8 mode is not supported:
    # https://github.com/KhronosGroup/glTF/issues/1471
    max_index = indices.max()
    if max_index < 65535:
        component_type = gltf2_io_constants.ComponentType.UnsignedShort
        indices = indices.astype(np.uint16, copy=False)
    elif max_index < 4294967295:
        component_type = gltf2_io_constants.ComponentType.UnsignedInt
        indices = indices.astype(np.uint32, copy=False)
    else:
        print_console('ERROR', 'A mesh contains too many vertices (' + str(max_index) + ') and needs to be split before export.')
        return None

    element_type = gltf2_io_constants.DataType.Scalar
    binary_data = gltf2_io_binary_data.BinaryData(indices.tobytes())
    return gltf2_blender_gather_accessors.gather_accessor(
        binary_data,
        component_type,
        len(indices),
        None,
        None,
        element_type,
        export_settings
    )


def __gather_attributes(blender_primitive, blender_mesh, modifiers, export_settings):
    return gltf2_blender_gather_primitive_attributes.gather_primitive_attributes(blender_primitive, export_settings)


def __gather_targets(blender_primitive, blender_mesh, modifiers, export_settings):
    if export_settings[MORPH]:
        targets = []
        if blender_mesh.shape_keys is not None:
            morph_index = 0
            for blender_shape_key in blender_mesh.shape_keys.key_blocks:
                if blender_shape_key == blender_shape_key.relative_key:
                    continue

                if blender_shape_key.mute is True:
                    continue

                target_position_id = 'MORPH_POSITION_' + str(morph_index)
                target_normal_id = 'MORPH_NORMAL_' + str(morph_index)
                target_tangent_id = 'MORPH_TANGENT_' + str(morph_index)

                if blender_primitive["attributes"].get(target_position_id) is not None:
                    target = {}
                    internal_target_position = blender_primitive["attributes"][target_position_id]
                    target["POSITION"] = gltf2_blender_gather_primitive_attributes.array_to_accessor(
                        internal_target_position,
                        component_type=gltf2_io_constants.ComponentType.Float,
                        data_type=gltf2_io_constants.DataType.Vec3,
                        include_max_and_min=True,
                    )

                    if export_settings[NORMALS] \
                            and export_settings[MORPH_NORMAL] \
                            and blender_primitive["attributes"].get(target_normal_id) is not None:

                        internal_target_normal = blender_primitive["attributes"][target_normal_id]
                        target['NORMAL'] = gltf2_blender_gather_primitive_attributes.array_to_accessor(
                            internal_target_normal,
                            component_type=gltf2_io_constants.ComponentType.Float,
                            data_type=gltf2_io_constants.DataType.Vec3,
                        )

                    if export_settings[TANGENTS] \
                            and export_settings[MORPH_TANGENT] \
                            and blender_primitive["attributes"].get(target_tangent_id) is not None:
                        internal_target_tangent = blender_primitive["attributes"][target_tangent_id]
                        target['TANGENT'] = gltf2_blender_gather_primitive_attributes.array_to_accessor(
                            internal_target_tangent,
                            component_type=gltf2_io_constants.ComponentType.Float,
                            data_type=gltf2_io_constants.DataType.Vec3,
                        )
                    targets.append(target)
                    morph_index += 1
        return targets
    return None
