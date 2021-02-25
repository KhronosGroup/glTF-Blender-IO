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


import typing

import bpy
import mathutils
from io_scene_gltf2.blender.com import gltf2_blender_math
from io_scene_gltf2.blender.com.gltf2_blender_data_path import get_target_property_name, get_target_object_path
from io_scene_gltf2.blender.exp import gltf2_blender_gather_animation_sampler_keyframes
from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached
from io_scene_gltf2.blender.exp import gltf2_blender_gather_accessors
from io_scene_gltf2.blender.exp import gltf2_blender_get
from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.io.com import gltf2_io_constants
from io_scene_gltf2.io.exp import gltf2_io_binary_data
from . import gltf2_blender_export_keys
from io_scene_gltf2.io.exp.gltf2_io_user_extensions import export_user_extensions


@cached
def gather_animation_sampler(channels: typing.Tuple[bpy.types.FCurve],
                             blender_object: bpy.types.Object,
                             bake_bone: typing.Union[str, None],
                             bake_channel: typing.Union[str, None],
                             bake_range_start,
                             bake_range_end,
                             action_name: str,
                             driver_obj,
                             export_settings
                             ) -> gltf2_io.AnimationSampler:

    blender_object_if_armature = blender_object if blender_object.type == "ARMATURE" else None
    if blender_object_if_armature is not None and driver_obj is None:
        if bake_bone is None:
            pose_bone_if_armature = gltf2_blender_get.get_object_from_datapath(blender_object_if_armature,
                                                                               channels[0].data_path)
        else:
            pose_bone_if_armature = blender_object.pose.bones[bake_bone]
    else:
        pose_bone_if_armature = None
    non_keyed_values = __gather_non_keyed_values(channels, blender_object,
                                                 blender_object_if_armature, pose_bone_if_armature,
                                                 bake_channel,
                                                 driver_obj,
                                                 export_settings)
    if blender_object.parent is not None:
        matrix_parent_inverse = blender_object.matrix_parent_inverse.copy().freeze()
    else:
        matrix_parent_inverse = mathutils.Matrix.Identity(4).freeze()

    sampler = gltf2_io.AnimationSampler(
        extensions=__gather_extensions(channels, blender_object_if_armature, export_settings, bake_bone, bake_channel),
        extras=__gather_extras(channels, blender_object_if_armature, export_settings, bake_bone, bake_channel),
        input=__gather_input(channels, blender_object_if_armature, non_keyed_values,
                             bake_bone, bake_channel, bake_range_start, bake_range_end, action_name, driver_obj, export_settings),
        interpolation=__gather_interpolation(channels, blender_object_if_armature, export_settings, bake_bone, bake_channel),
        output=__gather_output(channels,
                               matrix_parent_inverse,
                               blender_object_if_armature,
                               non_keyed_values,
                               bake_bone,
                               bake_channel,
                               bake_range_start,
                               bake_range_end,
                               action_name,
                               driver_obj,
                               export_settings)
    )

    export_user_extensions('gather_animation_sampler_hook',
                            export_settings,
                            sampler,
                            channels,
                            blender_object,
                            bake_bone,
                            bake_channel,
                            bake_range_start,
                            bake_range_end,
                            action_name)

    return sampler

def __gather_non_keyed_values(channels: typing.Tuple[bpy.types.FCurve],
                              blender_object: bpy.types.Object,
                              blender_object_if_armature: typing.Optional[bpy.types.Object],
                              pose_bone_if_armature: typing.Optional[bpy.types.PoseBone],
                              bake_channel: typing.Union[str, None],
                              driver_obj,
                              export_settings
                              ) ->  typing.Tuple[typing.Optional[float]]:

    non_keyed_values = []

    obj = blender_object if driver_obj is None else driver_obj

    # Note: channels has some None items only for SK if some SK are not animated
    if None not in channels:
        # classic case for object TRS or bone TRS
        # Or if all morph target are animated

        if driver_obj is not None:
            # driver of SK
            return tuple([None] * len(channels))

        if bake_channel is None:
            target = channels[0].data_path.split('.')[-1]
        else:
            target = bake_channel
        if target == "value":
            # All morph targets are animated
            return tuple([None] * len(channels))

        indices = [c.array_index for c in channels]
        indices.sort()
        length = {
            "delta_location": 3,
            "delta_rotation_euler": 3,
            "location": 3,
            "rotation_axis_angle": 4,
            "rotation_euler": 3,
            "rotation_quaternion": 4,
            "scale": 3,
            "value": len(channels)
        }.get(target)

        if length is None:
            # This is not a known target
            return ()

        for i in range(0, length):
            if bake_channel is not None:
                non_keyed_values.append({
                    "delta_location" : obj.delta_location,
                    "delta_rotation_euler" : obj.delta_rotation_euler,
                    "location" : obj.location,
                    "rotation_axis_angle" : obj.rotation_axis_angle,
                    "rotation_euler" : obj.rotation_euler,
                    "rotation_quaternion" : obj.rotation_quaternion,
                    "scale" : obj.scale
                }[target][i])
            elif i in indices:
                non_keyed_values.append(None)
            else:
                if blender_object_if_armature is None:
                    non_keyed_values.append({
                        "delta_location" : obj.delta_location,
                        "delta_rotation_euler" : obj.delta_rotation_euler,
                        "location" : obj.location,
                        "rotation_axis_angle" : obj.rotation_axis_angle,
                        "rotation_euler" : obj.rotation_euler,
                        "rotation_quaternion" : obj.rotation_quaternion,
                        "scale" : obj.scale
                    }[target][i])
                else:
                     # TODO, this is not working if the action is not active (NLA case for example)
                     trans, rot, scale = pose_bone_if_armature.matrix_basis.decompose()
                     non_keyed_values.append({
                        "location": trans,
                        "rotation_axis_angle": rot,
                        "rotation_euler": rot,
                        "rotation_quaternion": rot,
                        "scale": scale
                        }[target][i])

        return tuple(non_keyed_values)

    else:
        # We are in case of morph target, where all targets are not animated
        # So channels has some None items
        first_channel = [c for c in channels if c is not None][0]
        object_path = get_target_object_path(first_channel.data_path)
        if object_path:
            shapekeys_idx = {}
            cpt_sk = 0
            for sk in obj.data.shape_keys.key_blocks:
                if sk == sk.relative_key:
                    continue
                if sk.mute is True:
                    continue
                shapekeys_idx[cpt_sk] = sk.name
                cpt_sk += 1

        for idx_c, channel in enumerate(channels):
            if channel is None:
                non_keyed_values.append(obj.data.shape_keys.key_blocks[shapekeys_idx[idx_c]].value)
            else:
                non_keyed_values.append(None)

        return tuple(non_keyed_values)

def __gather_extensions(channels: typing.Tuple[bpy.types.FCurve],
                        blender_object_if_armature: typing.Optional[bpy.types.Object],
                        export_settings,
                        bake_bone: typing.Union[str, None],
                        bake_channel: typing.Union[str, None]
                        ) -> typing.Any:
    return None


def __gather_extras(channels: typing.Tuple[bpy.types.FCurve],
                    blender_object_if_armature: typing.Optional[bpy.types.Object],
                    export_settings,
                    bake_bone: typing.Union[str, None],
                    bake_channel: typing.Union[str, None]
                    ) -> typing.Any:
    return None


@cached
def __gather_input(channels: typing.Tuple[bpy.types.FCurve],
                   blender_object_if_armature: typing.Optional[bpy.types.Object],
                   non_keyed_values: typing.Tuple[typing.Optional[float]],
                   bake_bone: typing.Union[str, None],
                   bake_channel: typing.Union[str, None],
                   bake_range_start,
                   bake_range_end,
                   action_name,
                   driver_obj,
                   export_settings
                   ) -> gltf2_io.Accessor:
    """Gather the key time codes."""
    keyframes = gltf2_blender_gather_animation_sampler_keyframes.gather_keyframes(blender_object_if_armature,
                                                                                  channels,
                                                                                  non_keyed_values,
                                                                                  bake_bone,
                                                                                  bake_channel,
                                                                                  bake_range_start,
                                                                                  bake_range_end,
                                                                                  action_name,
                                                                                  driver_obj,
                                                                                  export_settings)
    times = [k.seconds for k in keyframes]

    return gltf2_blender_gather_accessors.gather_accessor(
        gltf2_io_binary_data.BinaryData.from_list(times, gltf2_io_constants.ComponentType.Float),
        gltf2_io_constants.ComponentType.Float,
        len(times),
        tuple([max(times)]),
        tuple([min(times)]),
        gltf2_io_constants.DataType.Scalar,
        export_settings
    )


def __gather_interpolation(channels: typing.Tuple[bpy.types.FCurve],
                           blender_object_if_armature: typing.Optional[bpy.types.Object],
                           export_settings,
                           bake_bone: typing.Union[str, None],
                           bake_channel: typing.Union[str, None]
                           ) -> str:

    # Note: channels has some None items only for SK if some SK are not animated

    if gltf2_blender_gather_animation_sampler_keyframes.needs_baking(blender_object_if_armature,
                                                                     channels,
                                                                     export_settings):
        if bake_bone is not None:
            # TODO: check if the bone was animated with CONSTANT
            return 'LINEAR'
        else:
            max_keyframes = max([len(ch.keyframe_points) for ch in channels if ch is not None])
            # If only single keyframe revert to STEP
            if max_keyframes < 2:
                return 'STEP'

            # If all keyframes are CONSTANT, we can use STEP.
            if all(all(k.interpolation == 'CONSTANT' for k in c.keyframe_points) for c in channels if c is not None):
                return 'STEP'

            # Otherwise, sampled keyframes use LINEAR interpolation.
            return 'LINEAR'

    # Non-sampled keyframes implies that all keys are of the same type, and that the
    # type is supported by glTF (because we checked in needs_baking).
    blender_keyframe = [c for c in channels if c is not None][0].keyframe_points[0]

    # Select the interpolation method.
    return {
        "BEZIER": "CUBICSPLINE",
        "LINEAR": "LINEAR",
        "CONSTANT": "STEP"
    }[blender_keyframe.interpolation]


@cached
def __gather_output(channels: typing.Tuple[bpy.types.FCurve],
                    parent_inverse,
                    blender_object_if_armature: typing.Optional[bpy.types.Object],
                    non_keyed_values: typing.Tuple[typing.Optional[float]],
                    bake_bone: typing.Union[str, None],
                    bake_channel: typing.Union[str, None],
                    bake_range_start,
                    bake_range_end,
                    action_name,
                    driver_obj,
                    export_settings
                    ) -> gltf2_io.Accessor:
    """Gather the data of the keyframes."""
    keyframes = gltf2_blender_gather_animation_sampler_keyframes.gather_keyframes(blender_object_if_armature,
                                                                                  channels,
                                                                                  non_keyed_values,
                                                                                  bake_bone,
                                                                                  bake_channel,
                                                                                  bake_range_start,
                                                                                  bake_range_end,
                                                                                  action_name,
                                                                                  driver_obj,
                                                                                  export_settings)
    if bake_bone is not None:
        target_datapath = "pose.bones['" + bake_bone + "']." + bake_channel
    else:
        target_datapath = [c for c in channels if c is not None][0].data_path

    is_yup = export_settings[gltf2_blender_export_keys.YUP]

    # bone animations need to be handled differently as they are in a different coordinate system
    if bake_bone is None:
        object_path = get_target_object_path(target_datapath)
    else:
        object_path = None
    is_armature_animation = bake_bone is not None or (blender_object_if_armature is not None and object_path != "")

    if is_armature_animation:
        if bake_bone is None:
            bone = gltf2_blender_get.get_object_from_datapath(blender_object_if_armature, object_path)
        else:
            bone = blender_object_if_armature.pose.bones[bake_bone]
        if isinstance(bone, bpy.types.PoseBone):
            if bone.parent is None:
                axis_basis_change = mathutils.Matrix.Identity(4)
                if export_settings[gltf2_blender_export_keys.YUP]:
                    axis_basis_change = mathutils.Matrix(
                        ((1.0, 0.0, 0.0, 0.0),
                         (0.0, 0.0, 1.0, 0.0),
                         (0.0, -1.0, 0.0, 0.0),
                         (0.0, 0.0, 0.0, 1.0)))
                correction_matrix_local = axis_basis_change @ bone.bone.matrix_local
            else:
                correction_matrix_local = (
                    bone.parent.bone.matrix_local.inverted() @
                    bone.bone.matrix_local
                )

            transform = correction_matrix_local
        else:
            transform = mathutils.Matrix.Identity(4)
    else:
        transform = parent_inverse

    values = []
    for keyframe in keyframes:
        # Transform the data and build gltf control points
        value = gltf2_blender_math.transform(keyframe.value, target_datapath, transform)
        if is_yup and not is_armature_animation:
            value = gltf2_blender_math.swizzle_yup(value, target_datapath)
        keyframe_value = gltf2_blender_math.mathutils_to_gltf(value)

        if keyframe.in_tangent is not None:
            # we can directly transform the tangent as it currently is represented by a control point
            in_tangent = gltf2_blender_math.transform(keyframe.in_tangent, target_datapath, transform)
            if is_yup and blender_object_if_armature is None:
                in_tangent = gltf2_blender_math.swizzle_yup(in_tangent, target_datapath)
            # the tangent in glTF is relative to the keyframe value
            if not isinstance(value, list):
                in_tangent = value - in_tangent
            else:
                in_tangent = [value[i] - in_tangent[i] for i in range(len(value))]
            keyframe_value = gltf2_blender_math.mathutils_to_gltf(in_tangent) + keyframe_value  # append

        if keyframe.out_tangent is not None:
            # we can directly transform the tangent as it currently is represented by a control point
            out_tangent = gltf2_blender_math.transform(keyframe.out_tangent, target_datapath, transform)
            if is_yup and blender_object_if_armature is None:
                out_tangent = gltf2_blender_math.swizzle_yup(out_tangent, target_datapath)
            # the tangent in glTF is relative to the keyframe value
            if not isinstance(value, list):
                out_tangent = value - out_tangent
            else:
                out_tangent = [value[i] - out_tangent[i] for i in range(len(value))]
            keyframe_value = keyframe_value + gltf2_blender_math.mathutils_to_gltf(out_tangent)  # append

        values += keyframe_value

    # store the keyframe data in a binary buffer
    component_type = gltf2_io_constants.ComponentType.Float
    if get_target_property_name(target_datapath) == "value":
        # channels with 'weight' targets must have scalar accessors
        data_type = gltf2_io_constants.DataType.Scalar
    else:
        data_type = gltf2_io_constants.DataType.vec_type_from_num(len(keyframes[0].value))

    return gltf2_io.Accessor(
        buffer_view=gltf2_io_binary_data.BinaryData.from_list(values, component_type),
        byte_offset=None,
        component_type=component_type,
        count=len(values) // gltf2_io_constants.DataType.num_elements(data_type),
        extensions=None,
        extras=None,
        max=None,
        min=None,
        name=None,
        normalized=None,
        sparse=None,
        type=data_type
    )
