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


def get_target_property_name(data_path: str) -> str:
    """Retrieve target property."""
    return data_path.rsplit('.', 1)[-1]


def get_target_object_path(data_path: str) -> str:
    """Retrieve target object data path without property"""
    path_split = data_path.rsplit('.', 1)
    self_targeting = len(path_split) < 2
    if self_targeting:
        return ""
    return path_split[0]

def get_rotation_modes(target_property: str) -> str:
    """Retrieve rotation modes based on target_property"""
    if target_property == "rotation_euler":
        return True, False, ["XYZ", "XZY", "YXZ", "YZX", "ZXY", "ZYX"]
    elif target_property == "delta_rotation_euler":
        return True, True, ["XYZ", "XZY", "YXZ", "YZX", "ZXY", "ZYX"]
    elif target_property == "rotation_quaternion":
        return True, False, ["QUATERNION"]
    elif target_property == "delta_rotation_quaternion":
        return True, True, ["QUATERNION"]
    elif target_property in ["rotation_axis_angle"]:
        return True, False, ["AXIS_ANGLE"]
    else:
        return False, False, []
