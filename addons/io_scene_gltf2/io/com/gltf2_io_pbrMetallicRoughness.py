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
from ...blender.imp.material.texture import * #SPLIT_TODO

class PyPbr():

    SIMPLE  = 1
    TEXTURE = 2
    TEXTURE_FACTOR = 3

    def __init__(self, json, gltf):
        self.json = json # pbrMetallicRoughness json
        self.gltf = gltf # Reference to global glTF instance

        self.color_type = self.SIMPLE
        self.vertex_color = False
        self.metallic_type = self.SIMPLE

        # Default values
        self.baseColorFactor = [1,1,1,1]
        self.baseColorTexture = None
        self.metallicFactor = 1
        self.roughnessFactor = 1
        self.metallicRoughnessTexture = None
        self.extensions = None
        self.extras = None

    def read(self):
        if self.json is None:
            return # will use default values

        if 'baseColorTexture' in self.json.keys():
            self.color_type = self.TEXTURE
            self.baseColorTexture = Texture(self.json['baseColorTexture']['index'], self.gltf.json['textures'][self.json['baseColorTexture']['index']], self.gltf)
            self.baseColorTexture.read()
            self.baseColorTexture.debug_missing()

            if 'texCoord' in self.json['baseColorTexture']:
                self.baseColorTexture.texcoord = int(self.json['baseColorTexture']['texCoord'])
            else:
                self.baseColorTexture.texcoord = 0

        if 'metallicRoughnessTexture' in self.json.keys():
            self.metallic_type = self.TEXTURE
            self.metallicRoughnessTexture = Texture(self.json['metallicRoughnessTexture']['index'], self.gltf.json['textures'][self.json['metallicRoughnessTexture']['index']], self.gltf)
            self.metallicRoughnessTexture.read()
            self.metallicRoughnessTexture.debug_missing()

            if 'texCoord' in self.json['metallicRoughnessTexture']:
                self.metallicRoughnessTexture.texcoord = int(self.json['metallicRoughnessTexture']['texCoord'])
            else:
                self.metallicRoughnessTexture.texcoord = 0

        if 'baseColorFactor' in self.json.keys():
            self.baseColorFactor = self.json['baseColorFactor']
            if self.color_type == self.TEXTURE and self.baseColorFactor != [1.0,1.0,1.0]:
                self.color_type = self.TEXTURE_FACTOR

        if 'metallicFactor' in self.json.keys():
            self.metallicFactor = self.json['metallicFactor']
            if self.metallic_type == self.TEXTURE and self.metallicFactor != 1.0 and self.roughnessFactor != 1.0:
                self.metallic_type = self.TEXTURE_FACTOR

        if 'roughnessFactor' in self.json.keys():
            self.roughnessFactor = self.json['roughnessFactor']
            if self.metallic_type == self.TEXTURE and self.roughnessFactor != 1.0 and self.metallicFactor != 1.0:
                self.metallic_type = self.TEXTURE_FACTOR

    def debug_missing(self):
        if self.json is None:
            return
        keys = [
                'baseColorFactor',
                'metallicFactor',
                'roughnessFactor',
                'baseColorTexture',
                'metallicRoughnessTexture'
                ]

        for key in self.json.keys():
            if key not in keys:
                self.gltf.log.debug("PBR MISSING " + key)
