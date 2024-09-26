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

from ......io.exp.user_extensions import export_user_extensions
from ......io.com import gltf2_io
from ....cache import cached


@cached
def gather_object_sampled_channel_target(
        obj_uuid: str,
        channel: str,
        export_settings
        ) -> gltf2_io.AnimationChannelTarget:

    blender_object = export_settings['vtree'].nodes[obj_uuid].blender_object

    animation_channel_target = gltf2_io.AnimationChannelTarget(
        extensions=__gather_extensions(obj_uuid, channel, export_settings),
        extras=__gather_extras(obj_uuid, channel, export_settings),
        node=__gather_node(obj_uuid, export_settings),
        path=__gather_path(channel, export_settings)
        )

    export_user_extensions('gather_animation_object_sampled_channel_target_hook',
                            export_settings,
                            blender_object,
                            channel)

    return animation_channel_target

def __gather_extensions(armature_uuid, channel, export_settings):
    return None

def __gather_extras(armature_uuid, channel, export_settings):
    return None

def __gather_node(obj_uuid: str, export_settings):
    return export_settings['vtree'].nodes[obj_uuid].node

def __gather_path(channel, export_settings):
    return {
        "location":"translation",
        "rotation_quaternion":"rotation",
        "scale":"scale"
    }.get(channel)
