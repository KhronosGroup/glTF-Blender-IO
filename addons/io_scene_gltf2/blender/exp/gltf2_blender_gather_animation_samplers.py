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
import mathutils
import typing
import math

from . import gltf2_blender_export_keys
from mathutils import Matrix
from io_scene_gltf2.blender.com.gltf2_blender_data_path import get_target_property_name, get_target_object_path
from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached
from io_scene_gltf2.io.exp import gltf2_io_binary_data
from io_scene_gltf2.io.com import gltf2_io_constants
from io_scene_gltf2.blender.com import gltf2_blender_math
from io_scene_gltf2.blender.exp import gltf2_blender_gather_animation_sampler_keyframes


@cached
def gather_animation_sampler(channels: typing.Tuple[bpy.types.FCurve],
                             blender_object: bpy.types.Object,
                             export_settings
                             ) -> gltf2_io.AnimationSampler:
    return gltf2_io.AnimationSampler(
        extensions=__gather_extensions(channels, blender_object, export_settings),
        extras=__gather_extras(channels, blender_object, export_settings),
        input=__gather_input(channels, blender_object, export_settings),
        interpolation=__gather_interpolation(channels, blender_object, export_settings),
        output=__gather_output(channels, blender_object, export_settings)
    )


def __gather_extensions(channels: typing.Tuple[bpy.types.FCurve],
                        blender_object: bpy.types.Object,
                        export_settings
                        ) -> typing.Any:
    return None


def __gather_extras(channels: typing.Tuple[bpy.types.FCurve],
                    blender_object: bpy.types.Object,
                    export_settings
                    ) -> typing.Any:
    return None


def __gather_input(channels: typing.Tuple[bpy.types.FCurve],
                   blender_object: bpy.types.Object,
                   export_settings
                   ) -> gltf2_io.Accessor:
    """Gather the key time codes."""
    keyframes = gltf2_blender_gather_animation_sampler_keyframes.gather_keyframes(channels, export_settings)
    times = [k.seconds for k in keyframes]

    return gltf2_io.Accessor(
        buffer_view=gltf2_io_binary_data.BinaryData.from_list(times, gltf2_io_constants.ComponentType.Float),
        byte_offset=None,
        component_type=gltf2_io_constants.ComponentType.Float,
        count=len(times),
        extensions=None,
        extras=None,
        max=[max(times)],
        min=[min(times)],
        name=None,
        normalized=None,
        sparse=None,
        type=gltf2_io_constants.DataType.Scalar
    )


def __gather_interpolation(channels: typing.Tuple[bpy.types.FCurve],
                           blender_object: bpy.types.Object,
                           export_settings
                           ) -> str:
    if gltf2_blender_gather_animation_sampler_keyframes.needs_baking(channels, export_settings):
        return 'STEP'

    blender_keyframe = channels[0].keyframe_points[0]

    # Select the interpolation method. Any unsupported method will fallback to STEP
    return {
        "BEZIER": "CUBICSPLINE",
        "LINEAR": "LINEAR",
        "CONSTANT": "STEP"
    }[blender_keyframe.interpolation]


def __gather_output(channels: typing.Tuple[bpy.types.FCurve],
                    blender_object: bpy.types.Object,
                    export_settings
                    ) -> gltf2_io.Accessor:
    """Gather the data of the keyframes."""
    keyframes = gltf2_blender_gather_animation_sampler_keyframes.gather_keyframes(channels, export_settings)

    target_datapath = channels[0].data_path

    transform = Matrix.Identity(4)

    if blender_object.type == "ARMATURE":
        bone = blender_object.path_resolve(get_target_object_path(target_datapath))
        if isinstance(bone, bpy.types.PoseBone):
            transform = bone.bone.matrix_local
            if bone.parent is not None:
                parent_transform = bone.parent.bone.matrix_local
                transform = gltf2_blender_math.multiply(parent_transform.inverted(), transform)
                # if not export_settings[gltf2_blender_export_keys.YUP]:
                #     transform = gltf2_blender_math.multiply(gltf2_blender_math.to_zup(), transform)
            else:
                # only apply the y-up conversion to root bones, as child bones already are in the y-up space
                if export_settings[gltf2_blender_export_keys.YUP]:
                    transform = gltf2_blender_math.multiply(gltf2_blender_math.to_yup(), transform)

    values = []
    for keyframe in keyframes:
        # Transform the data and extract
        value = gltf2_blender_math.transform(keyframe.value, target_datapath, transform)
        if export_settings[gltf2_blender_export_keys.YUP] and not blender_object.type == "ARMATURE":
            value = gltf2_blender_math.swizzle_yup(value, target_datapath)
        keyframe_value = gltf2_blender_math.mathutils_to_gltf(value)
        if keyframe.in_tangent is not None:
            in_tangent = gltf2_blender_math.transform(keyframe.in_tangent, target_datapath, transform)
            if export_settings[gltf2_blender_export_keys.YUP] and not blender_object.type == "ARMATURE":
                in_tangent = gltf2_blender_math.swizzle_yup(in_tangent, target_datapath)
            keyframe_value = gltf2_blender_math.mathutils_to_gltf(in_tangent) + keyframe_value
        if keyframe.out_tangent is not None:
            out_tangent = gltf2_blender_math.transform(keyframe.out_tangent, target_datapath, transform)
            if export_settings[gltf2_blender_export_keys.YUP] and not blender_object.type == "ARMATURE":
                out_tangent = gltf2_blender_math.swizzle_yup(out_tangent, target_datapath)
            keyframe_value = keyframe_value + gltf2_blender_math.mathutils_to_gltf(out_tangent)
        values += keyframe_value

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
