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

import base64
from os.path import dirname, join

class Buffer():
    def __init__(self, index, json, gltf):
        self.index = index
        self.json  = json  # buffer json
        self.gltf = gltf # Reference to global glTF instance

    def read(self):

        if self.gltf.is_glb_format:
            return

        self.length = self.json['byteLength']

        if 'uri' in self.json.keys():
            sep = ';base64,'
            if self.json['uri'][:5] == 'data:':
                idx = self.json['uri'].find(sep)
                if idx != -1:
                    data = self.json['uri'][idx+len(sep):]
                    self.data = base64.b64decode(data)
                    return


            with open(join(dirname(self.gltf.filename), self.json['uri']), 'rb') as f_:
                self.data = f_.read()
