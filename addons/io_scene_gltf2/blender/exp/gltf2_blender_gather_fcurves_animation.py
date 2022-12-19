# Copyright 2018-2022 The glTF-Blender-IO authors.
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
from io_scene_gltf2.blender.exp.gltf2_blender_gather_fcurves_channels import gather_animation_fcurves_channels

def gather_animation_fcurves(
        obj_uuid: str,
        blender_action: bpy.types.Action,
        export_settings
        ):

    name = __gather_name(blender_action, export_settings)

    channels, to_be_sampled = __gather_channels_fcurves(obj_uuid, blender_action, export_settings)

    animation = gltf2_io.Animation(
        channels=channels,
        extensions=None,
        extras=None,
        name=name,
        samplers=[]
    )

    if not animation.channels:
        return None, to_be_sampled

    #TODOANIM add hook
    return animation, to_be_sampled

def __gather_name(blender_action: bpy.types.Action,
                  export_settings
                  ) -> str:
    return blender_action.name

def __gather_channels_fcurves(
        obj_uuid: str, 
        blender_action: bpy.types.Action, 
        export_settings):
    return gather_animation_fcurves_channels(obj_uuid, blender_action, export_settings)
