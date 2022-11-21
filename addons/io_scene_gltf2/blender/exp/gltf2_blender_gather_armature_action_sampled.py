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

import typing
from io_scene_gltf2.io.com import gltf2_io
from .gltf2_blender_gather_armature_channels import gather_armature_sampled_channels
from ..com.gltf2_blender_extras import generate_extras
from io_scene_gltf2.io.com.gltf2_io_debug import print_console
from io_scene_gltf2.io.exp.gltf2_io_user_extensions import export_user_extensions
import bpy


def gather_action_armature_sampled(armature_uuid: str, blender_action: typing.Optional[bpy.types.Action], export_settings):
    print("Using New Armature Bake action code") #TODOANIM remove print

    blender_object = export_settings['vtree'].nodes[armature_uuid].blender_object

    name = __gather_name(blender_action, armature_uuid, export_settings)

    try:
        animation = gltf2_io.Animation(
            channels=__gather_channels(armature_uuid, blender_action.name if blender_action else armature_uuid, export_settings),
            extensions=None,
            extras=__gather_extras(blender_action, export_settings),
            name=name,
            samplers=[] # We need to gather the samplers after gathering all channels --> populate this list in __link_samplers
        )
    except RuntimeError as error:
        print_console("WARNING", "Animation '{}' could not be exported. Cause: {}".format(name, error))
        return None

    export_user_extensions('pre_gather_animation_hook', export_settings, animation, blender_action, blender_object)

    if not animation.channels:
        return None

    # To allow reuse of samplers in one animation : This will be done later, when we know all channels are here

    export_user_extensions('gather_animation_hook', export_settings, animation, blender_action, blender_object)

    return animation

def __gather_name(blender_action: bpy.types.Action,
                  armature_uuid: str,  
                  export_settings
                  ) -> str:
    return blender_action.name if blender_action else export_settings['vtree'].nodes[armature_uuid].blender_object.name


def __gather_channels(armature_uuid, blender_action_name, export_settings) -> typing.List[gltf2_io.AnimationChannel]:
    return gather_armature_sampled_channels(armature_uuid, blender_action_name, export_settings)


def __gather_extras(blender_action: bpy.types.Action, export_settings) -> typing.Any:

    if export_settings['gltf_extras']:
        return generate_extras(blender_action)
    return None