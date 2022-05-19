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

from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.io.com.gltf2_io_debug import print_console
from io_scene_gltf2.blender.exp import gltf2_blender_gather_nodes
from io_scene_gltf2.blender.exp import gltf2_blender_gather_animations
from io_scene_gltf2.blender.exp import gltf2_blender_gather_animation_sampler_keyframes
from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached
from ..com.gltf2_blender_extras import generate_extras
from io_scene_gltf2.blender.exp import gltf2_blender_export_keys
from io_scene_gltf2.io.exp.gltf2_io_user_extensions import export_user_extensions
from io_scene_gltf2.blender.exp import gltf2_blender_gather_tree


def gather_gltf2(export_settings):
    """
    Gather glTF properties from the current state of blender.

    :return: list of scene graphs to be added to the glTF export
    """
    scenes = []
    animations = []  # unfortunately animations in gltf2 are just as 'root' as scenes.
    active_scene = None
    store_user_scene = bpy.context.scene
    scenes_to_export = bpy.data.scenes if export_settings['gltf_active_scene'] is False else [scene for scene in bpy.data.scenes if scene.name == store_user_scene.name]
    for blender_scene in scenes_to_export:
        scenes.append(__gather_scene(blender_scene, export_settings))
        if export_settings[gltf2_blender_export_keys.ANIMATIONS]:
            # resetting object cache
            gltf2_blender_gather_animation_sampler_keyframes.get_object_matrix.reset_cache()
            animations += __gather_animations(blender_scene, export_settings)
        if bpy.context.scene.name == store_user_scene.name:
            active_scene = len(scenes) -1

    # restore user scene
    bpy.context.window.scene = store_user_scene
    return active_scene, scenes, animations


@cached
def __gather_scene(blender_scene, export_settings):
    scene = gltf2_io.Scene(
        extensions=None,
        extras=__gather_extras(blender_scene, export_settings),
        name=blender_scene.name,
        nodes=[]
    )


    vtree = gltf2_blender_gather_tree.VExportTree(export_settings)
    vtree.construct(blender_scene)
    vtree.search_missing_armature() # In case armature are no parented correctly

    export_user_extensions('vtree_before_filter_hook', export_settings, vtree)

    # Now, we can filter tree if needed
    vtree.filter()

    vtree.variants_reset_to_original()

    export_user_extensions('vtree_after_filter_hook', export_settings, vtree)

    export_settings['vtree'] = vtree

    for r in [vtree.nodes[r] for r in vtree.roots]:
        node = gltf2_blender_gather_nodes.gather_node(
            r, export_settings)
        if node is not None:
            scene.nodes.append(node)

    vtree.add_neutral_bones()

    export_user_extensions('gather_scene_hook', export_settings, scene, blender_scene)

    return scene


def __gather_animations(blender_scene, export_settings):
    animations = []
    merged_tracks = {}

    vtree = export_settings['vtree']
    for obj_uuid in vtree.get_all_objects():
        blender_object = vtree.nodes[obj_uuid].blender_object

        # Do not manage not exported objects
        if vtree.nodes[obj_uuid].node is None:
            continue

        animations_, merged_tracks = gltf2_blender_gather_animations.gather_animations(obj_uuid, merged_tracks, len(animations), export_settings)
        animations += animations_

    if export_settings['gltf_nla_strips'] is False:
        # Fake an animation with all animations of the scene
        merged_tracks = {}
        merged_tracks['Animation'] = []
        for idx, animation in enumerate(animations):
            merged_tracks['Animation'].append(idx)


    to_delete_idx = []
    for merged_anim_track in merged_tracks.keys():
        if len(merged_tracks[merged_anim_track]) < 2:

            # There is only 1 animation in the track
            # If name of the track is not a default name, use this name for action
            if len(merged_tracks[merged_anim_track]) != 0:
                animations[merged_tracks[merged_anim_track][0]].name = merged_anim_track

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

            # Merging extensions
            # Provide a hook to handle extension merging since there is no way to know author intent
            export_user_extensions('merge_animation_extensions_hook', export_settings, animations[anim_idx], animations[base_animation_idx])

            # Merging extras
            # Warning, some values can be overwritten if present in multiple merged animations
            if animations[anim_idx].extras is not None:
                for k in animations[anim_idx].extras.keys():
                    if animations[base_animation_idx].extras is None:
                        animations[base_animation_idx].extras = {}
                    animations[base_animation_idx].extras[k] = animations[anim_idx].extras[k]

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
        return generate_extras(blender_object)
    return None
