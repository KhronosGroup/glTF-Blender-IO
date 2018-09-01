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

from .gltf2_io_image import *

class PyTexture():
    def __init__(self, index, json, gltf):
        self.index = index
        self.json = json # texture json
        self.gltf = gltf # Reference to global glTF instance

        # glTF2.0 required properties
        # No required properties

        # glTF2.0 not requirement properties
        self.sampler = None #TODO Not implemented yet
        self.source_ = None #TODO to be renamed, already an attribute with this name
        self.name = ""
        self.extension = {}
        self.extras = {}

    def read(self):
        if 'source' in self.json.keys():

            if self.json['source'] not in self.gltf.images.keys():
                image = PyImage(self.json['source'], self.gltf.json['images'][self.json['source']], self.gltf)
                self.gltf.images[self.json['source']] = image

            self.image = self.gltf.images[self.json['source']]
            self.image.read()
