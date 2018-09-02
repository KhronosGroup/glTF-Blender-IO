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

from .gltf2_io_pbrMetallicRoughness import *
from .gltf2_io_map import *
from .gltf2_io_KHR_materials_pbrSpecularGlossiness import *

class PyMaterial():
    def __init__(self, index, json, gltf):
        self.index = index
        self.json = json # Material json
        self.gltf = gltf # Reference to global glTF instance

        # glTF2.0 required properties
        # No required properties!

        # glTF2.0 not required properties, with default values
        self.emissiveFactor = [0,0,0]
        self.alphaMode = "OPAQUE"
        self.alphaCutoff = 0.5
        self.doubleSided = False

        # glTF2.0 not required properties
        self.name = ""
        self.pbrMetallicRoughness = None    #TODO linked to self.pbr
        self.normalTexture = None           #TODO linked to self.normalmap
        self.occlusionTexture = None        #TODO linked to self.occlusionmap
        self.emissiveTexture = None         #TODO linked to self.emissivemap
        self.extensions = {}
        self.extras = {}

        # PyMaterial spefifics

        self.emissivemap  = None
        self.normalmap    = None
        self.occlusionmap = None
