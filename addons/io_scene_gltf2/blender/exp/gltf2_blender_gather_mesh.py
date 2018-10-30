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

from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached
from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.blender.exp import gltf2_blender_gather_primitives

@cached
def gather_mesh(blender_mesh: bpy.types.Mesh, vertex_groups: bpy.types.VertexGroups, export_settings):
    if not __filter_mesh(blender_mesh, vertex_groups, export_settings):
        return None

    mesh = gltf2_io.Mesh(
        extensions=__gather_extensions(blender_mesh, vertex_groups, export_settings),
        extras=__gather_extras(blender_mesh, vertex_groups, export_settings),
        name=__gather_name(blender_mesh, vertex_groups, export_settings),
        primitives=__gather_primitives(blender_mesh, vertex_groups, export_settings),
        weights=__gather_weights(blender_mesh, vertex_groups, export_settings)
    )

    return mesh


def __filter_mesh(blender_mesh: bpy.types.Mesh, vertex_groups: bpy.types.VertexGroups, export_settings):
    if blender_mesh.users == 0:
        return False
    return True


def __gather_extensions(blender_mesh: bpy.types.Mesh, vertex_groups: bpy.types.VertexGroups, export_settings):
    return None


def __gather_extras(blender_mesh: bpy.types.Mesh, vertex_groups: bpy.types.VertexGroups, export_settings):
    return None


def __gather_name(blender_mesh: bpy.types.Mesh, vertex_groups: bpy.types.VertexGroups, export_settings):
    return blender_mesh.name


def __gather_primitives(blender_mesh: bpy.types.Mesh, vertex_groups: bpy.types.VertexGroups, export_settings):
    return gltf2_blender_gather_primitives.gather_primitives(blender_mesh, vertex_groups, export_settings)


def __gather_weights(blender_mesh: bpy.types.Mesh, vertex_groups: bpy.types.VertexGroups, export_settings):
    return None