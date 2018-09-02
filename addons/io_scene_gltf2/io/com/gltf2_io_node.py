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

from .gltf2_io_mesh import *
from .gltf2_io_camera import *
from .gltf2_io_animation import *

from .gltf2_io_trs import *

class PyNode():
    def __init__(self, index, json, gltf, scene):
        self.index = index
        self.json = json   # Node json
        self.gltf = gltf # Reference to global glTF instance
        self.scene = scene # Reference to scene


        # glTF2.0 required properties
        # No required !

        # glTF2.0 not required properties, with default values
        self.matrix      = [1.0,0.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0,0.0,1.0]
        self.rotation    = [0.0,0.0,0.0,1.0]
        self.scale       = [1.0,1.0,1.0]
        self.translation = [0.0,0.0,0.0]

        # glTF2.0 not required properties
        #TODO : note that all these properties are not managed yet
        self.camera = None
        self.children = []
        self.skin = None #TODO
        self.mesh = None
        self.weights = []
        self.name = ""
        self.extensions = {}
        self.extras = {}

        # PyNode specific

        self.animation = PyAnimationData(self, self.gltf)
        self.is_joint = False
        self.parent = None
        self.transform = [1.0,0.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0,0.0,1.0]
