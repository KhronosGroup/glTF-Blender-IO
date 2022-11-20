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

import typing
from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached
from io_scene_gltf2.io.exp.gltf2_io_user_extensions import export_user_extensions
from io_scene_gltf2.blender.exp import gltf2_blender_gather_joints

@cached
def gather_armature_baked_channel_target(
        armature_uuid: str,
        bone: str,
        channel: str,
        export_settings
        ) -> gltf2_io.AnimationChannelTarget:

    blender_object = export_settings['vtree'].nodes[armature_uuid].blender_object

    animation_channel_target = gltf2_io.AnimationChannelTarget(
        extensions=__gather_extensions(armature_uuid, bone, channel, export_settings),
        extras=__gather_extras(armature_uuid, bone, channel, export_settings),
        node=__gather_node(armature_uuid, bone, export_settings),
        path=__gather_path(channel, export_settings)
        )

    export_user_extensions('gather_animation_bone_bake_channel_target_hook',
                            export_settings,
                            blender_object,
                            bone,
                            channel)

    return animation_channel_target

def __gather_extensions(armature_uuid, bone, channel, export_settings):
    return None

def __gather_extras(armature_uuid, bone, channel, export_settings):
    return None

def __gather_node(armature_uuid, bone, export_settings):
    return gltf2_blender_gather_joints.gather_joint_vnode(export_settings['vtree'].nodes[armature_uuid].bones[bone], export_settings)

def __gather_path(channel, export_settings):
    return {
        "location":"translation",
        "rotation_quaternion":"rotation",
        "scale":"scale"
    }.get(channel)