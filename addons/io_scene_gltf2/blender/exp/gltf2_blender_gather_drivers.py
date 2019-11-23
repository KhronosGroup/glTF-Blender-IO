# Copyright 2019 The glTF-Blender-IO authors.
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


from io_scene_gltf2.blender.exp import gltf2_blender_gather_nodes
from io_scene_gltf2.blender.com import gltf2_blender_conversion


def gather_drivers(blender_object, export_settings):
    """
    Get driver impacted objects of the scene.

    :return: targets transform to be animated
    """

    # Only this cases are managed for now:
    # * Driver on location / rotation / scale of object, managed by:
    #       location / rotation / scale of another object


    drivers = []

    # Check if this object has driver on transforms
    if not blender_object.animation_data:
        continue
    if not blender_object.animation_data.drivers:
        continue
    if len(blender_object.animation_data.drivers) == 0:
        continue
    for dr in blender_object.animation_data.drivers:
        if not dr.driver:
            continue
        if not dr.driver.is_valid:
            continue
        for var in dr.driver.variables:
            if dr.driver.type == "SCRIPTED" and var.name not in dr.driver.expression:
                continue
            if var.type == "TRANSFORMS":
                # Store info about this driver
                drivers.append(gltf2_blender_conversion.get_target(dr.data_path))

    return drivers if len(drivers) != 0 else None
