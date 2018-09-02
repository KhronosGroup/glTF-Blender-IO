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

from ..com.gltf2_io_sparse import *
from .gltf2_io_bufferview import *

class SparseImporter():

    @staticmethod
    def read(pysparse):
        pysparse.count = pysparse.json['count']

        if 'indices' in pysparse.json.keys():
            pysparse.indices_buffer = BufferViewImporter.importer(pysparse.json['indices']['bufferView'], pysparse.gltf.json['bufferViews'][pysparse.json['indices']['bufferView']], pysparse.gltf)

            #TODO factorisation with accessor code ?
            fmt_char = pysparse.gltf.fmt_char_dict[pysparse.json['indices']['componentType']]
            component_size = struct.calcsize(fmt_char)

            component_nb = pysparse.gltf.component_nb_dict['SCALAR']
            fmt = '<' + (fmt_char * component_nb)

            stride = struct.calcsize(fmt)

            # TODO data alignment stuff

            if 'byteOffset' in pysparse.json['indices'].keys():
                offset = pysparse.json['indices']['byteOffset']
            else:
                offset = 0

            pysparse.indices = pysparse.indices_buffer.read_data(fmt, stride, pysparse.count, offset)


        if 'values' in pysparse.json.keys():
            if pysparse.json['values']['bufferView'] not in pysparse.gltf.bufferViews.keys():
                pysparse.gltf.bufferViews[pysparse.json['values']['bufferView']] = BufferViewImporter.importer(pysparse.json['values']['bufferView'], pysparse.gltf.json['bufferViews'][pysparse.json['values']['bufferView']], pysparse.gltf)

            pysparse.bufferView = pysparse.gltf.bufferViews[pysparse.json['values']['bufferView']]

            #TODO factorisation with accessor code ?
            fmt_char = pysparse.gltf.fmt_char_dict[pysparse.component_type]
            component_size = struct.calcsize(fmt_char)

            component_nb = pysparse.gltf.component_nb_dict[pysparse.type]
            fmt = '<' + (fmt_char * component_nb)

            stride = struct.calcsize(fmt)

            # TODO data alignment stuff

            if 'byteOffset' in pysparse.json['values'].keys():
                offset = pysparse.json['values']['byteOffset']
            else:
                offset = 0

            pysparse.data = pysparse.bufferView.read_data(fmt, stride, pysparse.count, offset)


    @staticmethod
    def importer(component_type, type, json, gltf):
        sparse = Sparse(component_type, type, json, gltf)
        SparseImporter.read(sparse)
        return sparse
