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
import bmesh
from mathutils import Vector

from .gltf2_blender_material import BlenderMaterial
from .gltf2_blender_primitive import BlenderPrimitive
from ...io.imp.gltf2_io_binary import BinaryData
from ..com.gltf2_blender_conversion import loc_gltf_to_blender


class BlenderMesh():
    """Blender Mesh."""
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("%s should not be instantiated" % cls)

    @staticmethod
    def create(gltf, mesh_idx, node_idx, parent):
        """Mesh creation."""
        pymesh = gltf.data.meshes[mesh_idx]

        # Create one bmesh, add all primitives to it, and then convert it to a
        # mesh.
        bme = bmesh.new()

        # List of all the materials this mesh will use. The material each
        # primitive uses is set by giving an index into this list.
        materials = []

        # Process all primitives
        for prim in pymesh.primitives:
            prim.blender_texcoord = {}

            if prim.material is None:
                material_idx = None
            else:
                pymaterial = gltf.data.materials[prim.material]

                vertex_color = None
                if 'COLOR_0' in prim.attributes:
                    vertex_color = 'COLOR_0'

                # Create Blender material if needed
                if vertex_color not in pymaterial.blender_material:
                    BlenderMaterial.create(gltf, prim.material, vertex_color)
                material_name = pymaterial.blender_material[vertex_color]
                material = bpy.data.materials[material_name]

                try:
                    material_idx = materials.index(material)
                except ValueError:
                    materials.append(material)
                    material_idx = len(materials) - 1

            BlenderPrimitive.add_primitive_to_bmesh(gltf, bme, pymesh, prim, material_idx)

        name = pymesh.name or 'Mesh_' + str(mesh_idx)
        mesh = bpy.data.meshes.new(name)
        BlenderMesh.bmesh_to_mesh(gltf, pymesh, bme, mesh)
        bme.free()
        for material in materials:
            mesh.materials.append(material)
        mesh.update()

        pymesh.blender_name = mesh.name

        return mesh

    @staticmethod
    def set_mesh(gltf, pymesh, mesh, obj):
        """Sets mesh data after creation."""
        # Object and UV are now created, we can set UVMap into material
        for prim in pymesh.primitives:
            vertex_color = None
            if 'COLOR_0' in prim.attributes.keys():
                vertex_color = 'COLOR_0'
            BlenderPrimitive.set_UV_in_mat(gltf, prim, obj, vertex_color)

        # set default weights for shape keys, and names, if not set by convention on extras data
        if pymesh.weights is not None:
            for i in range(len(pymesh.weights)):
                if pymesh.shapekey_names[i] is None: # No default value if shapekeys was not created
                    continue
                obj.data.shape_keys.key_blocks[pymesh.shapekey_names[i]].value = pymesh.weights[i]

    @staticmethod
    def bmesh_to_mesh(gltf, pymesh, bme, mesh):
        bme.to_mesh(mesh)

        # Unfortunately need to do shapekeys/normals/smoothing ourselves.

        # Shapekeys
        if len(bme.verts.layers.shape) != 0:
            # The only way I could find to create a shape key was to temporarily
            # parent mesh to an object and use obj.shape_key_add.
            tmp_ob = None
            try:
                tmp_ob = bpy.data.objects.new('##gltf-import:tmp-object##', mesh)
                tmp_ob.shape_key_add(name='Basis')
                mesh.shape_keys.name = mesh.name
                for layer_name in bme.verts.layers.shape.keys():
                    tmp_ob.shape_key_add(name=layer_name)
                    key_block = mesh.shape_keys.key_blocks[layer_name]
                    layer = bme.verts.layers.shape[layer_name]

                    for i, v in enumerate(bme.verts):
                        key_block.data[i].co = v[layer]
            finally:
                if tmp_ob:
                    bpy.data.objects.remove(tmp_ob)

        # Normals
        mesh.update()

        if gltf.import_settings['import_shading'] == "NORMALS":
            mesh.create_normals_split()

        # use_smooth for faces
        face_idx = 0
        for prim in pymesh.primitives:
            if 'NORMAL' not in prim.attributes:
                face_idx += prim.num_faces
                continue

            if gltf.import_settings['import_shading'] == "FLAT":
                for fi in range(face_idx, face_idx + prim.num_faces):
                    mesh.polygons[fi].use_smooth = False
            elif gltf.import_settings['import_shading'] == "SMOOTH":
                for fi in range(face_idx, face_idx + prim.num_faces):
                    mesh.polygons[fi].use_smooth = True
            elif gltf.import_settings['import_shading'] == "NORMALS":
                for fi in range(face_idx, face_idx + prim.num_faces):
                    poly = mesh.polygons[fi]
                    calc_norm_vertices = []
                    for loop_idx in range(poly.loop_start, poly.loop_start + poly.loop_total):
                        vert_idx = mesh.loops[loop_idx].vertex_index
                        calc_norm_vertices.append(vert_idx)

                        if len(calc_norm_vertices) == 3:
                            # Calcul normal
                            vert0 = mesh.vertices[calc_norm_vertices[0]].co
                            vert1 = mesh.vertices[calc_norm_vertices[1]].co
                            vert2 = mesh.vertices[calc_norm_vertices[2]].co
                            calc_normal = (vert1 - vert0).cross(vert2 - vert0).normalized()

                            # Compare normal to vertex normal
                            for i in calc_norm_vertices:
                                vec = Vector(bme.verts[i].normal)
                                if not calc_normal.dot(vec) > 0.9999999:
                                    poly.use_smooth = True
                                    break
            else:
                # shouldn't happen
                pass

            face_idx += prim.num_faces

        # Custom normals, now that every update is done
        if gltf.import_settings['import_shading'] == "NORMALS":
            custom_normals = [v.normal for v in bme.verts]
            mesh.normals_split_custom_set_from_vertices(custom_normals)
            mesh.use_auto_smooth = True
