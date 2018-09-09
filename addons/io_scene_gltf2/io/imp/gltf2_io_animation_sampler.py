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

from ..com.gltf2_io_animation_channel import *
from .gltf2_io_accessor_old import *

class SamplerImporter():

    @staticmethod
    def read(pysampler):
        pysampler.interpolation = pysampler.json['interpolation']
        if pysampler.json['input'] not in pysampler.gltf.accessors.keys():
            pysampler.gltf.accessors[pysampler.json['input']], input_data = AccessorImporter.importer(pysampler.json['input'], pysampler.gltf.json['accessors'][pysampler.json['input']], pysampler.gltf)
            pysampler.input = pysampler.gltf.accessors[pysampler.json['input']]
        else:
            pysampler.input  = pysampler.gltf.accessors[pysampler.json['input']]
            input_data = pysampler.input.data

        if pysampler.json['output'] not in pysampler.gltf.accessors.keys():
            pysampler.gltf.accessors[pysampler.json['output']], output_data = AccessorImporter.importer(pysampler.json['output'], pysampler.gltf.json['accessors'][pysampler.json['output']], pysampler.gltf)
            pysampler.output = pysampler.gltf.accessors[pysampler.json['output']]
        else:
            pysampler.output = pysampler.gltf.accessors[pysampler.json['output']]
            output_data = pysampler.output.data

        anim_data = []

        if pysampler.channels == 0:
            cpt_idx = 0
            for i in input_data:
                anim_data.append(tuple([input_data[cpt_idx][0], output_data[cpt_idx]]))
                cpt_idx += 1

            return anim_data

        else:

            for chan in range(0, pysampler.channels):
                anim_data_chan = []
                cpt_idx = 0
                for i in input_data:
                    anim_data_chan.append(tuple([input_data[cpt_idx][0], output_data[cpt_idx*pysampler.channels+chan][0]]))
                    cpt_idx += 1
                anim_data.append(anim_data_chan)

            return anim_data

    @staticmethod
    def importer(idx, json, gltf, channels=0):
        sampler = PySampler(idx, json, gltf, channels)
        data = SamplerImporter.read(sampler)
        return sampler, data
