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

from ..com.gltf2_io_buffer import *

class BufferImporter():

    @staticmethod
    def read(pybuffer):

        if pybuffer.gltf.is_glb_format:
            return

        pybuffer.length = pybuffer.json['byteLength']

        if 'uri' in pybuffer.json.keys():
            sep = ';base64,'
            if pybuffer.json['uri'][:5] == 'data:':
                idx = pybuffer.json['uri'].find(sep)
                if idx != -1:
                    data = pybuffer.json['uri'][idx+len(sep):]
                    pybuffer.data = base64.b64decode(data)
                    return


            with open(join(dirname(pybuffer.gltf.filename), pybuffer.json['uri']), 'rb') as f_:
                pybuffer.data = f_.read()


    @staticmethod
    def importer(idx, json, gltf):
        buffer = Buffer(idx, json, gltf)
        BufferImporter.read(buffer)
        return buffer
