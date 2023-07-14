# Copyright 2018-2023 The glTF-Blender-IO authors.
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

from ......io.com import gltf2_io
from ....gltf2_blender_gather_cache import cached


@cached
def gather_material_sampled_channel_target(
        material_id,
        channel: str,
        export_settings
        ) -> gltf2_io.AnimationChannelTarget:

    animation_channel_target = gltf2_io.AnimationChannelTarget(
        extensions=__gather_extensions(material_id, channel, export_settings),
        extras=__gather_extras(material_id, channel, export_settings),
        node=__gather_node(material_id, export_settings),
        path=__gather_path(material_id, channel, export_settings)
        )

    return animation_channel_target

def __gather_extensions(material_id, channel, export_settings):
    return None

def __gather_extras(material_id, channel, export_settings):
    return None

def __gather_node(material_id, export_settings):
    return export_settings['KHR_animation_pointer']['materials'][material_id]['glTF_material']

def __gather_path(material_id, channel, export_settings):
    return export_settings['KHR_animation_pointer']['materials'][material_id]['paths'][channel]['path']
