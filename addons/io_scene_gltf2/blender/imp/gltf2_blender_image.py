# Copyright 2018-2021 The glTF-Blender-IO authors.
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
import re

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
        img_name = img.name

        if img.blender_image_name is not None:
            # Image is already used somewhere
            return

        is_binary = False
        is_placeholder = False

        num_images = len(bpy.data.images)

            if img.uri is not None and not img.uri.startswith('data:'):
                # Image stored in a file
                path = join(dirname(gltf.filename), _uri_to_path(img.uri))
                try:
                    path = bpy.path.relpath(path)
                except ValueError:
                    # May happen on Windows if on different drives, eg. C:\ and D:\
                    pass
                if bpy.data.is_saved and bpy.context.preferences.filepaths.use_relative_paths:
                    path = bpy.path.relpath(path)

                img_name = img_name or basename(path)

                try:
                    blender_image = bpy.data.images.load(
                        path,
                        check_existing=True,
                    )
                except RuntimeError:
                    gltf.log.error("Missing image file (index %d): %s" % (img_idx, path))
                    blender_image = _placeholder_image(img_name, os.path.abspath(path))
                    is_placeholder = True

            else:
                # Image stored as data => pack
                is_binary = True
                img_data = BinaryData.get_image_data(gltf, img_idx)
                if img_data is None:
                    return
                img_name = 'Image_%d' % img_idx

                # Create image, width and height are dummy values
                img_pack = bpy.data.images.new(img_name, 8, 8)
                # Set packed file data
                img_pack.pack(data=img_data.tobytes(), data_len=len(img_data))
                img_pack.source = 'FILE'
                img.blender_image_name = img_pack.name

            if is_binary is False:
                if len(bpy.data.images) != num_images:  # If created a new image
                    blender_image.name = img_name
                    img.blender_image_name = img_name

                    needs_pack = gltf.import_settings['import_pack_images']
                    if not is_placeholder and needs_pack:
                        blender_image.pack()

def _placeholder_image(name, path):
    image = bpy.data.images.new(name, 128, 128)
    # allow the path to be resolved later
    image.filepath = path
    image.source = 'FILE'
    return image

def _uri_to_path(uri):
    uri = urllib.parse.unquote(uri)
    return normpath(uri)
