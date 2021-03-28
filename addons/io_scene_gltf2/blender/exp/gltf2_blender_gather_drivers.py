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


from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import skdriverdiscovercache, skdrivervalues
from io_scene_gltf2.blender.com.gltf2_blender_data_path import get_target_object_path


@skdriverdiscovercache
def get_sk_drivers(blender_armature):

    drivers = []

    for child in blender_armature.children:
        if not child.data:
            continue
        # child.data can be an armature - which has no shapekeys
        if not hasattr(child.data, 'shape_keys'):
            continue
        if not child.data.shape_keys:
            continue
        if not child.data.shape_keys.animation_data:
            continue
        if not child.data.shape_keys.animation_data.drivers:
            continue
        if len(child.data.shape_keys.animation_data.drivers) <= 0:
            continue

        shapekeys_idx = {}
        cpt_sk = 0
        for sk in child.data.shape_keys.key_blocks:
            if sk == sk.relative_key:
                continue
            if sk.mute is True:
                continue
            shapekeys_idx[sk.name] = cpt_sk
            cpt_sk += 1

        # Note: channels will have some None items only for SK if some SK are not animated
        idx_channel_mapping = []
        all_sorted_channels = []
        for sk_c in child.data.shape_keys.animation_data.drivers:
            sk_name = child.data.shape_keys.path_resolve(get_target_object_path(sk_c.data_path)).name
            idx = shapekeys_idx[sk_name]
            idx_channel_mapping.append((shapekeys_idx[sk_name], sk_c))
        existing_idx = dict(idx_channel_mapping)
        for i in range(0, cpt_sk):
            if i not in existing_idx.keys():
                all_sorted_channels.append(None)
            else:
                all_sorted_channels.append(existing_idx[i])

        drivers.append((child, tuple(all_sorted_channels)))

    return tuple(drivers)

@skdrivervalues
def get_sk_driver_values(blender_object, frame, fcurves):
    sk_values = []
    for f in [f for f in fcurves if f is not None]:
        sk_values.append(blender_object.data.shape_keys.path_resolve(get_target_object_path(f.data_path)).value)

    return tuple(sk_values)
