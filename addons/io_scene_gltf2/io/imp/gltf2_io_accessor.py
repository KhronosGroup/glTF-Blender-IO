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
 """

from ..com.gltf2_io_accessor import *
from .gltf2_io_bufferView import *
from .gltf2_io_sparse import *

class AccessorImporter():

    @staticmethod
    def read(pyaccessor):
        if not 'bufferView' in pyaccessor.json:
            return # TODO initialize with 0 when not present!

        if 'normalized' in pyaccessor.json.keys():
            pyaccessor.normalized = pyaccessor.json['normalized']

        if 'name' in pyaccessor.json.keys():
            pyaccessor.name = pyaccessor.json['name']

        if pyaccessor.json['bufferView'] not in pyaccessor.gltf.bufferViews.keys():
            pyaccessor.gltf.bufferViews[pyaccessor.json['bufferView']] = BufferViewImporter.importer(pyaccessor.json['bufferView'], pyaccessor.gltf.json['bufferViews'][pyaccessor.json['bufferView']], pyaccessor.gltf)

        pyaccessor.bufferView = pyaccessor.gltf.bufferViews[pyaccessor.json['bufferView']]

        fmt_char = pyaccessor.gltf.fmt_char_dict[pyaccessor.json['componentType']]
        component_size = struct.calcsize(fmt_char)

        component_nb = pyaccessor.gltf.component_nb_dict[pyaccessor.json['type']]
        fmt = '<' + (fmt_char * component_nb)

        stride = struct.calcsize(fmt)

        # TODO data alignment stuff

        if 'byteOffset' in pyaccessor.json.keys():
            offset = pyaccessor.json['byteOffset'] #TODO use pyaccessor.byteOffset
        else:
            offset = 0 #TODO use pyaccessor.byteOffset

        if 'sparse' in pyaccessor.json.keys():
            pyaccessor.sparse = SparseImporter.importer(pyaccessor.json['componentType'], pyaccessor.json['type'], pyaccessor.json['sparse'], pyaccessor.gltf)
            pyaccessor.data = BufferViewImporter.read_data(pyaccessor.bufferView, fmt, stride, pyaccessor.json['count'], offset)
            AccessorImporter.apply_sparse(pyaccessor)
            return pyaccessor.data

        else:
            pyaccessor.data = BufferViewImporter.read_data(pyaccessor.bufferView, fmt, stride, pyaccessor.json['count'], offset)
            return pyaccessor.data

    @staticmethod
    def apply_sparse(pyaccessor):
        cpt_idx = 0
        for idx in pyaccessor.sparse.indices:
            pyaccessor.data[idx[0]] = pyaccessor.sparse.data[cpt_idx]
            cpt_idx += 1

    @staticmethod
    def importer(idx, json, gltf):
        accessor = Accessor(idx, json, gltf)
        data = AccessorImporter.read(accessor)
        return accessor, data
