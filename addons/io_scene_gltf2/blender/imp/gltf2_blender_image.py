# Copyright 2018-2019 The glTF-Blender-IO authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import bpy
import os
import tempfile
from os.path import dirname, join, isfile, basename
from urllib.parse import unquote

from ...io.imp.gltf2_io_binary import BinaryData


# Note that Image is not a glTF2.0 object
class BlenderImage():
    """Manage Image."""
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("%s should not be instantiated" % cls)

    @staticmethod
    def get_image_path(gltf, img_idx):
        """Return image path."""
        pyimage = gltf.data.images[img_idx]

        image_name = "Image_" + str(img_idx)

        if pyimage.uri:
            sep = ';base64,'
            if pyimage.uri[:5] == 'data:':
                idx = pyimage.uri.find(sep)
                if idx != -1:
                    return False, None, None

            if isfile(join(dirname(gltf.filename), unquote(pyimage.uri))):
                return True, join(dirname(gltf.filename), unquote(pyimage.uri)), basename(join(dirname(gltf.filename), unquote(pyimage.uri)))
            else:
                gltf.log.error("Missing file (index " + str(img_idx) + "): " + pyimage.uri)
                return False, None, None

        if pyimage.buffer_view is None:
            return False, None, None

        return False, None, None

    @staticmethod
    def create(gltf, img_idx):
        """Image creation."""
        img = gltf.data.images[img_idx]

        if img.blender_image_name is not None:
            # Image is already used somewhere
            return

        if gltf.import_settings['import_pack_images'] is False:

            # Images are not packed (if image is a real file)
            real, path, img_name = BlenderImage.get_image_path(gltf, img_idx)

            if real is True:

                # Check if image is already loaded
                for img_ in bpy.data.images:
                    if img_.filepath == path:
                        # Already loaded, not needed to reload it
                        img.blender_image_name = img_.name
                        return

                blender_image = bpy.data.images.load(path)
                blender_image.name = img_name
                img.blender_image_name = blender_image.name
                return

        # Check if the file is already loaded (packed file)
        file_creation_needed = True
        for img_ in bpy.data.images:
            if hasattr(img_, "gltf_index") and img_['gltf_index'] == img_idx:
                file_creation_needed = False
                img.blender_image_name = img_.name
                break

        if file_creation_needed is True:
            # Create a temp image, pack, and delete image
            tmp_image = tempfile.NamedTemporaryFile(delete=False)
            img_data, img_name = BinaryData.get_image_data(gltf, img_idx)
            if img_data is not None:
                tmp_image.write(img_data)
                tmp_image.close()

                blender_image = bpy.data.images.load(tmp_image.name)
                blender_image.pack()
                blender_image.name = img_name
                img.blender_image_name = blender_image.name
                blender_image['gltf_index'] = img_idx
                os.remove(tmp_image.name)
