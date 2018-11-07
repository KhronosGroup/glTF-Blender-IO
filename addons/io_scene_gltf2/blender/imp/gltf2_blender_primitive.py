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
from ..com.gltf2_blender_conversion import Conversion
from ...io.imp.gltf2_io_binary import BinaryData


class BlenderPrimitive():

    @staticmethod
    def create(gltf, pyprimitive, verts, edges, faces):

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

        prim_verts = [Conversion.loc_gltf_to_blender(vert) for vert in pos]
        pyprimitive.vertices_length = len(prim_verts)
        verts.extend(prim_verts)
        prim_faces = []
        for i in range(0, len(indices), 3):
            vals = indices[i:i + 3]
            new_vals = []
            for y in vals:
                new_vals.append(y[0] + current_length)
            prim_faces.append(tuple(new_vals))
        faces.extend(prim_faces)
        pyprimitive.faces_length = len(prim_faces)

        # manage material of primitive
        if pyprimitive.material is not None:

            # Create Blender material
            # TODO, a same material can have difference COLOR_0 multiplicator
            if gltf.data.materials[pyprimitive.material].blender_material is None:
                vertex_color = None
                if 'COLOR_0' in pyprimitive.attributes.keys():
                    vertex_color = pyprimitive.attributes['COLOR_0']
                BlenderMaterial.create(gltf, pyprimitive.material, vertex_color)

        return verts, edges, faces

    def set_normals(gltf, pyprimitive, mesh, offset):
        if 'NORMAL' in pyprimitive.attributes.keys():
            normal_data = BinaryData.get_data_from_accessor(gltf, pyprimitive.attributes['NORMAL'])
            for poly in mesh.polygons:
                if gltf.import_settings['shading'] == "NORMALS":
                    calc_norm_vertices = []
                    for loop_idx in range(poly.loop_start, poly.loop_start + poly.loop_total):
                        vert_idx = mesh.loops[loop_idx].vertex_index
                        if vert_idx in range(offset, offset + pyprimitive.vertices_length):
                            cpt_vert = vert_idx - offset
                            mesh.vertices[vert_idx].normal = normal_data[cpt_vert]
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
                elif gltf.import_settings['shading'] == "FLAT":
                    poly.use_smooth = False
                elif gltf.import_settings['shading'] == "SMOOTH":
                    poly.use_smooth = True
                else:
                    pass  # Should not happend

        offset = offset + pyprimitive.vertices_length
        return offset

    def set_UV(gltf, pyprimitive, obj, mesh, offset):
        for texcoord in [attr for attr in pyprimitive.attributes.keys() if attr[:9] == "TEXCOORD_"]:
            if bpy.app.version < (2, 80, 0):
                if texcoord not in mesh.uv_textures:
                    mesh.uv_textures.new(texcoord)
                    pyprimitive.blender_texcoord[int(texcoord[9:])] = texcoord
            else:
                if texcoord not in mesh.uv_layers:
                    mesh.uv_layers.new(name=texcoord)
                    pyprimitive.blender_texcoord[int(texcoord[9:])] = texcoord

            texcoord_data = BinaryData.get_data_from_accessor(gltf, pyprimitive.attributes[texcoord])
            for poly in mesh.polygons:
                for loop_idx in range(poly.loop_start, poly.loop_start + poly.loop_total):
                    vert_idx = mesh.loops[loop_idx].vertex_index
                    if vert_idx in range(offset, offset + pyprimitive.vertices_length):
                        obj.data.uv_layers[texcoord].data[loop_idx].uv = \
                            Vector((texcoord_data[vert_idx - offset][0], 1 - texcoord_data[vert_idx - offset][1]))

        offset = offset + pyprimitive.vertices_length
        return offset

    def set_UV_in_mat(gltf, pyprimitive, obj):
        if pyprimitive.material is None:
            return
        if gltf.data.materials[pyprimitive.material].extensions \
                and "KHR_materials_pbrSpecularGlossiness" in \
                    gltf.data.materials[pyprimitive.material].extensions.keys():
            if pyprimitive.material is not None \
                    and gltf.data.materials[pyprimitive.material].extensions[
                        'KHR_materials_pbrSpecularGlossiness'
                    ]['diffuse_type'] in [gltf.TEXTURE, gltf.TEXTURE_FACTOR]:
                BlenderMaterial.set_uvmap(gltf, pyprimitive.material, pyprimitive, obj)
            else:
                if pyprimitive.material is not None \
                        and gltf.data.materials[pyprimitive.material].extensions[
                            'KHR_materials_pbrSpecularGlossiness'
                        ]['specgloss_type'] in [gltf.TEXTURE, gltf.TEXTURE_FACTOR]:
                    BlenderMaterial.set_uvmap(gltf, pyprimitive.material, pyprimitive, obj)

        else:
            if pyprimitive.material is not None \
                    and gltf.data.materials[pyprimitive.material].pbr_metallic_roughness.color_type in \
                    [gltf.TEXTURE, gltf.TEXTURE_FACTOR]:
                BlenderMaterial.set_uvmap(gltf, pyprimitive.material, pyprimitive, obj)
            else:
                if pyprimitive.material is not None \
                        and gltf.data.materials[pyprimitive.material].pbr_metallic_roughness.metallic_type in \
                        [gltf.TEXTURE, gltf.TEXTURE_FACTOR]:
                    BlenderMaterial.set_uvmap(gltf, pyprimitive.material, pyprimitive, obj)

    def assign_material(gltf, pyprimitive, obj, bm, offset, cpt_index_mat):
        if pyprimitive.material is not None:
            obj.data.materials.append(bpy.data.materials[gltf.data.materials[pyprimitive.material].blender_material])
            for vert in bm.verts:
                if vert.index in range(offset, offset + pyprimitive.vertices_length):
                    for loop in vert.link_loops:
                        face = loop.face.index
                        bm.faces[face].material_index = cpt_index_mat
            cpt_index_mat += 1
        offset = offset + pyprimitive.vertices_length
        return offset, cpt_index_mat
