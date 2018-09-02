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
from .gltf2_io_material import *

class PyPrimitive():
    def __init__(self, index, json, gltf):
        self.index = index
        self.json  = json  # Primitive json
        self.gltf = gltf # Reference to global glTF instance

        # glTF2.0 required properties
        self.attributes = {}

        # glTF2.0 not required properties, with default values
        self.mode = 4

        # glTF2.0 not required properties
        self.indices_ = None #TODO: to be renamed, because my code already has a indice attribute
        self.material = None
        self.targets = [] # shapekeys
        self.extensions = {}
        self.extras = {}

        # PyPrimitive specific
        self.mat = None
