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
#from .gltf2_blender_animation_node import *

class BlenderAnimationData():

    @staticmethod
    def set_interpolation(interpolation, kf):
        pass #TODO_SPLIT
        # if interpolation == "LINEAR":
        #     kf.interpolation = 'LINEAR'
        # elif interpolation == "STEP":
        #     kf.interpolation = 'CONSTANT'
        # elif interpolation == "CATMULLROMSPLINE":
        #     kf.interpolation = 'BEZIER' #TODO
        # elif interpolation == "CUBICSPLINE":
        #     kf.interpolation = 'BEZIER' #TODO
        # else:
        #     kf.interpolation = 'BEZIER'
