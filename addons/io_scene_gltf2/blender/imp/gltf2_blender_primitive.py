"""
 * ***** BEGIN GPL LICENSE BLOCK *****
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License
 * as published by the Free Software Foundation; either version 2
 * of the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software Foundation,
 * Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
 *
 * Contributor(s): Julien Duroure.
 *
 * ***** END GPL LICENSE BLOCK *****
 """

import bpy
from mathutils import Vector

from .gltf2_blender_material import *
from ..com.gltf2_blender_conversion import *
from ...io.imp.gltf2_io_binary import *

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
            vals = indices[i:i+3]
            new_vals = []
            for y in vals:
                new_vals.append(y[0]+current_length)
            prim_faces.append(tuple(new_vals))
        faces.extend(prim_faces)
        pyprimitive.faces_length = len(prim_faces)

        # manage material of primitive
        if pyprimitive.material is not None:

            # Create Blender material
            if gltf.data.materials[pyprimitive.material].blender_material is None:
                BlenderMaterial.create(gltf, pyprimitive.material)

        return verts, edges, faces

    def set_normals(gltf, pyprimitive, mesh, offset):
        if 'NORMAL' in pyprimitive.attributes.keys():
            normal_data = BinaryData.get_data_from_accessor(gltf, pyprimitive.attributes['NORMAL'])
            for poly in mesh.polygons:
                for loop_idx in range(poly.loop_start, poly.loop_start + poly.loop_total):
                    vert_idx = mesh.loops[loop_idx].vertex_index
                    if vert_idx in range(offset, offset + pyprimitive.vertices_length):
                        cpt_vert = vert_idx - offset
                        mesh.vertices[vert_idx].normal = normal_data[cpt_vert]
        offset = offset + pyprimitive.vertices_length
        return offset

    def set_UV(gltf, pyprimitive, obj, mesh, offset):
        for texcoord in [attr for attr in pyprimitive.attributes.keys() if attr[:9] == "TEXCOORD_"]:
            if not texcoord in mesh.uv_textures:
                mesh.uv_textures.new(texcoord)
                pyprimitive.blender_texcoord[int(texcoord[9:])] = texcoord

            texcoord_data = BinaryData.get_data_from_accessor(gltf, pyprimitive.attributes[texcoord])
            for poly in mesh.polygons:
                for loop_idx in range(poly.loop_start, poly.loop_start + poly.loop_total):
                    vert_idx = mesh.loops[loop_idx].vertex_index
                    if vert_idx in range(offset, offset + pyprimitive.vertices_length):
                        obj.data.uv_layers[texcoord].data[loop_idx].uv = Vector((texcoord_data[vert_idx-offset][0], 1-texcoord_data[vert_idx-offset][1]))

        offset = offset + pyprimitive.vertices_length
        return offset

    def set_UV_in_mat(gltf, pyprimitive, obj):
        #TODO_SPLIT
        # if pyprimitive.material.extensions "KHR_materials_pbrSpecularGlossiness"):
        #     if pyprimitive.mat.KHR_materials_pbrSpecularGlossiness.diffuse_type in [pyprimitive.mat.KHR_materials_pbrSpecularGlossiness.TEXTURE, pyprimitive.mat.KHR_materials_pbrSpecularGlossiness.TEXTURE_FACTOR]:
        #         BlenderMaterial.set_uvmap(pyprimitive.mat, pyprimitive, obj)
        #     else:
        #         if pyprimitive.mat.KHR_materials_pbrSpecularGlossiness.specgloss_type in [pyprimitive.mat.KHR_materials_pbrSpecularGlossiness.TEXTURE, pyprimitive.mat.KHR_materials_pbrSpecularGlossiness.TEXTURE_FACTOR]:
        #             BlenderMaterial.set_uvmap(pyprimitive.mat, pyprimitive, obj)
        #
        # else:
        if pyprimitive.material is not None and gltf.data.materials[pyprimitive.material].pbr_metallic_roughness.color_type in [gltf.TEXTURE, gltf.TEXTURE_FACTOR] :
            BlenderMaterial.set_uvmap(gltf, pyprimitive.material, pyprimitive, obj)
        else:
            if pyprimitive.material is not None and gltf.data.materials[pyprimitive.material].pbr_metallic_roughness.metallic_type in [gltf.TEXTURE, gltf.TEXTURE_FACTOR] :
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
