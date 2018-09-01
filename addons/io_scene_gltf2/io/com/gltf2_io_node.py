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
 * This development is done in strong collaboration with Airbus Defence & Space
 """

from .gltf2_io_mesh import *
from .gltf2_io_camera import *
from .gltf2_io_animation import *

from .gltf2_io_trs import *

class PyNode():
    def __init__(self, index, json, gltf, scene):
        self.index = index
        self.json = json   # Node json
        self.gltf = gltf # Reference to global glTF instance
        self.scene = scene # Reference to scene


        # glTF2.0 required properties
        # No required !

        # glTF2.0 not required properties, with default values
        self.matrix      = [1.0,0.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0,0.0,1.0]
        self.rotation    = [0.0,0.0,0.0,1.0]
        self.scale       = [1.0,1.0,1.0]
        self.translation = [0.0,0.0,0.0]

        # glTF2.0 not required properties
        #TODO : note that all these properties are not managed yet
        self.camera = None
        self.children = []
        self.skin = None #TODO
        self.mesh = None
        self.weights = []
        self.name = ""
        self.extensions = {}
        self.extras = {}

        # PyNode specific

        self.animation = AnimationData(self, self.gltf)
        self.is_joint = False
        self.parent = None
        self.transform = [1.0,0.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0,0.0,1.0]

    def read(self):
        if 'name' in self.json.keys():
            self.name = self.json['name']
            self.gltf.log.info("Node " + self.json['name'])
        else:
            self.name = None
            self.gltf.log.info("Node index " + str(self.index))

        self.transform = self.get_transforms()

        if 'mesh' in self.json.keys():
            if self.json['mesh'] not in self.gltf.meshes.keys():
                self.gltf.meshes[self.json['mesh']] = PyMesh(self.json['mesh'], self.gltf.json['meshes'][self.json['mesh']], self.gltf)
                self.mesh = self.gltf.meshes[self.json['mesh']]
                self.mesh.read()
            else:
                self.mesh = self.gltf.meshes[self.json['mesh']]

            if 'skin' in self.json.keys():
                self.mesh.rig(self.json['skin'], self.index)

        if 'camera' in self.json.keys():
            self.camera = PyCamera(self.json['camera'], self.name, self.gltf.json['cameras'][self.json['camera']], self.gltf)
            self.camera.read()

        if not 'children' in self.json.keys():
            return

        for child in self.json['children']:
            child = PyNode(child, self.gltf.json['nodes'][child], self.gltf, self.scene)
            child.read()
            self.children.append(child)
            self.scene.nodes[child.index] = child

    def get_transforms(self):

        if 'matrix' in self.json.keys():
            self.matrix = self.json['matrix']
            return self.matrix

        #No matrix, but TRS
        mat = self.transform #init

        if 'scale' in self.json.keys():
            self.scale = self.json['scale']
            mat = TRS.scale_to_matrix(self.scale)


        if 'rotation' in self.json.keys():
            self.rotation = self.json['rotation']
            q_mat = TRS.quaternion_to_matrix(self.rotation)
            mat = TRS.matrix_multiply(q_mat, mat)

        if 'translation' in self.json.keys():
            self.translation = self.json['translation']
            loc_mat = TRS.translation_to_matrix(self.translation)
            mat = TRS.matrix_multiply(loc_mat, mat)

        return mat
