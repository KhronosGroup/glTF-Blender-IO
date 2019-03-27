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
import bmesh

from .gltf2_blender_primitive import BlenderPrimitive
from ...io.imp.gltf2_io_binary import BinaryData
from ...io.com.gltf2_io_color_management import color_linear_to_srgb
from ..com.gltf2_blender_conversion import loc_gltf_to_blender


class BlenderMesh():
    """Blender Mesh."""
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("%s should not be instantiated" % cls)

    @staticmethod
    def create(gltf, mesh_idx, node_idx, parent):
        """Mesh creation."""
        pymesh = gltf.data.meshes[mesh_idx]

        # Geometry
        if pymesh.name:
            mesh_name = pymesh.name
        else:
            mesh_name = "Mesh_" + str(mesh_idx)

        mesh = bpy.data.meshes.new(mesh_name)
        verts = []
        edges = []
        faces = []
        for prim in pymesh.primitives:
            verts, edges, faces = BlenderPrimitive.create(gltf, prim, verts, edges, faces)

        mesh.from_pydata(verts, edges, faces)
        mesh.validate()

        pymesh.blender_name = mesh.name

        return mesh

    @staticmethod
    def set_mesh(gltf, pymesh, mesh, obj):
        """Set all data after mesh creation."""
        # Normals
        offset = 0
        custom_normals = [[0.0, 0.0, 0.0]] * len(mesh.vertices)

        if gltf.import_settings['import_shading'] == "NORMALS":
            mesh.create_normals_split()

        for prim in pymesh.primitives:
            offset = BlenderPrimitive.set_normals(gltf, prim, mesh, offset, custom_normals)

        mesh.update()

        # manage UV
        offset = 0
        for prim in pymesh.primitives:
            offset = BlenderPrimitive.set_UV(gltf, prim, obj, mesh, offset)

        mesh.update()

        # Normals, now that every update is done
        if gltf.import_settings['import_shading'] == "NORMALS":
            mesh.normals_split_custom_set_from_vertices(custom_normals)
            mesh.use_auto_smooth = True

        # Object and UV are now created, we can set UVMap into material
        for prim in pymesh.primitives:
            vertex_color = None
            if 'COLOR_0' in prim.attributes.keys():
                vertex_color = 'COLOR_0'
            BlenderPrimitive.set_UV_in_mat(gltf, prim, obj, vertex_color)

        # Assign materials to mesh
        offset = 0
        cpt_index_mat = 0
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        for prim in pymesh.primitives:
            offset, cpt_index_mat = BlenderPrimitive.assign_material(gltf, prim, obj, bm, offset, cpt_index_mat)

        bm.to_mesh(obj.data)
        bm.free()

        # Create shapekeys if needed
        max_shape_to_create = 0
        for prim in pymesh.primitives:
            if prim.targets:
                if len(prim.targets) > max_shape_to_create:
                    max_shape_to_create = len(prim.targets)

        # Create basis shape key
        if max_shape_to_create > 0:
            obj.shape_key_add(name="Basis")

        current_shapekey_index = 0
        for sk in range(max_shape_to_create):

            # Check if this target has POSITION
            if 'POSITION' not in prim.targets[sk].keys():
                gltf.shapekeys[sk] = None
                continue

            # Check if glTF file has some extras with targetNames
            shapekey_name = None
            if pymesh.extras is not None:
                if 'targetNames' in pymesh.extras.keys() and sk < len(pymesh.extras['targetNames']):
                    shapekey_name = pymesh.extras['targetNames'][sk]

            if shapekey_name is None:
                shapekey_name = "target_" + str(sk)

            obj.shape_key_add(name=shapekey_name)
            current_shapekey_index += 1

            offset_idx = 0
            for prim in pymesh.primitives:
                if prim.targets is None:
                    continue
                if sk >= len(prim.targets):
                    continue

                bm = bmesh.new()
                bm.from_mesh(mesh)

                shape_layer = bm.verts.layers.shape[current_shapekey_index]
                gltf.shapekeys[sk] = current_shapekey_index

                original_pos = BinaryData.get_data_from_accessor(gltf, prim.targets[sk]['POSITION'])

                tmp_indices = {}
                tmp_idx = 0
                pos = []
                for i in prim.tmp_indices:
                    if i[0] not in tmp_indices.keys():
                        tmp_indices[i[0]] = tmp_idx
                        tmp_idx += 1
                        pos.append(original_pos[i[0]])

                for vert in bm.verts:
                    if vert.index not in range(offset_idx, offset_idx + prim.vertices_length):
                        continue

                    shape = vert[shape_layer]

                    co = loc_gltf_to_blender(list(pos[vert.index - offset_idx]))
                    shape.x = obj.data.vertices[vert.index].co.x + co[0]
                    shape.y = obj.data.vertices[vert.index].co.y + co[1]
                    shape.z = obj.data.vertices[vert.index].co.z + co[2]

                bm.to_mesh(obj.data)
                bm.free()
                offset_idx += prim.vertices_length

        # set default weights for shape keys, and names
        if pymesh.weights is not None:
            for i in range(max_shape_to_create):
                if i < len(pymesh.weights):
                    if gltf.shapekeys[i] is None: # No default value if shapekeys was not created
                        continue
                    obj.data.shape_keys.key_blocks[gltf.shapekeys[i]].value = pymesh.weights[i]
                    if gltf.data.accessors[pymesh.primitives[0].targets[i]['POSITION']].name is not None:
                        obj.data.shape_keys.key_blocks[gltf.shapekeys[i]].name = \
                            gltf.data.accessors[pymesh.primitives[0].targets[i]['POSITION']].name

        # Apply vertex color.
        vertex_color = None
        offset = 0
        for prim in pymesh.primitives:
            if 'COLOR_0' in prim.attributes.keys():
                # Create vertex color, once only per object
                if vertex_color is None:
                    vertex_color = obj.data.vertex_colors.new(name="COLOR_0")

                original_color_data = BinaryData.get_data_from_accessor(gltf, prim.attributes['COLOR_0'])

                tmp_indices = {}
                tmp_idx = 0
                color_data = []
                for i in prim.tmp_indices:
                    if i[0] not in tmp_indices.keys():
                        tmp_indices[i[0]] = tmp_idx
                        tmp_idx += 1
                        color_data.append(original_color_data[i[0]])

                for poly in mesh.polygons:
                    for loop_idx in range(poly.loop_start, poly.loop_start + poly.loop_total):
                        vert_idx = mesh.loops[loop_idx].vertex_index
                        if vert_idx in range(offset, offset + prim.vertices_length):
                            cpt_idx = vert_idx - offset
                            # Need to convert from linear (glTF to sRGB (blender))
                            if bpy.app.version < (2, 80, 0):
                                # manage post 2.79b versions
                                if len(vertex_color.data[loop_idx].color) == 4:
                                    if len(color_data[cpt_idx]) == 3:
                                        # TODO : no alpha in vertex color
                                        srgb_color = [
                                            color_linear_to_srgb(color_data[cpt_idx][0]),
                                            color_linear_to_srgb(color_data[cpt_idx][1]),
                                            color_linear_to_srgb(color_data[cpt_idx][2]),
                                            1.0]
                                    else:
                                        srgb_color = [
                                            color_linear_to_srgb(color_data[cpt_idx][0]),
                                            color_linear_to_srgb(color_data[cpt_idx][1]),
                                            color_linear_to_srgb(color_data[cpt_idx][2]),
                                            color_data[cpt_idx][3]]
                                    vertex_color.data[loop_idx].color = srgb_color
                                else:
                                    srgb_color = [
                                        color_linear_to_srgb(color_data[cpt_idx][0]),
                                        color_linear_to_srgb(color_data[cpt_idx][1]),
                                        color_linear_to_srgb(color_data[cpt_idx][2])]
                                    vertex_color.data[loop_idx].color = srgb_color
                            else:
                                # check dimension, and add alpha if needed
                                if len(color_data[cpt_idx]) == 3:
                                    srgb_color = [
                                        color_linear_to_srgb(color_data[cpt_idx][0]),
                                        color_linear_to_srgb(color_data[cpt_idx][1]),
                                        color_linear_to_srgb(color_data[cpt_idx][2]),
                                        1.0]
                                else:
                                    srgb_color = [
                                        color_linear_to_srgb(color_data[cpt_idx][0]),
                                        color_linear_to_srgb(color_data[cpt_idx][1]),
                                        color_linear_to_srgb(color_data[cpt_idx][2]),
                                        color_data[cpt_idx][3]]
                                vertex_color.data[loop_idx].color = srgb_color
            offset = offset + prim.vertices_length
