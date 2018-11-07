# Copyright 2018 The glTF-Blender-IO authors.
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

#
# Imports
#

from ...io.com.gltf2_io_image import create_img_from_pixels


def create_img_from_blender_image(blender_image):
    """
    Create a new image object using the given blender image.

    Returns the created image object.
    """
    if blender_image is None:
        return None

    return create_img_from_pixels(blender_image.size[0], blender_image.size[1], blender_image.pixels[:])
