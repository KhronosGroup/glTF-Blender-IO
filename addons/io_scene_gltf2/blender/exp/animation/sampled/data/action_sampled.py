# Copyright 2018-2026 The glTF-Blender-IO authors.
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

import bpy
from ......io.exp.user_extensions import export_user_extensions
from .channels import gather_data_sampled_channels


def gather_action_mesh_sampled(obj_uuid: str,
                               blender_action,
                               slot_identifier: str,
                               cache_key: str,
                               export_settings):
    # Used for custom properties on mesh data

    # If no animation in file, no need to bake
    if len(bpy.data.actions) == 0:
        return None

    channels = __gather_channels('meshes', obj_uuid, blender_action.name if blender_action else cache_key,
                                 slot_identifier if blender_action else None, export_settings)

    if not channels:
        return None

    return channels


def gather_action_material_sampled(mat_uuid: str,
                                   blender_action,
                                   slot_identifier: str,
                                   cache_key: str,
                                   export_settings):

    # If no animation in file, no need to bake
    if len(bpy.data.actions) == 0:
        return None

    channels = __gather_channels('materials', mat_uuid, blender_action.name if blender_action else cache_key,
                                 slot_identifier if blender_action else None, export_settings)

    if not channels:
        return None

    blender_material = export_settings['material_identifiers'][mat_uuid]
    export_user_extensions(
        'animation_channels_material_sampled',
        export_settings,
        channels,
        blender_material,
        blender_action,
        slot_identifier,
        cache_key)

    return channels


def __gather_channels(data_type: str, uuid: str, blender_action_name: str, slot_identifier: str,
                      export_settings):

    # For meshes, this is only for custom properties
    if data_type == 'meshes':
        data_main_type = 'extras'
    elif data_type == 'materials':
        data_main_type = 'extras'  # TODOEXTRAS This can be either for materials animation pointer or for extras
        # Currently, material animation pointer is not supported (doubleSided ?)
    else:
        # This is for animation pointer
        data_main_type = None

    return gather_data_sampled_channels(
        data_main_type,
        data_type,
        uuid,
        blender_action_name,
        slot_identifier,
        None,
        export_settings)
