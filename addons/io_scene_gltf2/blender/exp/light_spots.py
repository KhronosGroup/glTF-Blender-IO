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
from ...io.com import lights_punctual as gltf2_io_lights_punctual


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


def __gather_inner_cone_angle(blender_lamp, export_settings) -> Optional[float]:
    angle = blender_lamp.spot_size * 0.5

    path_ = {}
    path_['length'] = 1
    path_['path'] = "/extensions/KHR_lights_punctual/lights/XXX/spot.innerConeAngle"
    path_['additional_path'] = "spot_size"
    export_settings['current_paths']["spot_blend"] = path_

    return angle - angle * blender_lamp.spot_blend


def __gather_outer_cone_angle(blender_lamp, export_settings) -> Optional[float]:

    path_ = {}
    path_['length'] = 1
    path_['path'] = "/extensions/KHR_lights_punctual/lights/XXX/spot.outerConeAngle"
    export_settings['current_paths']["spot_size"] = path_

    return blender_lamp.spot_size * 0.5
