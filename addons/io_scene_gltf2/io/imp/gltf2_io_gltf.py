# Copyright 2018-2019 The glTF-Blender-IO authors.
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

from ..com.gltf2_io import gltf_from_dict
from ..com.gltf2_io_debug import Log
import logging
import json
import struct
import base64
from os.path import dirname, join, isfile, basename
from urllib.parse import unquote


class glTFImporter():
    """glTF Importer class."""

    def __init__(self, filename, import_settings):
        """initialization."""
        self.filename = filename
        self.import_settings = import_settings
        self.glb_buffer = None
        self.buffers = {}
        self.accessor_cache = {}

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
            'KHR_materials_pbrSpecularGlossiness',
            'KHR_lights_punctual',
            'KHR_materials_unlit',
            'KHR_texture_transform'
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
            return False, "GLB version %d unsupported" % self.version

        if self.file_size != len(self.content):
            return False, "Bad GLB: file size doesn't match"

        offset = 12  # header size = 12

        # JSON chunk is first
        type_, len_, json_bytes, offset = self.load_chunk(offset)
        if type_ != b"JSON":
            return False, "Bad GLB: first chunk not JSON"
        if len_ != len(json_bytes):
            return False, "Bad GLB: length of json chunk doesn't match"
        try:
            json_str = str(json_bytes, encoding='utf-8')
            json_ = json.loads(json_str, parse_constant=glTFImporter.bad_json_value)
            self.data = gltf_from_dict(json_)
        except ValueError as e:
            return False, e.args[0]

        # BIN chunk is second (if it exists)
        if offset < len(self.content):
            type_, len_, data, offset = self.load_chunk(offset)
            if type_ == b"BIN\0":
                if len_ != len(data):
                    return False, "Bad GLB: length of BIN chunk doesn't match"
                self.glb_buffer = data

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
            self.content = memoryview(f.read())

        self.is_glb_format = self.content[:4] == b'glTF'

        # glTF file
        if not self.is_glb_format:
            content = str(self.content, encoding='utf-8')
            self.content = None
            try:
                self.data = gltf_from_dict(json.loads(content, parse_constant=glTFImporter.bad_json_value))
                return True, None
            except ValueError as e:
                return False, e.args[0]

        # glb file
        else:
            # Parsing glb file
            success, txt = self.load_glb()
            self.content = None
            return success, txt

    def load_buffer(self, buffer_idx):
        """Load buffer."""
        buffer = self.data.buffers[buffer_idx]

        if buffer.uri:
            data, _file_name = self.load_uri(buffer.uri)
            if data is not None:
                self.buffers[buffer_idx] = data

        else:
            # GLB-stored buffer
            if buffer_idx == 0 and self.glb_buffer is not None:
                self.buffers[buffer_idx] = self.glb_buffer

    def load_uri(self, uri):
        """Loads a URI.
        Returns the data and the filename of the resource, if there is one.
        """
        sep = ';base64,'
        if uri.startswith('data:'):
            idx = uri.find(sep)
            if idx != -1:
                data = uri[idx + len(sep):]
                return memoryview(base64.b64decode(data)), None

        path = join(dirname(self.filename), unquote(uri))
        try:
            with open(path, 'rb') as f_:
                return memoryview(f_.read()), basename(path)
        except Exception:
            self.log.error("Couldn't read file: " + path)
            return None, None
