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

class BlenderPrimitive():

    @staticmethod
    def create(pyprimitive, verts, edges, faces):

        pyprimitive.blender_texcoord = {}

        # TODO mode of primitive 4 for now.
        current_length = len(verts)
        prim_verts = [Conversion.loc_gltf_to_blender(vert) for vert in pyprimitive.attributes['POSITION']['result']]
        pyprimitive.vertices_length = len(prim_verts)
        verts.extend(prim_verts)
        prim_faces = []
        for i in range(0, len(pyprimitive.indices), 3):
            vals = pyprimitive.indices[i:i+3]
            new_vals = []
            for y in vals:
                new_vals.append(y+current_length)
            prim_faces.append(tuple(new_vals))
        faces.extend(prim_faces)
        pyprimitive.faces_length = len(prim_faces)

        # manage material of primitive
        if pyprimitive.mat:

            # Create Blender material
            if not hasattr(pyprimitive.mat, "blender_material"):
                BlenderMaterial.create(pyprimitive.mat)

        return verts, edges, faces

    def set_normals(pyprimitive, mesh, offset):
        if 'NORMAL' in pyprimitive.attributes.keys():
            for poly in mesh.polygons:
                for loop_idx in range(poly.loop_start, poly.loop_start + poly.loop_total):
                    vert_idx = mesh.loops[loop_idx].vertex_index
                    if vert_idx in range(offset, offset + pyprimitive.vertices_length):
                        cpt_vert = vert_idx - offset
                        mesh.vertices[vert_idx].normal = pyprimitive.attributes['NORMAL']['result'][cpt_vert]
        offset = offset + pyprimitive.vertices_length
        return offset

    def set_UV(pyprimitive, obj, mesh, offset):
        for texcoord in [attr for attr in pyprimitive.attributes.keys() if attr[:9] == "TEXCOORD_"]:
            if not texcoord in mesh.uv_textures:
                mesh.uv_textures.new(texcoord)
                pyprimitive.blender_texcoord[int(texcoord[9:])] = texcoord

            for poly in mesh.polygons:
                for loop_idx in range(poly.loop_start, poly.loop_start + poly.loop_total):
                    vert_idx = mesh.loops[loop_idx].vertex_index
                    if vert_idx in range(offset, offset + pyprimitive.vertices_length):
                        obj.data.uv_layers[texcoord].data[loop_idx].uv = Vector((pyprimitive.attributes[texcoord]['result'][vert_idx-offset][0], 1-pyprimitive.attributes[texcoord]['result'][vert_idx-offset][1]))

        offset = offset + pyprimitive.vertices_length
        return offset

    def set_UV_in_mat(pyprimitive, obj):
        if hasattr(pyprimitive.mat, "KHR_materials_pbrSpecularGlossiness"):
            if pyprimitive.mat.KHR_materials_pbrSpecularGlossiness.diffuse_type in [pyprimitive.mat.KHR_materials_pbrSpecularGlossiness.TEXTURE, pyprimitive.mat.KHR_materials_pbrSpecularGlossiness.TEXTURE_FACTOR]:
                BlenderMaterial.set_uvmap(pyprimitive.mat, pyprimitive, obj)
            else:
                if pyprimitive.mat.KHR_materials_pbrSpecularGlossiness.specgloss_type in [pyprimitive.mat.KHR_materials_pbrSpecularGlossiness.TEXTURE, pyprimitive.mat.KHR_materials_pbrSpecularGlossiness.TEXTURE_FACTOR]:
                    BlenderMaterial.set_uvmap(pyprimitive.mat, pyprimitive, obj)

        else:
            if pyprimitive.mat.pbr.color_type in [pyprimitive.mat.pbr.TEXTURE, pyprimitive.mat.pbr.TEXTURE_FACTOR] :
                BlenderMaterial.set_uvmap(pyprimitive.mat, pyprimitive, obj)
            else:
                if pyprimitive.mat.pbr.metallic_type in [pyprimitive.mat.pbr.TEXTURE, pyprimitive.mat.pbr.TEXTURE_FACTOR] :
                    BlenderMaterial.set_uvmap(pyprimitive.mat, pyprimitive, obj)

    def assign_material(pyprimitive, obj, bm, offset, cpt_index_mat):
        obj.data.materials.append(bpy.data.materials[pyprimitive.mat.blender_material])
        for vert in bm.verts:
            if vert.index in range(offset, offset + pyprimitive.vertices_length):
                for loop in vert.link_loops:
                    face = loop.face.index
                    bm.faces[face].material_index = cpt_index_mat
        cpt_index_mat += 1
        offset = offset + pyprimitive.vertices_length
        return offset, cpt_index_mat
