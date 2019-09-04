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
import typing

from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.blender.exp import gltf2_blender_gather_nodes
from io_scene_gltf2.blender.exp import gltf2_blender_gather_animations
from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached
from io_scene_gltf2.blender.exp import gltf2_blender_generate_extras
from io_scene_gltf2.blender.exp import gltf2_blender_export_keys


def gather_gltf2(export_settings):
    """
    Gather glTF properties from the current state of blender.

    :return: list of scene graphs to be added to the glTF export
    """
    scenes = []
    animations = []  # unfortunately animations in gltf2 are just as 'root' as scenes.
    active_scene = None
    for blender_scene in bpy.data.scenes:
        scenes.append(__gather_scene(blender_scene, export_settings))
        if export_settings[gltf2_blender_export_keys.ANIMATIONS]:
            animations += __gather_animations(blender_scene, export_settings)
        if bpy.context.scene.name == blender_scene.name:
            active_scene = len(scenes) -1
    return active_scene, scenes, animations


@cached
def __gather_scene(blender_scene, export_settings):
    scene = gltf2_io.Scene(
        extensions=None,
        extras=__gather_extras(blender_scene, export_settings),
        name=blender_scene.name,
        nodes=[]
    )

    for blender_object in blender_scene.objects:
        if blender_object.parent is None:
            node = gltf2_blender_gather_nodes.gather_node(blender_object, blender_scene, export_settings)
            if node is not None:
                scene.nodes.append(node)

    return scene


def __merge_channels(animations) -> typing.List[gltf2_io.AnimationChannel]:
    channels = []
    samplerOffset = 0
    for anim in animations:
        for channel in anim.channels:
            # make sure to offet the channel sampler index properly
            channel.sampler += samplerOffset
            channels.append(channel)
        samplerOffset += len(anim.samplers)
    return channels


def __merge_extensions(animations) -> typing.Any:
    extensions = None
    for anim in animations:
        if anim.extensions is not None:
            if extensions is None:
                extensions = []
            extensions.extend(anim.extensions)
    # remove duplicates
    if extensions is not None:
        extensions = list(set(extensions))
    return extensions


def __merge_extras(animations) -> typing.Any:
    extras = None
    for anim in animations:
        if anim.extras is not None:
            if extras is None:
                extras = []
            extras.extend(anim.extras)
    # remove duplicates
    if extras is not None:
        extras = list(set(extras))
    return extras


def __merge_samplers(animations) -> typing.List[gltf2_io.AnimationSampler]:
    samplers = []
    for anim in animations:
        samplers.extend(anim.samplers)
    return samplers


def __merge_animations(blender_scene, animations, export_settings):
    scene_animation = gltf2_io.Animation(
            channels=__merge_channels(animations),
            extensions=__merge_extensions(animations),
            extras=__merge_extras(animations),
            name=blender_scene.name,
            samplers=__merge_samplers(animations)
        )
    return scene_animation


def __gather_animations(blender_scene, export_settings):
    animations = []
    for blender_object in blender_scene.objects:
        # First check if this object is exported or not. Do not export animation of not exported object
        obj_node = gltf2_blender_gather_nodes.gather_node(blender_object, blender_scene, export_settings)
        if obj_node is not None:
            animations += gltf2_blender_gather_animations.gather_animations(blender_object, export_settings)

    # if none of those two actions have been selected, 
    # let's merge indivudual animations into one single with multiple channels
    all_actions = export_settings['gltf_all_actions']
    nla_strips = export_settings['gltf_nla_strips']
    if not all_actions and not nla_strips:
        scene_animation = __merge_animations(blender_scene, animations, export_settings)
        animations = []
        animations.append(scene_animation)

    return animations


def __gather_extras(blender_object, export_settings):
    if export_settings[gltf2_blender_export_keys.EXTRAS]:
        return gltf2_blender_generate_extras.generate_extras(blender_object)
    return None
