# Copyright 2018 The glTF-Blender-IO authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from ..com.gltf2_io import *
from ..com.gltf2_io_debug import *
import logging
import json
import struct
import base64
from os.path import dirname, join, getsize, isfile


class glTFImporter():
    """glTF Importer class."""

    def __init__(self, filename, import_settings):
        """initialization."""
        self.filename = filename
        self.import_settings = import_settings
        self.buffers = {}

        if 'loglevel' not in self.import_settings.keys():
            self.import_settings['loglevel'] = logging.ERROR

        log = Log(import_settings['loglevel'])
        self.log = log.logger
        self.log_handler = log.hdlr

        self.SIMPLE = 1
        self.TEXTURE = 2
        self.TEXTURE_FACTOR = 3

        # TODO: move to a com place?
        self.extensions_managed = [
            'KHR_materials_pbrSpecularGlossiness'
        ]

        # TODO : merge with io_constants
        self.fmt_char_dict = {}
        self.fmt_char_dict[5120] = 'b'  # Byte
        self.fmt_char_dict[5121] = 'B'  # Unsigned Byte
        self.fmt_char_dict[5122] = 'h'  # Short
        self.fmt_char_dict[5123] = 'H'  # Unsigned Short
        self.fmt_char_dict[5125] = 'I'  # Unsigned Int
        self.fmt_char_dict[5126] = 'f'  # Float

        self.component_nb_dict = {}
        self.component_nb_dict['SCALAR'] = 1
        self.component_nb_dict['VEC2'] = 2
        self.component_nb_dict['VEC3'] = 3
        self.component_nb_dict['VEC4'] = 4
        self.component_nb_dict['MAT2'] = 4
        self.component_nb_dict['MAT3'] = 9
        self.component_nb_dict['MAT4'] = 16

    @staticmethod
    def bad_json_value(val):
        """Bad Json value."""
        raise ValueError('Json contains some unauthorized values')

    def checks(self):
        """Some checks."""
        if self.data.asset.version != "2.0":
            return False, "glTF version must be 2"

        if self.data.extensions_required is not None:
            for extension in self.data.extensions_required:
                if extension not in self.data.extensions_used:
                    return False, "Extension required must be in Extension Used too"
                if extension not in self.extensions_managed:
                    return False, "Extension " + extension + " is not available on this addon version"

        if self.data.extensions_used is not None:
            for extension in self.data.extensions_used:
                if extension not in self.extensions_managed:
                    # Non blocking error #TODO log
                    pass

        return True, None

    def load_glb(self):
        """Load binary glb."""
        header = struct.unpack_from('<4sII', self.content)
        self.format = header[0]
        self.version = header[1]
        self.file_size = header[2]

        if self.format != b'glTF':
            return False, "This file is not a glTF/glb file"

        if self.version != 2:
            return False, "glTF version doesn't match to 2"

        if self.file_size != getsize(self.filename):
            return False, "File size doesn't match"

        offset = 12  # header size = 12

        # TODO check json type for chunk 0, and BIN type for next ones

        # json
        type, len_, str_json, offset = self.load_chunk(offset)
        if len_ != len(str_json):
            return False, "Length of json part doesn't match"
        try:
            json_ = json.loads(str_json.decode('utf-8'), parse_constant=glTFImporter.bad_json_value)
            self.data = gltf_from_dict(json_)
        except ValueError as e:
            return False, e.args[0]

        # binary data
        chunk_cpt = 0
        while offset < len(self.content):
            type, len_, data, offset = self.load_chunk(offset)
            if len_ != len(data):
                return False, "Length of bin buffer " + str(chunk_cpt) + " doesn't match"

            self.buffers[chunk_cpt] = data
            chunk_cpt += 1

        self.content = None
        return True, None

    def load_chunk(self, offset):
        """Load chunk."""
        chunk_header = struct.unpack_from('<I4s', self.content, offset)
        data_length = chunk_header[0]
        data_type = chunk_header[1]
        data = self.content[offset + 8: offset + 8 + data_length]

        return data_type, data_length, data, offset + 8 + data_length

    def read(self):
        """Read file."""
        # Check this is a file
        if not isfile(self.filename):
            return False, "Please select a file"

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

    def is_node_joint(self, node_idx):
        """Check if node is a joint."""
        if not self.data.skins:  # if no skin in gltf file
            return False, None

        for skin_idx, skin in enumerate(self.data.skins):
            if node_idx in skin.joints:
                return True, skin_idx

        return False, None

    def load_buffer(self, buffer_idx):
        """Load buffer."""
        buffer = self.data.buffers[buffer_idx]

        if buffer.uri:
            sep = ';base64,'
            if buffer.uri[:5] == 'data:':
                idx = buffer.uri.find(sep)
                if idx != -1:
                    data = buffer.uri[idx + len(sep):]
                    self.buffers[buffer_idx] = base64.b64decode(data)
                    return

            with open(join(dirname(self.filename), buffer.uri), 'rb') as f_:
                self.buffers[buffer_idx] = f_.read()
