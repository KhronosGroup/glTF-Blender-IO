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

from .....io.com.gltf2_io_texture import *

class Map():
    def __init__(self, json, factor, gltf):
        self.json   = json # map json
        self.factor = factor
        self.gltf   = gltf # Reference to global glTF instance

    def read(self):
        self.texture = PyTexture(self.json['index'], self.gltf.json['textures'][self.json['index']], self.gltf)
        self.texture.read()

        if 'texCoord' in self.json.keys():
            self.texCoord = int(self.json['texCoord'])
        else:
            self.texCoord = 0

    def create_blender(self):
        pass

    def debug_missing(self):

        keys = [
                'index',
                'texCoord'
                ]

        for key in self.json.keys():
            if key not in keys:
                self.gltf.log.debug("MAP MISSING " + key)
