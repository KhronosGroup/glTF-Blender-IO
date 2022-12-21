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

import bpy
from ....io.com import gltf2_io
from .gltf2_blender_gather_drivers import get_sk_drivers
from .sampled.armature.gltf2_blender_gather_armature_channels import gather_armature_sampled_channels
from .sampled.object.gltf2_blender_gather_object_channels import gather_object_sampled_channels
from .sampled.shapekeys.gltf2_blender_gather_sk_channels import gather_sk_sampled_channels
from .gltf2_blender_gather_animation_utils import link_samplers

def gather_scene_animation(export_settings):

    # if there is no animation in file => no need to bake
    if len(bpy.data.actions) == 0:
        return None

    total_channels = []

    start_frame = bpy.context.scene.frame_start
    end_frame = bpy.context.scene.frame_end

    # TODOANIM limits range all options

    # This mode will bake all objects like there are in the scene
    vtree = export_settings['vtree']
    for obj_uuid in vtree.get_all_objects():

        # Do not manage not exported objects
        if vtree.nodes[obj_uuid].node is None:
            continue

        blender_object = export_settings['vtree'].nodes[obj_uuid].blender_object

        export_settings['ranges'][obj_uuid] = {}
        export_settings['ranges'][obj_uuid][obj_uuid] = {'start': start_frame, 'end': end_frame}
        if blender_object.type == "ARMATURE":
            # Manage sk drivers
            obj_drivers = get_sk_drivers(obj_uuid, export_settings)
            for obj_dr in obj_drivers:
                if obj_dr not in export_settings['ranges']:
                    export_settings['ranges'][obj_dr] = {}
                export_settings['ranges'][obj_dr][obj_uuid + "_" + obj_uuid] = {}
                export_settings['ranges'][obj_dr][obj_uuid + "_" + obj_uuid]['start'] = start_frame
                export_settings['ranges'][obj_dr][obj_uuid + "_" + obj_uuid]['end'] = end_frame

        if blender_object.type != "ARMATURE":
            # We have to check if this is a skinned mesh, because we don't have to force animation baking on this case
            if export_settings['vtree'].nodes[obj_uuid].skin is None:
                channels = gather_object_sampled_channels(obj_uuid, obj_uuid, export_settings)
                if channels is not None:
                    total_channels.extend(channels)
            if export_settings['gltf_morph_anim'] and blender_object.type == "MESH" \
                    and blender_object.data is not None \
                    and blender_object.data.shape_keys is not None:
                    # TODOANIM: should not bake if already implicated in a driver
                channels = gather_sk_sampled_channels(obj_uuid, obj_uuid, export_settings)
                if channels is not None:
                    total_channels.extend(channels)
        else:
                channels = gather_armature_sampled_channels(obj_uuid, obj_uuid, export_settings)
                if channels is not None:
                    total_channels.extend(channels)

    if len(total_channels) > 0:
        animation = gltf2_io.Animation(
            channels=total_channels,
            extensions=None,
            extras=None,
            name=bpy.context.scene.name,
            samplers=[]
        )
        link_samplers(animation, export_settings)
        return [animation]

    return None
    