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

from .gltf2_io_primitive import *
from .gltf2_io_skin import *

class PyMesh():
    def __init__(self, index, json, gltf):
        self.index = index
        self.json = json    # Mesh json
        self.gltf = gltf  # Reference to global glTF instance

        # glTF2.0 required properties
        self.primitives = []

        # glTF2.0 not required properties
        self.target_weights = [] #TODO to be renamed weights
        self.name = None
        self.extensions = {}
        self.extras = {}

        # PyMesh specific
        self.skin = None


    def rig(self, skin_id, mesh_id):
        if skin_id not in self.gltf.skins.keys():
            self.skin = PySkin(skin_id, self.gltf.json['skins'][skin_id], self.gltf)
            self.skin.mesh_id = mesh_id
            self.gltf.skins[skin_id] = self.skin
            self.skin.read()
        else:
            self.skin = self.gltf.skins[skin_id]
