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
from .gltf2_io_sparse import *


class Accessor():
    def __init__(self, index, json, gltf):
        self.json  = json   # Accessor json
        self.gltf =  gltf # Reference to global glTF instance

        # glTF2.0 required properties
        self.componentType = None
        self.count = None
        self.type = None

        # glTF2.0 not required properties, with default values
        self.byteOffset = 0
        self.normalized = False

        # glTF2.0 not required properties
        self.bufferView_ = None #TODO must be renamed, already an attribute with this name in my code
        self.max = None
        self.min = None
        self.sparse = None
        self.name = ""
        self.extensions = {}
        self.extras = {}

    #SPLIT_TODO: to be removed
    # already done for primitives
    #SPLIT_TODO: animation_sampler (input & output)
    #SPLIT_TODO: skin
    def read(self):
        if not 'bufferView' in self.json:
            return # TODO initialize with 0 when not present!

        if 'normalized' in self.json.keys():
            self.normalized = self.json['normalized']

        if 'name' in self.json.keys():
            self.name = self.json['name']

        if self.json['bufferView'] not in self.gltf.bufferViews.keys():
            self.gltf.bufferViews[self.json['bufferView']] = BufferView(self.json['bufferView'], self.gltf.json['bufferViews'][self.json['bufferView']], self.gltf)
            self.gltf.bufferViews[self.json['bufferView']].read()

        self.bufferView = self.gltf.bufferViews[self.json['bufferView']]

        fmt_char = self.gltf.fmt_char_dict[self.json['componentType']]
        component_size = struct.calcsize(fmt_char)

        component_nb = self.gltf.component_nb_dict[self.json['type']]
        fmt = '<' + (fmt_char * component_nb)

        stride = struct.calcsize(fmt)

        # TODO data alignment stuff

        if 'byteOffset' in self.json.keys():
            offset = self.json['byteOffset'] #TODO use self.byteOffset
        else:
            offset = 0 #TODO use self.byteOffset

        if 'sparse' in self.json.keys():
            self.sparse = Sparse(self.json['componentType'], self.json['type'], self.json['sparse'], self.gltf)
            self.sparse.read()
            self.data = self.bufferView.read_data(fmt, stride, self.json['count'], offset)
            self.apply_sparse()
            return self.data

        else:
            self.data = self.bufferView.read_data(fmt, stride, self.json['count'], offset)
            return self.data

    #SPLIT_TODO: to be removed when .read() is removed
    def apply_sparse(self):
        cpt_idx = 0
        for idx in self.sparse.indices:
            self.data[idx[0]] = self.sparse.data[cpt_idx]
            cpt_idx += 1
