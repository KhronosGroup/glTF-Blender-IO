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


from .gltf2_io_accessor import *

class PySkin():
    def __init__(self, index, json, gltf):
        self.index = index
        self.json  = json # skin json
        self.gltf  = gltf # Reference to global glTF instance


        # glTF2.0 required properties
        self.joints = [] #TODO is self.bones in my code ?

        # glTF2.0 not required properties
        self.inverseBindMatrices_ = None #TODO to be renamed, already attribute with this name
        self.skeleton = None #TODO is self.root in my code
        self.name  = None
        self.extensions = {}
        self.extras = {}

        # glTF2.0 specifics

        self.bones = [] #TODO is joints
        self.mesh_id = None
        self.root = None #TODO is skeleton

    def read(self):
        if 'skeleton' in self.json.keys():
            self.root = self.json['skeleton']

        if 'joints' in self.json.keys():
            self.bones = self.json['joints']

        if 'name' in self.json.keys():
            self.name = self.json['name']

        if 'inverseBindMatrices' in self.json.keys():
            if self.json['inverseBindMatrices'] not in self.gltf.accessors.keys():
                self.gltf.accessors[self.json['inverseBindMatrices']] = Accessor(self.json['inverseBindMatrices'], self.gltf.json['accessors'][self.json['inverseBindMatrices']], self.gltf)
                self.inverseBindMatrices = self.gltf.accessors[self.json['inverseBindMatrices']]
                self.data = self.inverseBindMatrices.read()
            else:
                self.inverseBindMatrices = self.gltf.accessors[self.json['inverseBindMatrices']]
                self.data = self.inverseBindMatrices.data
