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

from ..com.gltf2_io_bufferview import *

class BufferViewImporter():

    @staticmethod
    def read(pybufferview):
        if not 'buffer' in pybufferview.json.keys():
            return

        if pybufferview.json['buffer'] not in pybufferview.gltf.buffers:
            pybufferview.gltf.buffers[pybufferview.json['buffer']] = Buffer(pybufferview.json['buffer'], pybufferview.gltf.json['buffers'][pybufferview.json['buffer']], pybufferview.gltf)
            pybufferview.gltf.buffers[pybufferview.json['buffer']].read()
        pybufferview.buffer = pybufferview.gltf.buffers[pybufferview.json['buffer']]

    @staticmethod
    def read_data(pybufferview, fmt, stride_, count, accessor_offset):
        data = []

        if 'byteOffset' in pybufferview.json.keys():
            bufferview_offset = pybufferview.json['byteOffset'] #TODO use pybufferview.byteOffset
        else:
            bufferview_offset = 0 #TODO use pybufferview.byteOffset

        length = pybufferview.json['byteLength']

        if 'byteStride' in pybufferview.json.keys(): #TODO use pybufferview.byteStride
            stride = pybufferview.json['byteStride']
        else:
            stride = stride_

        slice = pybufferview.buffer.data[bufferview_offset:bufferview_offset + length]


        offset = accessor_offset
        while len(data) < count:
            element = struct.unpack_from(fmt, slice , offset)
            data.append(element)
            offset += stride

        return data

    @staticmethod
    def read_binary_data(pybufferview):
        if 'byteOffset' in pybufferview.json.keys():
            bufferview_offset = pybufferview.json['byteOffset']
        else:
            bufferview_offset = 0

        length = pybufferview.json['byteLength']

        return pybufferview.buffer.data[bufferview_offset:bufferview_offset + length]


    @staticmethod
    def importer(idx, json, gltf):
        bufferView = BufferView(idx, json, gltf)
        BufferViewImporter.read(bufferView)
        return bufferView
