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

from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.io.com.gltf2_io_debug import print_console
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


def __gather_animations(blender_scene, export_settings):
    animations = []
    merged_tracks = {}

    for blender_object in blender_scene.objects:
        # First check if this object is exported or not. Do not export animation of not exported object
        obj_node = gltf2_blender_gather_nodes.gather_node(blender_object, blender_scene, export_settings)
        if obj_node is not None:
            animations_, merged_tracks = gltf2_blender_gather_animations.gather_animations(blender_object, merged_tracks, len(animations), export_settings)
            animations += animations_

    if export_settings['gltf_nla_strips'] is False:
        # Fake an animation witha all animations of the scene
        merged_tracks = {}
        merged_tracks['Animation'] = []
        for idx, animation in enumerate(animations):
            merged_tracks['Animation'].append(idx)


    to_delete_idx = []
    for merged_anim_track in merged_tracks.keys():
        if len(merged_tracks[merged_anim_track]) < 2:
            continue

        base_animation_idx = None
        offset_sampler = 0

        for idx, anim_idx in enumerate(merged_tracks[merged_anim_track]):
            if idx == 0:
                base_animation_idx = anim_idx
                animations[anim_idx].name = merged_anim_track
                already_animated = []
                for channel in animations[anim_idx].channels:
                    already_animated.append((channel.target.node, channel.target.path))
                continue

            to_delete_idx.append(anim_idx)

            offset_sampler = len(animations[base_animation_idx].samplers)
            for sampler in animations[anim_idx].samplers:
                animations[base_animation_idx].samplers.append(sampler)

            for channel in animations[anim_idx].channels:
                if (channel.target.node, channel.target.path) in already_animated:
                    print_console("WARNING", "Some strips have same channel animation ({}), on node {} !".format(channel.target.path, channel.target.node.name))
                    continue
                animations[base_animation_idx].channels.append(channel)
                animations[base_animation_idx].channels[-1].sampler = animations[base_animation_idx].channels[-1].sampler + offset_sampler
                already_animated.append((channel.target.node, channel.target.path))

    new_animations = []
    if len(to_delete_idx) != 0:
        for idx, animation in enumerate(animations):
            if idx in to_delete_idx:
                continue
            new_animations.append(animation)
    else:
        new_animations = animations


    return new_animations


def __gather_extras(blender_object, export_settings):
    if export_settings[gltf2_blender_export_keys.EXTRAS]:
        return gltf2_blender_generate_extras.generate_extras(blender_object)
    return None
