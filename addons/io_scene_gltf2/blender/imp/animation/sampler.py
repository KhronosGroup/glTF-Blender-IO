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

from ..buffer import *

class Sampler():
    def __init__(self, index, json, gltf, channels=0):
        self.index = index
        self.json  = json # Sampler json
        self.gltf  = gltf # Reference to global glTF instance

        self.channels = channels # for shape keys weights

    def read(self):
        self.interpolation = self.json['interpolation']
        self.input  = Accessor(self.json['input'], self.gltf.json['accessors'][self.json['input']], self.gltf)
        self.output = Accessor(self.json['output'], self.gltf.json['accessors'][self.json['output']], self.gltf)
        input_data  = self.input.read()
        output_data = self.output.read()

        self.input.debug_missing()
        self.output.debug_missing()

        anim_data = []

        if self.channels == 0:
            cpt_idx = 0
            for i in input_data:
                anim_data.append(tuple([input_data[cpt_idx][0], output_data[cpt_idx]]))
                cpt_idx += 1

            return anim_data

        else:

            for chan in range(0, self.channels):
                anim_data_chan = []
                cpt_idx = 0
                for i in input_data:
                    anim_data_chan.append(tuple([input_data[cpt_idx][0], output_data[cpt_idx*self.channels+chan][0]]))
                    cpt_idx += 1
                anim_data.append(anim_data_chan)

            return anim_data

    def debug_missing(self):
        keys = [
                'input',
                'output',
                'interpolation'
                ]

        for key in self.json.keys():
            if key not in keys:
                self.gltf.log.debug("SAMPLER CHANNEL MISSING " + key)
