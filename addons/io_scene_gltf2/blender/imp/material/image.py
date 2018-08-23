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

import bpy
import os
import base64
import tempfile
from os.path import dirname, join, isfile, basename
from ..buffer import *

class Image():
    def __init__(self, index, json, gltf):
        self.index = index
        self.json  = json # Image json
        self.gltf  = gltf # Reference to global glTF instance

        self.blender_image_name = None

    def read(self):


        self.image_name = "Image_" + str(self.index)

        if 'uri' in self.json.keys():
            sep = ';base64,'
            if self.json['uri'][:5] == 'data:':
                idx = self.json['uri'].find(sep)
                if idx != -1:
                    data = self.json['uri'][idx+len(sep):]
                    self.data = base64.b64decode(data)
                    return

            if isfile(join(dirname(self.gltf.filename), self.json['uri'])):
                with open(join(dirname(self.gltf.filename), self.json['uri']), 'rb') as f_:
                    self.data = f_.read()
                    self.image_name = basename(join(dirname(self.gltf.filename), self.json['uri']))
                    return
            else:
                self.gltf.log.error("Missing file (index " + str(self.index) + "): " + self.json['uri'])
                return

        if 'bufferView' not in self.json.keys():
            return

        if self.json['bufferView'] not in self.gltf.bufferViews.keys():
            self.gltf.bufferViews[self.json['bufferView']] = BufferView(self.json['bufferView'], self.gltf.json['bufferViews'][self.json['bufferView']], self.gltf)
            self.gltf.bufferViews[self.json['bufferView']].read()

        self.bufferView = self.gltf.bufferViews[self.json['bufferView']]

        self.bufferView.debug_missing()

        self.data = self.bufferView.read_binary_data()

        return

    def blender_create(self):
        # Create a temp image, pack, and delete image
        tmp_image = tempfile.NamedTemporaryFile(delete=False)
        tmp_image.write(self.data)
        tmp_image.close()

        blender_image = bpy.data.images.load(tmp_image.name)
        blender_image.pack()
        blender_image.name = self.image_name
        self.blender_image_name = blender_image.name
        os.remove(tmp_image.name)


    def debug_missing(self):
        if self.index is None:
            return
        keys = [
                'uri'
                ]

        for key in self.json.keys():
            if key not in keys:
                self.gltf.log.debug("MATERIAL MISSING " + key)
