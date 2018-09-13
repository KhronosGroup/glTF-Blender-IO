# Copyright (c) 2017 The Khronos Group Inc.
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
import functools

from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.blender.exp import gltf2_blender_gather_nodes
from io_scene_gltf2.blender.exp import gltf2_blender_gather_animations


def cached(func):
    """
    Decorator to cache gather functions results. The gather function is only executed if its result isn't in the cache yet
    :param func: the function to be decorated. It will have a static __cache member afterwards
    :return:
    """
    @functools.wraps(func)
    def wrapper_cached(*args, **kwargs):
        assert len(args) == 2 and len(kwargs) == 0, "Wrong signature for cached function"
        blender_obj, export_settings = args
        # invalidate cache if export settings have changed
        if export_settings != func.__export_settings:
            func.__cache = {}
            func.__export_settings = export_settings
        # use or fill cache
        if blender_obj in func.__cache:
            return func.__cache[blender_obj]
        else:
            result = func(*args)
            func.__cache[blender_obj] = result
            return result
    return wrapper_cached


def gather_gltf2(operator, context, export_settings):
    """
    Gather glTF properties from the current state of blender
    :param operator: blender operator
    :param context: blender context
    :return: list of scene graphs to be added to the glTF export
    """
    scenes = []
    animations = []  # unfortunately animations in gltf2 are just as 'root' as scenes.
    for blender_scene in bpy.data.scenes:
        scenes.append(__gather_scene(blender_scene, export_settings))
        animations += __gather_animation(blender_scene, export_settings)

    return scenes


@cached
def __gather_scene(blender_scene, export_settings):
    scene = gltf2_io.Scene(
        extensions=None,
        extras=None,
        name=blender_scene.name,
        nodes=[]
    )

    for blender_object in blender_scene.objects:
        if blender_object.parent is None:
            node = gltf2_blender_gather_nodes.gather_node(blender_object, export_settings)
            if node is not None:
                scene.nodes.append(node)

    # TODO: materials, textures, images
    # TODO: animations
    # TODO: lights
    # TODO: meshes
    # TODO: asset?

    return scene


@cached
def __gather_animation(blender_scene, export_settings):
    for blender_object in blender_scene.objects:
        return gltf2_blender_gather_animations.gather_animation(blender_object, export_settings)