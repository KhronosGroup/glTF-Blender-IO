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

from ...blender.imp.mesh.primitive import *
from ...blender.imp.rig import *

class PyMesh():
    def __init__(self, index, json, gltf):
        self.index = index
        self.json = json    # Mesh json
        self.gltf = gltf  # Reference to global glTF instance

        # glTF2.0 required properties
        self.primitives = []

        # glTF22.0 not required properties
        self.target_weights = [] #TODO to be renamed weights
        self.name = None
        self.extensions = {}
        self.extras = {}

        # PyMesh specific
        self.skin = None


    def read(self):
        if 'name' in self.json.keys():
            self.name = self.json['name']
            self.gltf.log.debug("Mesh " + self.json['name'])
        else:
            self.gltf.log.debug("Mesh index " + str(self.index))

        cpt_idx_prim = 0
        for primitive_it in self.json['primitives']:
            primitive = Primitive(cpt_idx_prim, primitive_it, self.gltf)
            primitive.read()
            self.primitives.append(primitive)
            primitive.debug_missing()
            cpt_idx_prim += 1

        # reading default targets weights if any
        if 'weights' in self.json.keys():
            for weight in self.json['weights']:
                self.target_weights.append(weight)

    def rig(self, skin_id, mesh_id):
        if skin_id not in self.gltf.skins.keys():
            self.skin = Skin(skin_id, self.gltf.json['skins'][skin_id], self.gltf)
            self.skin.mesh_id = mesh_id
            self.gltf.skins[skin_id] = self.skin
            self.skin.read()
            self.skin.debug_missing()
        else:
            self.skin = self.gltf.skins[skin_id]
