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

import bpy
from .gltf2_io_pbrMetallicRoughness import *
from ...blender.imp.material.map.normalmap import * #SPLIT_TODO
from ...blender.imp.material.map.emissivemap import * #SPLIT_TODO
from ...blender.imp.material.map.occlusionmap import * #SPLIT_TODO
from ...blender.imp.material.extensions import * #SPLIT_TODO

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

    def read(self):

        # If no index, this is the default material
        if self.index is None:
            self.pbr = Pbr(None, self.gltf)
            self.pbr.read()
            self.name = "Default Material"
            return

        if 'extensions' in self.json.keys():
            if 'KHR_materials_pbrSpecularGlossiness' in self.json['extensions'].keys():
                self.KHR_materials_pbrSpecularGlossiness = KHR_materials_pbrSpecularGlossiness(self.json['extensions']['KHR_materials_pbrSpecularGlossiness'], self.gltf)
                self.KHR_materials_pbrSpecularGlossiness.read()
                self.KHR_materials_pbrSpecularGlossiness.debug_missing()

        # Not default material
        if 'name' in self.json.keys():
            self.name = self.json['name']

        if 'pbrMetallicRoughness' in self.json.keys():
            self.pbr = PyPbr(self.json['pbrMetallicRoughness'], self.gltf)
        else:
            self.pbr = PyPbr(None, self.gltf)
        self.pbr.read()

        # Emission
        if 'emissiveTexture' in self.json.keys():
            if 'emissiveFactor' in self.json.keys():
                factor = self.json['emissiveFactor'] #TODO use self.emissiveFactor
            else:
                factor = [1.0, 1.0, 1.0]

            self.emissivemap = EmissiveMap(self.json['emissiveTexture'], factor, self.gltf)
            self.emissivemap.read()

        # Normal Map
        if 'normalTexture' in self.json.keys():
            self.normalmap = NormalMap(self.json['normalTexture'], 1.0, self.gltf)
            self.normalmap.read()

        # Occlusion Map
        if 'occlusionTexture' in self.json.keys():
            self.occlusionmap = OcclusionMap(self.json['occlusionTexture'], 1.0, self.gltf)
            self.occlusionmap.read()

    def use_vertex_color(self):
        if hasattr(self, 'KHR_materials_pbrSpecularGlossiness'):
            self.KHR_materials_pbrSpecularGlossiness.use_vertex_color()
        else:
            self.pbr.use_vertex_color()
