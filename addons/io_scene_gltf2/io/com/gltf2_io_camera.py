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


class PyCamera():
    def __init__(self, index, name, json, gltf):
        self.index = index
        self.json  = json # Camera json
        self.gltf =  gltf # Reference to global glTF instance

        # glTF2.0 required properties
        self.type = None

        # glTF2.0 not required properties
        self.orthographic = None
        self.perspective = None
        self.name = name            #TODO must be set here, not outside and pass as parameter
        self.extensions = {}
        self.extras = {}

        # PyCamera specifics
        # Lots of work TODO here
        # self.zfar
        # self.znear
        # self.aspectRatio
        # self.yfoc
        # self.xmag
        # self.ymag

    def read(self):
        if 'type' in self.json.keys():
            self.type = self.json['type']

        if self.type in self.json.keys():
            if 'zfar' in self.json[self.type].keys():
                self.zfar = self.json[self.type]['zfar']
            if 'znear' in self.json[self.type].keys():
                self.znear = self.json[self.type]['znear']

            if self.type == "perspective":
                if 'aspectRatio' in self.json[self.type].keys():
                    self.aspectRatio = self.json[self.type]['aspectRatio']
                if 'yfov' in self.json[self.type].keys():
                    self.yfoc = self.json[self.type]['yfov']
            elif self.type == "orthographic":
                if 'xmag' in self.json[self.type].keys():
                    self.xmag = self.json[self.type]['xmag']
                if 'ymag' in self.json[self.type].keys():
                    self.ymag = self.json[self.type]['ymag']
