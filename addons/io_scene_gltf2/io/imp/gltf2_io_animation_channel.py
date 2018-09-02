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
from .gltf2_io_animation_sampler import *

class AnimChannelImporter():

    @staticmethod
    def read(pychannel):
        if not 'target' in pychannel.json.keys():
            return

        pychannel.node = pychannel.json['target']['node']
        pychannel.path = pychannel.json['target']['path']

        if pychannel.path != "weights":
            channels = 0
        else:
            channels = 0
            for prim in pychannel.gltf.scene.nodes[pychannel.node].mesh.primitives:
                if len(prim.targets) > channels:
                    channels = len(prim.targets)
        pychannel.sampler, pychannel.data = SamplerImporter.importer(pychannel.json['sampler'], pychannel.anim.json['samplers'][pychannel.json['sampler']], pychannel.gltf, channels)
        pychannel.interpolation = pychannel.sampler.interpolation

    @staticmethod
    def importer(idx, json, anim, gltf):
        channel = PyAnimChannel(idx, json, anim, gltf)
        AnimChannelImporter.read(channel)
        return channel
