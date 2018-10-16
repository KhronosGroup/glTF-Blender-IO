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

from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached
from io_scene_gltf2.io.com import gltf2_io

import bpy
import math

@cached
def gather_camera(blender_obect, export_settings):
    if not __filter_camera(blender_obect, export_settings):
        return None

    return gltf2_io.Camera(
        extensions=__gather_extensions(blender_obect, export_settings),
        extras=__gather_extras(blender_obect, export_settings),
        name=__gather_name(blender_obect, export_settings),
        orthographic=__gather_orthographic(blender_obect, export_settings),
        perspective=__gather_perspective(blender_obect, export_settings),
        type=__gather_type(blender_obect, export_settings)
    )


def __filter_camera(blender_object, export_settings):
    if blender_object.type != 'CAMERA':
        return False
    if not __gather_type(blender_object, export_settings):
        return False

    return True


def __gather_extensions(blender_object, export_settings):
    return None


def __gather_extras(blender_object, export_settings):
    return None


def __gather_name(blender_object, export_settings):
    return blender_object.data.name


def __gather_orthographic(blender_object, export_settings):
    if __gather_type(blender_object, export_settings) == "orthographic":
        orthographic = gltf2_io.CameraOrthographic(
            extensions=None,
            extras=None,
            xmag=None,
            ymag=None,
            zfar=None,
            znear=None
        )
        blender_camera = blender_object.data

        orthographic.xmag = blender_camera.ortho_scale
        orthographic.ymag = blender_camera.ortho_scale

        orthographic.znear = blender_camera.clip_start
        orthographic.zfar = blender_camera.clip_end

        return orthographic
    return None


def __gather_perspective(blender_object, export_settings):
    if __gather_type(blender_object, export_settings) == "perspective":
        perspective = gltf2_io.CameraPerspective(
            aspect_ratio=None,
            extensions=None,
            extras=None,
            yfov=None,
            zfar=None,
            znear=None
        )
        blender_camera = blender_object.data

        width = bpy.context.scene.render.pixel_aspect_x * bpy.context.scene.render.resolution_x
        height = bpy.context.scene.render.pixel_aspect_y * bpy.context.scene.render.resolution_y
        perspective.aspectRatio = width / height

        if width >= height:
            if blender_camera.sensor_fit != 'VERTICAL':
                perspective.yfov = 2.0 * math.atan(math.tan(blender_camera.angle * 0.5) / perspective.aspectRatio)
            else:
                perspective.yfov = blender_camera.angle
        else:
            if blender_camera.sensor_fit != 'HORIZONTAL':
                perspective.yfov = blender_camera.angle
            else:
                perspective.yfov = 2.0 * math.atan(math.tan(blender_camera.angle * 0.5) / perspective.aspectRatio)

        perspective.znear = blender_camera.clip_start

        if not export_settings['gltf_camera_infinite']:
            perspective.zfar = blender_camera.clip_end

        return perspective
    return None


def __gather_type(blender_object, export_settings):
    camera = blender_object.data
    if camera.type == 'PERSP':
        return "perspective"
    elif camera.type == 'ORTHO':
        return "orthographic"
    return None

