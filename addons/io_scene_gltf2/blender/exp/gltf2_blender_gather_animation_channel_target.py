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


import bpy
import typing
from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached
from io_scene_gltf2.blender.exp import gltf2_blender_gather_nodes
from io_scene_gltf2.blender.exp import gltf2_blender_gather_joints
from io_scene_gltf2.blender.exp import gltf2_blender_gather_skins
from io_scene_gltf2.io.exp.gltf2_io_user_extensions import export_user_extensions

@cached
def gather_animation_channel_target(channels: typing.Tuple[bpy.types.FCurve],
                                    blender_object: bpy.types.Object,
                                    bake_bone: typing.Union[str, None],
                                    bake_channel: typing.Union[str, None],
                                    driver_obj,
                                    export_settings
                                    ) -> gltf2_io.AnimationChannelTarget:

        animation_channel_target = gltf2_io.AnimationChannelTarget(
            extensions=__gather_extensions(channels, blender_object, export_settings, bake_bone),
            extras=__gather_extras(channels, blender_object, export_settings, bake_bone),
            node=__gather_node(channels, blender_object, export_settings, bake_bone, driver_obj),
            path=__gather_path(channels, blender_object, export_settings, bake_bone, bake_channel)
        )

        export_user_extensions('gather_animation_channel_target_hook',
                               export_settings,
                               animation_channel_target,
                               channels,
                               blender_object,
                               bake_bone,
                               bake_channel)

        return animation_channel_target

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
                  bake_bone: typing.Union[str, None],
                  driver_obj
                  ) -> gltf2_io.Node:

    if driver_obj is not None:
        return gltf2_blender_gather_nodes.gather_node(driver_obj,
            driver_obj.library.name if driver_obj.library else None,
            None, None, export_settings)

    if blender_object.type == "ARMATURE":
        # TODO: get joint from fcurve data_path and gather_joint

        if bake_bone is not None:
            blender_bone = blender_object.pose.bones[bake_bone]
        else:
            blender_bone = blender_object.path_resolve(channels[0].data_path.rsplit('.', 1)[0])

        if isinstance(blender_bone, bpy.types.PoseBone):
            if export_settings["gltf_def_bones"] is False:
                obj = blender_object.proxy if blender_object.proxy else blender_object
                return gltf2_blender_gather_joints.gather_joint(obj, blender_bone, export_settings)
            else:
                bones, _, _ = gltf2_blender_gather_skins.get_bone_tree(None, blender_object)
                if blender_bone.name in [b.name for b in bones]:
                    obj = blender_object.proxy if blender_object.proxy else blender_object
                    return gltf2_blender_gather_joints.gather_joint(obj, blender_bone, export_settings)

    return gltf2_blender_gather_nodes.gather_node(blender_object,
        blender_object.library.name if blender_object.library else None,
        None, None, export_settings)


def __gather_path(channels: typing.Tuple[bpy.types.FCurve],
                  blender_object: bpy.types.Object,
                  export_settings,
                  bake_bone: typing.Union[str, None],
                  bake_channel: typing.Union[str, None]
                  ) -> str:
    if bake_channel is None:
        # Note: channels has some None items only for SK if some SK are not animated
        target = [c for c in channels if c is not None][0].data_path.split('.')[-1]
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
        return None

    return path
