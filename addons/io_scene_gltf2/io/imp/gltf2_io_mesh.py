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

from ..com.gltf2_io_mesh import *

class MeshImporter():

    @staticmethod
    def read(pymesh):
        if 'name' in pymesh.json.keys():
            pymesh.name = pymesh.json['name']
            pymesh.gltf.log.debug("Mesh " + pymesh.json['name'])
        else:
            pymesh.gltf.log.debug("Mesh index " + str(pymesh.index))

        cpt_idx_prim = 0
        for primitive_it in pymesh.json['primitives']:
            primitive = PyPrimitive(cpt_idx_prim, primitive_it, pymesh.gltf)
            primitive.read()
            pymesh.primitives.append(primitive)
            cpt_idx_prim += 1

        # reading default targets weights if any
        if 'weights' in pymesh.json.keys():
            for weight in pymesh.json['weights']:
                pymesh.target_weights.append(weight)

    @staticmethod
    def importer(idx, json, gltf):
        mesh = PyMesh(idx, json, gltf)
        MeshImporter.read(mesh)
        return mesh
