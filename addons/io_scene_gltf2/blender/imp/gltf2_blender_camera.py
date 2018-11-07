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

import bpy


class BlenderCamera():
    """Blender Camera."""

    @staticmethod
    def create(gltf, camera_id):
        """Camera creation."""
        pycamera = gltf.data.cameras[camera_id]

        if not pycamera.name:
            pycamera.name = "Camera"

        cam = bpy.data.cameras.new(pycamera.name)

        # Blender create a perspective camera by default
        if pycamera.type == "orthographic":
            cam.type = "ORTHO"

        # TODO: lot's of work for camera here...
        if hasattr(pycamera, "znear"):
            cam.clip_start = pycamera.znear

        if hasattr(pycamera, "zfar"):
            cam.clip_end = pycamera.zfar

        obj = bpy.data.objects.new(pycamera.name, cam)
        if bpy.app.version < (2, 80, 0):
            bpy.data.scenes[gltf.blender_scene].objects.link(obj)
        else:
            bpy.data.scenes[gltf.blender_scene].collection.objects.link(obj)
        return obj
