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

from ..com.gltf2_io import *
from ..com.gltf2_io_debug import *
import logging
import json

class glTFImporter():

    def __init__(self, filename, loglevel=logging.ERROR):
        self.filename = filename

        log = Log(loglevel)
        self.log = log.logger
        self.log_handler = log.hdlr

    @staticmethod
    def bad_json_value(val):
        raise ValueError('Json contains some unauthorized values')

    def load_glb(self):
        #TODO_SPLIT
        # glb files will be done later
        return True, None

    def load_chunk(self, offset):
        chunk_header = struct.unpack_from('<I4s', self.content, offset)
        data_length  = chunk_header[0]
        data_type    = chunk_header[1]
        data         = self.content[offset + 8 : offset + 8 + data_length]

        return data_type, data, offset + 8 + data_length

    def read(self):
        # Check if file is gltf or glb
        with open(self.filename, 'rb') as f:
            self.content = f.read()

        self.is_glb_format = self.content[:4] == b'glTF'

        # glTF file
        if not self.is_glb_format:
            self.content = None
            with open(self.filename, 'r') as f:
                content = f.read()
                try:
                    self.data = gltf_from_dict(json.loads(content, parse_constant=glTFImporter.bad_json_value))
                    return True, None
                except ValueError as e:
                    return False, e.args[0]

        # glb file
        else:
            # Parsing glb file
            success, txt = self.load_glb()
            return success, txt
