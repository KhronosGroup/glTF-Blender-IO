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

import typing
import numpy as np
from ....gltf2_blender_gather_cache import cached
from ...gltf2_blender_gather_keyframes import Keyframe
from ..gltf2_blender_gather_animation_sampling_cache import get_cache_data


@cached
def gather_material_sampled_keyframes(
        material_id,
        channel,
        action_name,
        node_channel_is_animated: bool,
        export_settings):

    start_frame = export_settings['ranges'][material_id][action_name]['start']
    end_frame  = export_settings['ranges'][material_id][action_name]['end']

    keyframes = []

    frame = start_frame
    step = export_settings['gltf_frame_step']
    while frame <= end_frame:

        # Retrieve length of data to export
        if export_settings['KHR_animation_pointer']['materials'][material_id]['paths'][channel]['path'] != "/materials/XXX/pbrMetallicRoughness/baseColorFactor":
            length = export_settings['KHR_animation_pointer']['materials'][material_id]['paths'][channel]['length']
        else:
            length = 4

        key = Keyframe([None] * length, frame, 'value')

        value = get_cache_data(
            'value',
            material_id,
            channel,
            action_name,
            frame,
            step,
            export_settings
        )

        # Convert data if needed
        if "attenuationDistance" in export_settings['KHR_animation_pointer']['materials'][material_id]['paths'][channel]['path']:
            value = 1.0 / value if value != 0.0 else 1e13

        if export_settings['KHR_animation_pointer']['materials'][material_id]['paths'][channel]['path'] == "/materials/XXX/occlusionTexture/strength":
            if export_settings['KHR_animation_pointer']['materials'][material_id]['paths'][channel]['reverse'] is True:
                value = 1.0 - value

        key.value_total = value
        keyframes.append(key)
        frame += step

    if len(keyframes) == 0:
        # For example, option CROP negative frames, but all are negatives
        return None

    cst = fcurve_is_constant(keyframes)
    return None if cst is True else keyframes

def fcurve_is_constant(keyframes):
    if type(keyframes[0].value).__name__ == "float":
        return all([j < 0.0001 for j in np.ptp([[k.value] for k in keyframes], axis=0)])
    else:
        return all([j < 0.0001 for j in np.ptp([[k.value[i] for i in range(len(keyframes[0].value))] for k in keyframes], axis=0)])
