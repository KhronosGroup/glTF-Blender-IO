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

from .gltf2_io_texture import *

class PyPbr():

    #TODO: move to blender file?
    SIMPLE  = 1
    TEXTURE = 2
    TEXTURE_FACTOR = 3

    def __init__(self, json, gltf):
        self.json = json # pbrMetallicRoughness json
        self.gltf = gltf # Reference to global glTF instance

        # glTF2.0 required properties
        # No required properties

        # glTF2.0 not required properties, with default values
        self.baseColorFactor = [1,1,1,1]
        self.metallicFactor = 1
        self.roughnessFactor = 1

        # glTF2.0 not required properties
        self.baseColorTexture = None
        self.metallicRoughnessTexture = None
        self.extensions = None
        self.extras = None

        # PyPbr specifics
        # TODO: move to Blender file?
        self.color_type = self.SIMPLE
        self.vertex_color = False
        self.metallic_type = self.SIMPLE
