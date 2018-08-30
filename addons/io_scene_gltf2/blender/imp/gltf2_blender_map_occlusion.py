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

import bpy
from .gltf2_blender_texture import *

class BlenderOcclusionMap():

    @staticmethod
    def create(pymap, mat_name):
        engine = bpy.context.scene.render.engine
        if engine == 'CYCLES':
            BlenderNormalMap.create_cycles(pymap, mat_name)
        else:
            pass #TODO for internal / Eevee in future 2.8

    def create(pymap, mat_name):
        engine = bpy.context.scene.render.engine
        if engine == 'CYCLES':
            BlenderOcclusionMap.create_cycles(pymap, mat_name)
        else:
            pass #TODO for internal / Eevee in future 2.8

    def create_cycles(pymap, mat_name):
        BlenderTexture.create(pymap.texture)

        # Pack texture, but doesn't use it for now. Occlusion is calculated from Cycles.
        bpy.data.images[pymap.texture.image.blender_image_name].use_fake_user = True
