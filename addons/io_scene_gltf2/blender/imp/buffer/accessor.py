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
from .bufferview import *
from .sparse import *


class Accessor():
    def __init__(self, index, json, gltf):
        self.json  = json   # Accessor json
        self.gltf =  gltf # Reference to global glTF instance
        self.name = None

    def read(self):
        if not 'bufferView' in self.json:
            return

        if 'name' in self.json.keys():
            self.name = self.json['name']

        self.bufferView = BufferView(self.json['bufferView'], self.gltf.json['bufferViews'][self.json['bufferView']], self.gltf)
        self.bufferView.read()
        self.bufferView.debug_missing()

        fmt_char = self.gltf.fmt_char_dict[self.json['componentType']]
        component_size = struct.calcsize(fmt_char)

        component_nb = self.gltf.component_nb_dict[self.json['type']]
        fmt = '<' + (fmt_char * component_nb)

        stride = struct.calcsize(fmt)

        # TODO data alignment stuff

        if 'byteOffset' in self.json.keys():
            offset = self.json['byteOffset']
        else:
            offset = 0

        if 'sparse' in self.json.keys():
            self.sparse = Sparse(self.json['componentType'], self.json['type'], self.json['sparse'], self.gltf)
            self.sparse.read()
            self.sparse.debug_missing()
            self.data = self.bufferView.read_data(fmt, stride, self.json['count'], offset)
            self.apply_sparse()
            return self.data

        else:
            return self.bufferView.read_data(fmt, stride, self.json['count'], offset)

    def apply_sparse(self):
        cpt_idx = 0
        for idx in self.sparse.indices:
            self.data[idx[0]] = self.sparse.data[cpt_idx]
            cpt_idx += 1

    def debug_missing(self):
        keys = [
                'componentType',
                'count',
                'type',
                'bufferView',
                'byteOffset',
                'min', #TODO :  add some checks ?
                'max', #TODO :  add some checks ?
                'name',
                'sparse'
                ]

        for key in self.json.keys():
            if key not in keys:
                self.gltf.log.debug("ACCESSOR MISSING " + key)
