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

from .gltf2_io_constants import *

class PyAsset():
    def __init__(self, json, gltf):
        self.json  = json   # Asset json
        self.gltf  = gltf   # Reference to global glTF instance

        # glTF2.0 required properties
        self.version = None

        # glTF2.0 not required properties
        self.copyright = None
        self.generator = None
        self.minVersion = None
        self.extensions = {}
        self.extras = {}


    def read(self):
        if 'version' in self.json.keys():
            self.version = self.json['version']

        if 'copyright' in self.json.keys():
            self.copyright = self.json['copyright']

        if 'generator' in self.json.keys():
            self.generator = self.json['generator']

        if 'minVersion' in self.json.keys():
            self.minVersion = self.json['minVersion']

    def check_version(self):
        if self.version is None:
            return False, "Version is mandatory"

        if self.version != GLTF_VERSION:
            return False, "glTF version is not supported"

        return True, None
