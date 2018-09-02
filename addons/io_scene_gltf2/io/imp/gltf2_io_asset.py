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

from ..com.gltf2_io_asset import *
from ..com.gltf2_io_constants import *

class AssetImporter():

    @staticmethod
    def read(pyasset):
        if 'version' in pyasset.json.keys():
            pyasset.version = pyasset.json['version']

        if 'copyright' in pyasset.json.keys():
            pyasset.copyright = pyasset.json['copyright']

        if 'generator' in pyasset.json.keys():
            pyasset.generator = pyasset.json['generator']

        if 'minVersion' in pyasset.json.keys():
            pyasset.minVersion = pyasset.json['minVersion']

    @staticmethod
    def check_version(pyasset):
        if pyasset.version is None:
            return False, "Version is mandatory"

        if pyasset.version != GLTF_VERSION:
            return False, "glTF version is not supported"

        return True, None

    @staticmethod
    def importer(json, gltf):
        asset = PyAsset(json, gltf)
        AssetImporter.read(asset)
        return asset
