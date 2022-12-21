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


from .gltf2_blender_gather_action import gather_actions_animations


def gather_animations(export_settings):

    # Reinit stored data
    export_settings['ranges'] = {}
    export_settings['action_slide'] = {}

    if export_settings['gltf_animation_mode'] in ["ACTIVE_ACTIONS", "ACTIONS"]:
        return gather_actions_animations(export_settings)
