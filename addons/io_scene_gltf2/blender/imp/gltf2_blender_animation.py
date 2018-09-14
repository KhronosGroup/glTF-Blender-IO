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

from .gltf2_blender_animation_bone import *
from .gltf2_blender_animation_node import *

class BlenderAnimation():

    @staticmethod
    def anim(gltf, anim_idx, node_idx):
        if gltf.data.nodes[node_idx].is_joint:
            BlenderBoneAnim.anim(gltf, anim_idx, node_idx)
        else:
            BlenderNodeAnim.anim(gltf, anim_idx, node_idx)

        if gltf.data.nodes[node_idx].children:
            for child in gltf.data.nodes[node_idx].children:
                BlenderAnimation.anim(gltf, anim_idx, child)
