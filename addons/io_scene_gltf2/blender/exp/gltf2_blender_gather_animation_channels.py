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
import typing
from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached

from io_scene_gltf2.blender.exp import gltf2_blender_gather_animation_samplers

@cached
def gather_animation_channels(blender_action: bpy.types.Action,
                              blender_object: bpy.types.Object,
                              export_settings
                              ) -> typing.List[gltf2_io.AnimationChannel]:
    channels = typing.List[gltf2_io.AnimationChannel]()

    for action_group in blender_action.groups:
        channel = __gather_animation_channel(action_group, blender_object, export_settings)
        if channel is not None:
            channels.append(channel)

    return channels


def __gather_animation_channel(action_group: bpy.types.ActionGroup,
                               blender_object: bpy.types.Object,
                               export_settings
                               ) -> typing.Union[gltf2_io.AnimationChannel, None]:
    if not __filter_animation_channel(action_group, blender_object, export_settings):
        return None

    return gltf2_io.AnimationChannel(
        extensions=None,
        extras=None,
        sampler=None,
        target=None
    )


def __filter_animation_channel(action_group: bpy.types.ActionGroup,
                               blender_object: bpy.types.Object,
                               export_settings
                               ) -> bool:
    return True


def __gather_extensions(action_group: bpy.types.ActionGroup,
                        blender_object: bpy.types.Object,
                        export_settings
                        ) -> typing.Any:
    return None


def __gather_extras(action_group: bpy.types.ActionGroup,
                    blender_object: bpy.types.Object,
                    export_settings
                    ) -> typing.Any:
    return None


def __gather_sampler(action_group: bpy.types.ActionGroup,
                     blender_object: bpy.types.Object,
                     export_settings
                     ) -> gltf2_io.AnimationSampler:
    return gltf2_blender_gather_animation_samplers.gather_animation_sampler(
        action_group,
        blender_object,
        export_settings
    )


def __gather_target(action_group: bpy.types.ActionGroup,
                    blender_object: bpy.types.Object,
                    export_settings
                    ) -> gltf2_io.AnimationChannelTarget:
    return None
