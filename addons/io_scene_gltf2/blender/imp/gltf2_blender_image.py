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
import os
import tempfile

class BlenderImage():

    @staticmethod
    def create(self):
        # Create a temp image, pack, and delete image
        tmp_image = tempfile.NamedTemporaryFile(delete=False)
        tmp_image.write(self.data)
        tmp_image.close()

        blender_image = bpy.data.images.load(tmp_image.name)
        blender_image.pack()
        blender_image.name = self.image_name
        self.blender_image_name = blender_image.name
        os.remove(tmp_image.name)
