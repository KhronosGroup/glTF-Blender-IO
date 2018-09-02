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

class PyKHR_materials_pbrSpecularGlossiness():

    SIMPLE  = 1
    TEXTURE = 2
    TEXTURE_FACTOR = 3

    def __init__(self, json, gltf):
        self.json = json # KHR_materials_pbrSpecularGlossiness json
        self.gltf = gltf # Reference to global glTF instance

        # KHR_materials_pbrSpecularGlossiness required properties
        # No required properties

        # KHR_materials_pbrSpecularGlossiness not required properties, with default values
        self.diffuseFactor    = [1.0,1.0,1.0,1.0]
        self.specularFactor   = [1.0,1.0,1.0]
        self.glossinessFactor = 1.0

        # KHR_materials_pbrSpecularGlossiness not required properties
        self.diffuseTexture_ = None             #TODO rename, already attribute with this name
        self.specularGlossinessFactor_ = None   #TODO rename, already attribute with this name

        self.diffuse_type   = self.SIMPLE
        self.specgloss_type = self.SIMPLE
        self.vertex_color   = False
