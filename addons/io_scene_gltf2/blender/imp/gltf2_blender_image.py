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
from os.path import dirname, join, isfile

from ...io.imp.gltf2_io_binary import *

# Note that Image is not a glTF2.0 object
class BlenderImage():

    @staticmethod
    def get_image_path(gltf, img_idx):
        pyimage = gltf.data.images[img_idx]

        image_name = "Image_" + str(img_idx)

        if pyimage.uri:
            sep = ';base64,'
            if pyimage.uri[:5] == 'data:':
                idx = pyimage.uri.find(sep)
                if idx != -1:
                    return False, None, None

            if isfile(join(dirname(gltf.filename), pyimage.uri)):
                return True, join(dirname(gltf.filename), pyimage.uri), image_name
            else:
                pyimage.gltf.log.error("Missing file (index " + str(img_idx) + "): " + pyimage.uri)
                return False, None, None

        if pyimage.buffer_view is None:
            return False, None, None

        return False, None, None

    @staticmethod
    def create(gltf, img_idx):

        img = gltf.data.images[img_idx]

        img.blender_image_name = None

        if gltf.import_settings['pack_images'] == False:

            # Images are not packed (if image is a real file)
            real, path, img_name = BlenderImage.get_image_path(gltf, img_idx)

            if real == True:

                blender_image = bpy.data.images.load(path)
                blender_image.name = img_name
                img.blender_image_name = blender_image.name
                return

        # Create a temp image, pack, and delete image
        tmp_image = tempfile.NamedTemporaryFile(delete=False)
        img_data, img_name = BinaryData.get_image_data(gltf, img_idx)
        tmp_image.write(img_data)
        tmp_image.close()

        blender_image = bpy.data.images.load(tmp_image.name)
        blender_image.pack()
        blender_image.name = img_name
        img.blender_image_name = blender_image.name
        os.remove(tmp_image.name)
