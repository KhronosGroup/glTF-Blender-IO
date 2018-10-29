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
import mathutils
import typing

from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached
from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.blender.exp import gltf2_blender_gather_animation_channels
from io_scene_gltf2.blender.exp import gltf2_blender_gather_animation_samplers


def gather_animations(blender_object: bpy.types.Object, export_settings) -> typing.List[gltf2_io.Animation]:
    """
    Gather all animations which contribute to the objects property
    :param blender_object: The blender object which is animated
    :param export_settings:
    :return: A list of glTF2 animations
    """

    if blender_object.animation_data is None:
        return []

    animations = []

    # Collect all 'actions' affecting this object. There is a direct mapping between blender actions and glTF animations
    blender_actions = __get_blender_actions(blender_object)

    # Export all collected actions.
    for blender_action in blender_actions:
        animation = __gather_animation(blender_action, blender_object, export_settings)
        if animation is not None:
            animations.append(animation)

    return animations


def __gather_animation(blender_action: bpy.types.Action,
                       blender_object: bpy.types.Object,
                       export_settings
                       ) -> typing.Optional[gltf2_io.Animation]:
    if not __filter_animation(blender_action, blender_object, export_settings):
        return None

    animation = gltf2_io.Animation(
        channels=__gather_channels(blender_action, blender_object, export_settings),
        extensions=__gather_extensions(blender_action, blender_object, export_settings),
        extras=__gather_extras(blender_action, blender_object, export_settings),
        name=__gather_name(blender_action, blender_object, export_settings),
        samplers=__gather_samplers(blender_action, blender_object, export_settings)
    )

    # To allow reuse of samplers in one animation,
    __link_samplers(animation, export_settings)

    if not animation.channels:
        return None

    return animation


def __filter_animation(blender_action: bpy.types.Action,
                       blender_object: bpy.types.Object,
                       export_settings
                       ) -> bool:
    if blender_action.users == 0:
        return False

    return True


def __gather_channels(blender_action: bpy.types.Action,
                      blender_object: bpy.types.Object,
                      export_settings
                      ) -> typing.List[gltf2_io.AnimationChannel]:
    return gltf2_blender_gather_animation_channels.gather_animation_channels(blender_action, blender_object, export_settings)


def __gather_extensions(blender_action: bpy.types.Action,
                        blender_object: bpy.types.Object,
                        export_settings
                        ) -> typing.Any:
    return None


def __gather_extras(blender_action: bpy.types.Action,
                    blender_object: bpy.types.Object,
                    export_settings
                    ) -> typing.Any:
    return None


def __gather_name(blender_action: bpy.types.Action,
                  blender_object: bpy.types.Object,
                  export_settings
                  ) -> typing.Optional[str]:
    return blender_action.name


def __gather_samplers(blender_action: bpy.types.Action,
                      blender_object: bpy.types.Object,
                      export_settings
                      ) -> typing.List[gltf2_io.AnimationSampler]:
    # We need to gather the samplers after gathering all channels --> populate this list in __link_samplers
    return []


def __link_samplers(animation: gltf2_io.Animation, export_settings):
    """
    After gathering, samplers are stored in the channels properties of the animation and need to be moved
    to their own list while storing an index into this list at the position where they previously were.
    This behaviour is similar to that of the glTFExporter that traverses all nodes
    :param animation:
    :param export_settings:
    :return:
    """

    # TODO: move this to some util module and update gltf2 exporter also
    T = typing.TypeVar('T')
    def __append_unique_and_get_index(l: typing.List[T], item: T):
        if item in l:
            return l.index(item)
        else:
            index = len(l)
            l.append(item)
            return index

    for i, channel in enumerate(animation.channels):
        animation.channels[i].sampler = __append_unique_and_get_index(animation.samplers, channel.sampler)


def __get_blender_actions(blender_object: bpy.types.Object
                          ) -> typing.List[bpy.types.Action]:
    blender_actions = []

    # Collect active action.
    if blender_object.animation_data.action is not None:
        blender_actions.append(blender_object.animation_data.action)

    if blender_object.type == "MESH"\
            and blender_object.data is not None \
            and blender_object.data.shape_keys is not None \
            and blender_object.data.shape_keys.animation_data is not None:
        blender_actions.append(blender_object.data.shape_keys.animation_data.action)

    # Collect associated strips from NLA tracks.
    for track in blender_object.animation_data.nla_tracks:
        # Multi-strip tracks do not export correctly yet (they need to be baked),
        # so skip them for now and only write single-strip tracks.
        if track.strips is None or len(track.strips) != 1:
            continue
        for strip in track.strips:
            blender_actions.append(strip.action)
    # Remove duplicate actions.
    blender_actions = list(set(blender_actions))

    return blender_actions
