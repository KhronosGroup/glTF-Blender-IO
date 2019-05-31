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
import typing
import numpy as np
import tempfile


class ExportImage:
    """Custom image class that allows manipulation and encoding of images"""
    # FUTURE_WORK: as a method to allow the node graph to be better supported, we could model some of
    # the node graph elements with numpy functions

    def __init__(self, img: typing.Union[np.ndarray, typing.List[np.ndarray]], max_channels: int = 4,\
            blender_image: bpy.types.Image = None, has_alpha: bool = False):
        if isinstance(img, list):
            np.stack(img, axis=2)

        if len(img.shape) == 2:
            # images must always have a channels dimension
            img = np.expand_dims(img, axis=2)

        if not len(img.shape) == 3 or img.shape[2] > 4:
            raise RuntimeError("Cannot construct an export image from an array of shape {}".format(img.shape))

        self._img = img
        self._max_channels = max_channels
        self._blender_image = blender_image
        self._has_alpha = has_alpha

    @classmethod
    def from_blender_image(cls, blender_image: bpy.types.Image):
        img = np.array(blender_image.pixels)
        img = img.reshape((blender_image.size[0], blender_image.size[1], blender_image.channels))
        has_alpha = blender_image.depth == 32
        return ExportImage(img=img, blender_image=blender_image, has_alpha=has_alpha)

    @classmethod
    def white_image(cls, width, height, num_channels: int = 4):
        img = np.ones((width, height, num_channels))
        return ExportImage(img=img)

    def split_channels(self):
        """return a list of numpy arrays where each list element corresponds to one image channel (r,g?,b?,a?)"""
        return np.split(self._img, self._img.shape[2], axis=2)

    @property
    def img(self) -> np.ndarray:
        return self._img

    @property
    def shape(self):
        return self._img.shape

    @property
    def width(self):
        return self.shape[0]

    @property
    def height(self):
        return self.shape[1]

    @property
    def channels(self):
        return self.shape[2]

    def __getitem__(self, key):
        """returns a new ExportImage with only the selected channels"""
        return ExportImage(self._img[:, :, key])

    def __setitem__(self, key, value):
        """set the selected channels to a new value"""
        if isinstance(key, slice):
            self._img[:, :, key] = value.img
        else:
            self._img[:, :, key] = value.img[:, :, 0]

    def append(self, other):
        if self.channels + other.channels > self._max_channels:
            raise RuntimeError("Cannot append image data to this image "
                               "because the maximum number of channels is exceeded.")

        self._img = np.concatenate([self.img, other.img], axis=2)

    def __add__(self, other):
        self.append(other)

    def encode(self, mime_type: typing.Optional[str]) -> bytes:
        file_format = {
            "image/jpeg": "JPEG",
            "image/png": "PNG"
        }.get(mime_type, "PNG")

        if self._blender_image is not None and file_format == self._blender_image.file_format:
            src_path = bpy.path.abspath(self._blender_image.filepath_raw)
            if os.path.isfile(src_path):
                with open(src_path, "rb") as f:
                    encoded_image = f.read()
                return encoded_image

        image = bpy.data.images.new("TmpImage", width=self.width, height=self.height, alpha=self._has_alpha)
        pixels = self._img.flatten().tolist()
        image.pixels = pixels

        # we just use blenders built in save mechanism, this can be considered slightly dodgy but currently is the only
        # way to support
        with tempfile.TemporaryDirectory() as tmpdirname:
            tmpfilename = tmpdirname + "/img"
            image.filepath_raw = tmpfilename
            image.file_format = file_format
            image.save()

            with open(tmpfilename, "rb") as f:
                encoded_image = f.read()

        bpy.data.images.remove(image, do_unlink=True)

        return encoded_image
