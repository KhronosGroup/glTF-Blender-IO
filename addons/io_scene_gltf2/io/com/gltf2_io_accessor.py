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

import struct
from .gltf2_io_bufferview import *
from .gltf2_io_sparse import *


class Accessor():
    def __init__(self, index, json, gltf):
        self.json  = json   # Accessor json
        self.gltf =  gltf # Reference to global glTF instance

        # glTF2.0 required properties
        self.componentType = None
        self.count = None
        self.type = None

        # glTF2.0 not required properties, with default values
        self.byteOffset = 0
        self.normalized = False

        # glTF2.0 not required properties
        self.bufferView_ = None #TODO must be renamed, already an attribute with this name in my code
        self.max = None
        self.min = None
        self.sparse = None
        self.name = ""
        self.extensions = {}
        self.extras = {}
