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

class Sparse():
    def __init__(self, component_type, type, json, gltf):
        self.json = json # Sparse json
        self.gltf = gltf # Reference to global glTF instance


        # glTF2.0 required properties
        self.count = None
        self.indices = None
        self.values = None

        # glTF2.0 not required properties
        self.extensions = {}
        self.extras = {}

        # Sparse specifics
        self.component_type = component_type
        self.type = type


    def read(self):
        self.count = self.json['count']

        if 'indices' in self.json.keys():
            self.indices_buffer = BufferView(self.json['indices']['bufferView'], self.gltf.json['bufferViews'][self.json['indices']['bufferView']], self.gltf)
            self.indices_buffer.read()

            #TODO factorisation with accessor code ?
            fmt_char = self.gltf.fmt_char_dict[self.json['indices']['componentType']]
            component_size = struct.calcsize(fmt_char)

            component_nb = self.gltf.component_nb_dict['SCALAR']
            fmt = '<' + (fmt_char * component_nb)

            stride = struct.calcsize(fmt)

            # TODO data alignment stuff

            if 'byteOffset' in self.json['indices'].keys():
                offset = self.json['indices']['byteOffset']
            else:
                offset = 0

            self.indices = self.indices_buffer.read_data(fmt, stride, self.count, offset)


        if 'values' in self.json.keys():
            if self.json['values']['bufferView'] not in self.gltf.bufferViews.keys():
                self.gltf.bufferViews[self.json['values']['bufferView']] = BufferView(self.json['values']['bufferView'], self.gltf.json['bufferViews'][self.json['values']['bufferView']], self.gltf)
                self.gltf.bufferViews[self.json['values']['bufferView']].read()

            self.bufferView = self.gltf.bufferViews[self.json['values']['bufferView']]

            #TODO factorisation with accessor code ?
            fmt_char = self.gltf.fmt_char_dict[self.component_type]
            component_size = struct.calcsize(fmt_char)

            component_nb = self.gltf.component_nb_dict[self.type]
            fmt = '<' + (fmt_char * component_nb)

            stride = struct.calcsize(fmt)

            # TODO data alignment stuff

            if 'byteOffset' in self.json['values'].keys():
                offset = self.json['values']['byteOffset']
            else:
                offset = 0

            self.data = self.bufferView.read_data(fmt, stride, self.count, offset)
