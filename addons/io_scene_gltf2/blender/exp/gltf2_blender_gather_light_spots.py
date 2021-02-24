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

from typing import Optional
from io_scene_gltf2.io.com import gltf2_io_lights_punctual


def gather_light_spot(blender_lamp, export_settings) -> Optional[gltf2_io_lights_punctual.LightSpot]:

    if not __filter_light_spot(blender_lamp, export_settings):
        return None

    spot = gltf2_io_lights_punctual.LightSpot(
        inner_cone_angle=__gather_inner_cone_angle(blender_lamp, export_settings),
        outer_cone_angle=__gather_outer_cone_angle(blender_lamp, export_settings)
    )
    return spot


def __filter_light_spot(blender_lamp, _) -> bool:
    if blender_lamp.type != "SPOT":
        return False

    return True


def __gather_inner_cone_angle(blender_lamp, _) -> Optional[float]:
    angle = blender_lamp.spot_size * 0.5
    return angle - angle * blender_lamp.spot_blend


def __gather_outer_cone_angle(blender_lamp, _) -> Optional[float]:
    return blender_lamp.spot_size * 0.5
