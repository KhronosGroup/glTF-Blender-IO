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
def gather_animation_channel_target(channels: typing.Tuple[bpy.types.FCurve],
                                    blender_object: bpy.types.Object,
                                    bake_bone: typing.Union[str, None],
                                    bake_channel: typing.Union[str, None],
                                    export_settings
                                    ) -> gltf2_io.AnimationChannelTarget:

        return gltf2_io.AnimationChannelTarget(
            extensions=__gather_extensions(channels, blender_object, export_settings, bake_bone),
            extras=__gather_extras(channels, blender_object, export_settings, bake_bone),
            node=__gather_node(channels, blender_object, export_settings, bake_bone),
            path=__gather_path(channels, blender_object, export_settings, bake_bone, bake_channel)
        )

def __gather_extensions(channels: typing.Tuple[bpy.types.FCurve],
                        blender_object: bpy.types.Object,
                        export_settings,
                        bake_bone: typing.Union[str, None]
                        ) -> typing.Any:
    return None


def __gather_extras(channels: typing.Tuple[bpy.types.FCurve],
                    blender_object: bpy.types.Object,
                    export_settings,
                    bake_bone: typing.Union[str, None]
                    ) -> typing.Any:
    return None


def __gather_node(channels: typing.Tuple[bpy.types.FCurve],
                  blender_object: bpy.types.Object,
                  export_settings,
                  bake_bone: typing.Union[str, None]
                  ) -> gltf2_io.Node:
    if blender_object.type == "ARMATURE":
        # TODO: get joint from fcurve data_path and gather_joint

        if bake_bone is not None:
            blender_bone = blender_object.pose.bones[bake_bone]
        else:
            blender_bone = blender_object.path_resolve(channels[0].data_path.rsplit('.', 1)[0])

        if isinstance(blender_bone, bpy.types.PoseBone):
            return gltf2_blender_gather_joints.gather_joint(blender_bone, export_settings)

    return gltf2_blender_gather_nodes.gather_node(blender_object, None, export_settings)


def __gather_path(channels: typing.Tuple[bpy.types.FCurve],
                  blender_object: bpy.types.Object,
                  export_settings,
                  bake_bone: typing.Union[str, None],
                  bake_channel: typing.Union[str, None]
                  ) -> str:
    if bake_channel is None:
        target = channels[0].data_path.split('.')[-1]
    else:
        target = bake_channel
    path = {
        "delta_location": "translation",
        "delta_rotation_euler": "rotation",
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
