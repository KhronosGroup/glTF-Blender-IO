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
from .gltf2_io_buffer import *

class BufferView():
    def __init__(self, index, json, gltf):
        self.index = index
        self.json  = json  # bufferView json
        self.gltf = gltf # Reference to global glTF instance

        # glTF2.0 required properties
        self.buffer_ = None #TODO to be renamed, already an attribute with this name
        self.byteLength = None

        # glTF2.0 not required properties, with default values
        self.byteOffset = 0

        # glTF2.0 not required properties
        self.byteStride = None
        self.target = None
        self.name = None
        self.extensions = {}
        self.extras = {}


    def read(self):
        if not 'buffer' in self.json.keys():
            return

        if self.json['buffer'] not in self.gltf.buffers:
            self.gltf.buffers[self.json['buffer']] = Buffer(self.json['buffer'], self.gltf.json['buffers'][self.json['buffer']], self.gltf)
            self.gltf.buffers[self.json['buffer']].read()
        self.buffer = self.gltf.buffers[self.json['buffer']]

    def read_data(self, fmt, stride_, count, accessor_offset):
        data = []

        if 'byteOffset' in self.json.keys():
            bufferview_offset = self.json['byteOffset'] #TODO use self.byteOffset
        else:
            bufferview_offset = 0 #TODO use self.byteOffset

        length = self.json['byteLength']

        if 'byteStride' in self.json.keys(): #TODO use self.byteStride
            stride = self.json['byteStride']
        else:
            stride = stride_

        slice = self.buffer.data[bufferview_offset:bufferview_offset + length]


        offset = accessor_offset
        while len(data) < count:
            element = struct.unpack_from(fmt, slice , offset)
            data.append(element)
            offset += stride

        return data

    def read_binary_data(self):
        if 'byteOffset' in self.json.keys():
            bufferview_offset = self.json['byteOffset']
        else:
            bufferview_offset = 0

        length = self.json['byteLength']

        return self.buffer.data[bufferview_offset:bufferview_offset + length]
