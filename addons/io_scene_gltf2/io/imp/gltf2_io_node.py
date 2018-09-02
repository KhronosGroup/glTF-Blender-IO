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

from ..com.gltf2_io_node import *
from .gltf2_io_camera import *
from .gltf2_io_mesh import *

class NodeImporter():

    @staticmethod
    def get_transforms(pynode):

        if 'matrix' in pynode.json.keys():
            pynode.matrix = pynode.json['matrix']
            return pynode.matrix

        #No matrix, but TRS
        mat = pynode.transform #init

        if 'scale' in pynode.json.keys():
            pynode.scale = pynode.json['scale']
            mat = TRS.scale_to_matrix(pynode.scale)


        if 'rotation' in pynode.json.keys():
            pynode.rotation = pynode.json['rotation']
            q_mat = TRS.quaternion_to_matrix(pynode.rotation)
            mat = TRS.matrix_multiply(q_mat, mat)

        if 'translation' in pynode.json.keys():
            pynode.translation = pynode.json['translation']
            loc_mat = TRS.translation_to_matrix(pynode.translation)
            mat = TRS.matrix_multiply(loc_mat, mat)

        return mat

    @staticmethod
    def read(pynode):
        if 'name' in pynode.json.keys():
            pynode.name = pynode.json['name']
            pynode.gltf.log.info("Node " + pynode.json['name'])
        else:
            pynode.name = None
            pynode.gltf.log.info("Node index " + str(pynode.index))

        pynode.transform = NodeImporter.get_transforms(pynode)

        if 'mesh' in pynode.json.keys():
            if pynode.json['mesh'] not in pynode.gltf.meshes.keys():
                pynode.gltf.meshes[pynode.json['mesh']] = MeshImporter.importer(pynode.json['mesh'], pynode.gltf.json['meshes'][pynode.json['mesh']], pynode.gltf)
                pynode.mesh = pynode.gltf.meshes[pynode.json['mesh']]
            else:
                pynode.mesh = pynode.gltf.meshes[pynode.json['mesh']]

            if 'skin' in pynode.json.keys():
                MeshImporter.rig(pynode.mesh, pynode.json['skin'], pynode.index)

        if 'camera' in pynode.json.keys():
            pynode.camera = CameraImporter.importer(pynode.json['camera'], pynode.name, pynode.gltf.json['cameras'][pynode.json['camera']], pynode.gltf)

        if not 'children' in pynode.json.keys():
            return

        for child in pynode.json['children']:
            child = NodeImporter.importer(child, pynode.gltf.json['nodes'][child], pynode.gltf, pynode.scene)
            pynode.children.append(child)
            pynode.scene.nodes[child.index] = child

    @staticmethod
    def importer(idx, json, gltf, pyscene):
        node = PyNode(idx, json, gltf, pyscene)
        NodeImporter.read(node)
        return node
