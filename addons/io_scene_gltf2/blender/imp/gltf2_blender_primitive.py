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
from mathutils import Vector

from .gltf2_blender_material import BlenderMaterial
from ..com.gltf2_blender_conversion import loc_gltf_to_blender
from ...io.imp.gltf2_io_binary import BinaryData


class BlenderPrimitive():
    """Blender Primitive."""
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("%s should not be instantiated" % cls)

    @staticmethod
    def create(gltf, pyprimitive, verts, edges, faces):
        """Primitive creation."""
        pyprimitive.blender_texcoord = {}

        # TODO mode of primitive 4 for now.
        current_length = len(verts)
        pos = BinaryData.get_data_from_accessor(gltf, pyprimitive.attributes['POSITION'])
        if pyprimitive.indices is not None:
            indices = BinaryData.get_data_from_accessor(gltf, pyprimitive.indices)
        else:
            indices = []
            indices_ = range(0, len(pos))
            for i in indices_:
                indices.append((i,))

        pyprimitive.tmp_indices = indices

        # Manage only vertices that are in indices tab
        indice_equivalents = {}
        new_pos = []
        new_pos_idx = 0
        for i in indices:
            if i[0] not in indice_equivalents.keys():
                indice_equivalents[i[0]] = new_pos_idx
                new_pos.append(pos[i[0]])
                new_pos_idx += 1

        prim_verts = [loc_gltf_to_blender(vert) for vert in new_pos]

        pyprimitive.vertices_length = len(prim_verts)
        verts.extend(prim_verts)
        prim_faces = []
        for i in range(0, len(indices), 3):
            vals = indices[i:i + 3]
            new_vals = []
            for y in vals:
                new_vals.append(indice_equivalents[y[0]] + current_length)
            prim_faces.append(tuple(new_vals))
        faces.extend(prim_faces)
        pyprimitive.faces_length = len(prim_faces)

        # manage material of primitive
        if pyprimitive.material is not None:

            vertex_color = None
            if 'COLOR_0' in pyprimitive.attributes.keys():
                vertex_color = 'COLOR_0'

            # Create Blender material if needed
            if vertex_color is None:
                if None not in gltf.data.materials[pyprimitive.material].blender_material.keys():
                    BlenderMaterial.create(gltf, pyprimitive.material, vertex_color)
            else:
                if vertex_color not in gltf.data.materials[pyprimitive.material].blender_material.keys():
                    BlenderMaterial.create(gltf, pyprimitive.material, vertex_color)


        return verts, edges, faces

    def set_normals(gltf, pyprimitive, mesh, offset, custom_normals):
        """Set Normal."""
        if 'NORMAL' in pyprimitive.attributes.keys():
            original_normal_data = BinaryData.get_data_from_accessor(gltf, pyprimitive.attributes['NORMAL'])

            tmp_indices = {}
            tmp_idx = 0
            normal_data = []
            for i in pyprimitive.tmp_indices:
                if i[0] not in tmp_indices.keys():
                    tmp_indices[i[0]] = tmp_idx
                    tmp_idx += 1
                    normal_data.append(original_normal_data[i[0]])

            for poly in mesh.polygons:
                if gltf.import_settings['import_shading'] == "NORMALS":
                    calc_norm_vertices = []
                    for loop_idx in range(poly.loop_start, poly.loop_start + poly.loop_total):
                        vert_idx = mesh.loops[loop_idx].vertex_index
                        if vert_idx in range(offset, offset + pyprimitive.vertices_length):
                            cpt_vert = vert_idx - offset
                            mesh.vertices[vert_idx].normal = normal_data[cpt_vert]
                            custom_normals[vert_idx] = list(normal_data[cpt_vert])
                            calc_norm_vertices.append(vert_idx)

                        if len(calc_norm_vertices) == 3:
                            # Calcul normal
                            vert0 = mesh.vertices[calc_norm_vertices[0]].co
                            vert1 = mesh.vertices[calc_norm_vertices[1]].co
                            vert2 = mesh.vertices[calc_norm_vertices[2]].co
                            calc_normal = (vert1 - vert0).cross(vert2 - vert0).normalized()

                            # Compare normal to vertex normal
                            for i in calc_norm_vertices:
                                cpt_vert = vert_idx - offset
                                vec = Vector(
                                    (normal_data[cpt_vert][0], normal_data[cpt_vert][1], normal_data[cpt_vert][2])
                                )
                                if not calc_normal.dot(vec) > 0.9999999:
                                    poly.use_smooth = True
                                    break
                elif gltf.import_settings['import_shading'] == "FLAT":
                    poly.use_smooth = False
                elif gltf.import_settings['import_shading'] == "SMOOTH":
                    poly.use_smooth = True
                else:
                    pass  # Should not happend

        offset = offset + pyprimitive.vertices_length
        return offset

    def set_UV(gltf, pyprimitive, obj, mesh, offset):
        """Set UV Map."""
        for texcoord in [attr for attr in pyprimitive.attributes.keys() if attr[:9] == "TEXCOORD_"]:
            if bpy.app.version < (2, 80, 0):
                if texcoord not in mesh.uv_textures:
                    mesh.uv_textures.new(texcoord)
                pyprimitive.blender_texcoord[int(texcoord[9:])] = texcoord
            else:
                if texcoord not in mesh.uv_layers:
                    mesh.uv_layers.new(name=texcoord)
                pyprimitive.blender_texcoord[int(texcoord[9:])] = texcoord

            original_texcoord_data = BinaryData.get_data_from_accessor(gltf, pyprimitive.attributes[texcoord])


            tmp_indices = {}
            tmp_idx = 0
            texcoord_data = []
            for i in pyprimitive.tmp_indices:
                if i[0] not in tmp_indices.keys():
                    tmp_indices[i[0]] = tmp_idx
                    tmp_idx += 1
                    texcoord_data.append(original_texcoord_data[i[0]])

            for poly in mesh.polygons:
                for loop_idx in range(poly.loop_start, poly.loop_start + poly.loop_total):
                    vert_idx = mesh.loops[loop_idx].vertex_index
                    if vert_idx in range(offset, offset + pyprimitive.vertices_length):
                        obj.data.uv_layers[texcoord].data[loop_idx].uv = \
                            Vector((texcoord_data[vert_idx - offset][0], 1 - texcoord_data[vert_idx - offset][1]))

        offset = offset + pyprimitive.vertices_length
        return offset

    def set_UV_in_mat(gltf, pyprimitive, obj, vertex_color):
        """After nodetree creation, set UVMap in nodes."""
        if pyprimitive.material is None:
            return
        if gltf.data.materials[pyprimitive.material].extensions \
                and "KHR_materials_pbrSpecularGlossiness" in \
                    gltf.data.materials[pyprimitive.material].extensions.keys():
            if pyprimitive.material is not None \
                    and gltf.data.materials[pyprimitive.material].extensions[
                        'KHR_materials_pbrSpecularGlossiness'
                    ]['diffuse_type'] in [gltf.TEXTURE, gltf.TEXTURE_FACTOR]:
                BlenderMaterial.set_uvmap(gltf, pyprimitive.material, pyprimitive, obj, vertex_color)
            else:
                if pyprimitive.material is not None \
                        and gltf.data.materials[pyprimitive.material].extensions[
                            'KHR_materials_pbrSpecularGlossiness'
                        ]['specgloss_type'] in [gltf.TEXTURE, gltf.TEXTURE_FACTOR]:
                    BlenderMaterial.set_uvmap(gltf, pyprimitive.material, pyprimitive, obj, vertex_color)

        else:
            if pyprimitive.material is not None \
                    and gltf.data.materials[pyprimitive.material].pbr_metallic_roughness.color_type in \
                    [gltf.TEXTURE, gltf.TEXTURE_FACTOR]:
                BlenderMaterial.set_uvmap(gltf, pyprimitive.material, pyprimitive, obj, vertex_color)
            else:
                if pyprimitive.material is not None \
                        and gltf.data.materials[pyprimitive.material].pbr_metallic_roughness.metallic_type in \
                        [gltf.TEXTURE, gltf.TEXTURE_FACTOR]:
                    BlenderMaterial.set_uvmap(gltf, pyprimitive.material, pyprimitive, obj, vertex_color)

    def assign_material(gltf, pyprimitive, obj, bm, offset, cpt_index_mat):
        """Assign material to faces of primitives."""
        if pyprimitive.material is not None:

            vertex_color = None
            if 'COLOR_0' in pyprimitive.attributes.keys():
                vertex_color = 'COLOR_0'

            obj.data.materials.append(bpy.data.materials[gltf.data.materials[pyprimitive.material].blender_material[vertex_color]])
            for vert in bm.verts:
                if vert.index in range(offset, offset + pyprimitive.vertices_length):
                    for loop in vert.link_loops:
                        face = loop.face.index
                        bm.faces[face].material_index = cpt_index_mat
            cpt_index_mat += 1
        offset = offset + pyprimitive.vertices_length
        return offset, cpt_index_mat
