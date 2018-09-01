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

from .gltf2_io_texture import *

class PyKHR_materials_pbrSpecularGlossiness():

    SIMPLE  = 1
    TEXTURE = 2
    TEXTURE_FACTOR = 3

    def __init__(self, json, gltf):
        self.json = json # KHR_materials_pbrSpecularGlossiness json
        self.gltf = gltf # Reference to global glTF instance

        # KHR_materials_pbrSpecularGlossiness required properties
        # No required properties

        # KHR_materials_pbrSpecularGlossiness not required properties, with default values
        self.diffuseFactor    = [1.0,1.0,1.0,1.0]
        self.specularFactor   = [1.0,1.0,1.0]
        self.glossinessFactor = 1.0

        # KHR_materials_pbrSpecularGlossiness not required properties
        self.diffuseTexture_ = None             #TODO rename, already attribute with this name
        self.specularGlossinessFactor_ = None   #TODO rename, already attribute with this name

        self.diffuse_type   = self.SIMPLE
        self.specgloss_type = self.SIMPLE
        self.vertex_color   = False

    def read(self):
        if self.json is None:
            return # will use default values

        if 'diffuseTexture' in self.json.keys():
            self.diffuse_type = self.TEXTURE
            self.diffuseTexture = PyTexture(self.json['diffuseTexture']['index'], self.gltf.json['textures'][self.json['diffuseTexture']['index']], self.gltf)
            self.diffuseTexture.read()

            if 'texCoord' in self.json['diffuseTexture']:
                self.diffuseTexture.texcoord = int(self.json['diffuseTexture']['texCoord'])
            else:
                self.diffuseTexture.texcoord = 0

        if 'diffuseFactor' in self.json.keys():
            self.diffuseFactor = self.json['diffuseFactor']
            if self.diffuse_type == self.TEXTURE and self.diffuseFactor != [1.0,1.0,1.0,1.0]:
                self.diffuse_type = self.TEXTURE_FACTOR

        if 'specularGlossinessTexture' in self.json.keys():
            self.specgloss_type = self.TEXTURE
            self.specularGlossinessTexture = PyTexture(self.json['specularGlossinessTexture']['index'], self.gltf.json['textures'][self.json['specularGlossinessTexture']['index']], self.gltf)
            self.specularGlossinessTexture.read()

            if 'texCoord' in self.json['specularGlossinessTexture']:
                self.specularGlossinessTexture.texcoord = int(self.json['specularGlossinessTexture']['texCoord'])
            else:
                self.specularGlossinessTexture.texcoord = 0

        if 'glossinessFactor' in self.json.keys():
            self.glossinessFactor = self.json['glossinessFactor']

        if 'specularFactor' in self.json.keys():
            self.specularFactor = self.json['specularFactor']
            if self.specgloss_type == self.TEXTURE and self.specgloss_type != [1.0,1.0,1.0]:
                self.specgloss_type = self.TEXTURE_FACTOR


    def use_vertex_color(self):
        self.vertex_color = True
