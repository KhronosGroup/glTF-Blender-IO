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

from .gltf2_io_accessor import *

class PySampler():
    def __init__(self, index, json, gltf, channels=0):
        self.index = index
        self.json  = json # Sampler json
        self.gltf  = gltf # Reference to global glTF instance

        # glTF2.0 required properties
        self.input_ = None #TODO to be renamed, already an attribute with this name
        self.output_ = None #TODO to be renamed, already an attribute with this name

        # glTF2.0 not required properties, with default values
        self.interpolation = 'LINEAR'

        # glTF2.0 not required properties
        self.extensions = {}
        self.extras = {}

        self.channels = channels # for shape keys weights
