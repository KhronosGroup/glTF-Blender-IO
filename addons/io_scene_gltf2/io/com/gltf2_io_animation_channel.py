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

from .gltf2_io_animation_sampler import *

class PyAnimChannel():
    def __init__(self, index, json, anim, gltf):
        self.index = index
        self.json  = json # Anim Channel json
        self.anim  = anim # Reference to animation
        self.gltf  = gltf # Reference to global glTF instance

    def read(self):
        if not 'target' in self.json.keys():
            return

        self.node = self.json['target']['node']
        self.path = self.json['target']['path']

        if self.path != "weights":
            channels = 0
        else:
            channels = 0
            for prim in self.gltf.scene.nodes[self.node].mesh.primitives:
                if len(prim.targets) > channels:
                    channels = len(prim.targets)
        self.sampler = PySampler(self.json['sampler'], self.anim.json['samplers'][self.json['sampler']], self.gltf, channels)
        self.data = self.sampler.read()
        self.interpolation = self.sampler.interpolation
