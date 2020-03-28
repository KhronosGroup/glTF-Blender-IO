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
from os.path import dirname, join, isfile, basename, normpath
import urllib.parse

from ...io.imp.gltf2_io_binary import BinaryData


# Note that Image is not a glTF2.0 object
class BlenderImage():
    """Manage Image."""
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("%s should not be instantiated" % cls)

    @staticmethod
    def create(gltf, img_idx):
        """Image creation."""
        img = gltf.data.images[img_idx]

        if img.blender_image_name is not None:
            # Image is already used somewhere
            return

        tmp_file = None
        try:
            if img.uri is not None and not img.uri.startswith('data:'):
                # Image stored in a file
                img_from_file = True
                path = join(dirname(gltf.filename), _uri_to_path(img.uri))
                img_name = basename(path)
                if not isfile(path):
                    gltf.log.error("Missing file (index " + str(img_idx) + "): " + img.uri)
                    return
            else:
                # Image stored as data => create a tempfile, pack, and delete file
                img_from_file = False
                img_data, img_name = BinaryData.get_image_data(gltf, img_idx)
                if img_data is None:
                    return
                tmp_file = tempfile.NamedTemporaryFile(
                    prefix='gltfimg-',
                    suffix=_img_extension(img),
                    delete=False,
                )
                tmp_file.write(img_data)
                tmp_file.close()
                path = tmp_file.name

            num_images = len(bpy.data.images)
            blender_image = bpy.data.images.load(os.path.abspath(path), check_existing=img_from_file)
            if len(bpy.data.images) != num_images:  # If created a new image
                blender_image.name = img_name
                if gltf.import_settings['import_pack_images'] or not img_from_file:
                    blender_image.pack()

            img.blender_image_name = blender_image.name

        finally:
            if tmp_file is not None:
                tmp_file.close()
                os.remove(tmp_file.name)

def _uri_to_path(uri):
    uri = urllib.parse.unquote(uri)
    return normpath(uri)

def _img_extension(img):
    if img.mime_type == 'image/png':
        return '.png'
    if img.mime_type == 'image/jpeg':
        return '.jpg'
    return None
