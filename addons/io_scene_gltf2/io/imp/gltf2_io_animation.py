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

from ..com.gltf2_io_animation import *

class AnimationImporter():

    @staticmethod
    def read(pyanimation):
        if not 'channels' in pyanimation.json.keys():
            return

        channel_idx = 0
        for channel in pyanimation.json['channels']:
            chan = PyAnimChannel(channel_idx, pyanimation.json['channels'][channel_idx], pyanimation, pyanimation.gltf)
            chan.read()
            pyanimation.channels.append(chan)
            channel_idx += 1

        AnimationImporter.dispatch_to_nodes(pyanimation)

        if 'name' in pyanimation.json.keys():
            pyanimation.name = pyanimation.json['name']

    @staticmethod
    def set_anim(pyanimation, channel):
        if channel.anim.index not in pyanimation.anims.keys():
            pyanimation.anims[channel.anim.index] = []
        pyanimation.anims[channel.anim.index].append(channel)

    @staticmethod
    def dispatch_to_nodes(pyanimation):
        for channel in pyanimation.channels:
            node = pyanimation.gltf.scene.nodes[channel.node]
            if node:
                AnimationImporter.set_anim(node.animation, channel)
            else:
                pyanimation.gltf.log.error("ERROR, node not found")

    @staticmethod
    def importer(idx, json, gltf):
        animation = PyAnimation(idx, json, gltf)
        AnimationImporter.read(animation)
        return animation
