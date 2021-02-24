# Copyright 2018-2021 The glTF-Blender-IO authors.
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

#
# Imports
#

import json
import struct

#
# Globals
#

#
# Functions
#
from collections import OrderedDict


def save_gltf(gltf, export_settings, encoder, glb_buffer):
    indent = None
    separators = (',', ':')

    if export_settings['gltf_format'] != 'GLB':
        indent = 4
        # The comma is typically followed by a newline, so no trailing whitespace is needed on it.
        separators = (',', ' : ')

    sort_order = [
        "asset",
        "extensionsUsed",
        "extensionsRequired",
        "extensions",
        "extras",
        "scene",
        "scenes",
        "nodes",
        "cameras",
        "animations",
        "materials",
        "meshes",
        "textures",
        "images",
        "skins",
        "accessors",
        "bufferViews",
        "samplers",
        "buffers"
    ]
    gltf_ordered = OrderedDict(sorted(gltf.items(), key=lambda item: sort_order.index(item[0])))
    gltf_encoded = json.dumps(gltf_ordered, indent=indent, separators=separators, cls=encoder, allow_nan=False)

    #

    if export_settings['gltf_format'] != 'GLB':
        file = open(export_settings['gltf_filepath'], "w", encoding="utf8", newline="\n")
        file.write(gltf_encoded)
        file.write("\n")
        file.close()

        binary = export_settings['gltf_binary']
        if len(binary) > 0 and not export_settings['gltf_embed_buffers']:
            file = open(export_settings['gltf_filedirectory'] + export_settings['gltf_binaryfilename'], "wb")
            file.write(binary)
            file.close()

    else:
        file = open(export_settings['gltf_filepath'], "wb")

        gltf_data = gltf_encoded.encode()
        binary = glb_buffer

        length_gltf = len(gltf_data)
        spaces_gltf = (4 - (length_gltf & 3)) & 3
        length_gltf += spaces_gltf

        length_bin = len(binary)
        zeros_bin = (4 - (length_bin & 3)) & 3
        length_bin += zeros_bin

        length = 12 + 8 + length_gltf
        if length_bin > 0:
            length += 8 + length_bin

        # Header (Version 2)
        file.write('glTF'.encode())
        file.write(struct.pack("I", 2))
        file.write(struct.pack("I", length))

        # Chunk 0 (JSON)
        file.write(struct.pack("I", length_gltf))
        file.write('JSON'.encode())
        file.write(gltf_data)
        file.write(b' ' * spaces_gltf)

        # Chunk 1 (BIN)
        if length_bin > 0:
            file.write(struct.pack("I", length_bin))
            file.write('BIN\0'.encode())
            file.write(binary)
            file.write(b'\0' * zeros_bin)

        file.close()

    return True
