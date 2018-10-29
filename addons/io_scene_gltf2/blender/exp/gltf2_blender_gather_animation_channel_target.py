# Copyright 2018 The glTF-Blender-IO authors.
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
import typing
from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached
from io_scene_gltf2.blender.exp import gltf2_blender_gather_nodes
from io_scene_gltf2.blender.exp import gltf2_blender_gather_joints


@cached
def gather_animation_channel_target(action_group: bpy.types.ActionGroup,
                                    blender_object: bpy.types.Object,
                                    export_settings
                                    ) -> gltf2_io.AnimationChannelTarget:
    return gltf2_io.AnimationChannelTarget(
        extensions=__gather_extensions(action_group, blender_object, export_settings),
        extras=__gather_extras(action_group, blender_object, export_settings),
        node=__gather_node(action_group, blender_object, export_settings),
        path=__gather_path(action_group, blender_object, export_settings)
    )


def __gather_extensions(action_group: bpy.types.ActionGroup,
                        blender_object: bpy.types.Object,
                        export_settings
                        ) -> typing.Any:
    return None


def __gather_extras(action_group: bpy.types.ActionGroup,
                    blender_object: bpy.types.Object,
                    export_settings
                    ) -> typing.Any:
    return None


def __gather_node(action_group: bpy.types.ActionGroup,
                  blender_object: bpy.types.Object,
                  export_settings
                  ) -> gltf2_io.Node:
    if blender_object.type == "ARMATURE":
        # TODO: get joint from fcurve data_path and gather_joint
        blender_bone = blender_object.path_resolve(action_group.channels[0].data_path.rsplit('.', 1)[0])
        return gltf2_blender_gather_joints.gather_joint(blender_bone, export_settings)

    return gltf2_blender_gather_nodes.gather_node(blender_object, export_settings)


def __gather_path(action_group: bpy.types.ActionGroup,
                  blender_object: bpy.types.Object,
                  export_settings
                  ) -> str:
    target = action_group.channels[0].data_path.split('.')[-1]
    path = {
        "location": "translation",
        "rotation_axis_angle": "rotation",
        "rotation_euler": "rotation",
        "rotation_quaternion": "rotation",
        "scale": "scale",
        "value": "weights"
    }.get(target)

    if target is None:
        raise RuntimeError("Cannot export an animation with {} target".format(target))

    return path
