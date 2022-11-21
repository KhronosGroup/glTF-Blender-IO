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
import typing
import mathutils
from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached
from .gltf2_blender_gather_armature_keyframes import gather_bone_sampled_keyframes
from io_scene_gltf2.blender.exp import gltf2_blender_gather_accessors
from io_scene_gltf2.io.com import gltf2_io_constants
from io_scene_gltf2.io.exp import gltf2_io_binary_data
from io_scene_gltf2.blender.exp.gltf2_blender_gather_tree import VExportNode
from io_scene_gltf2.blender.com import gltf2_blender_math
from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.io.exp.gltf2_io_user_extensions import export_user_extensions

@cached
def gather_bone_bake_animation_sampler(
        armature_uuid: str,
        bone: str,
        channel: str,
        action_name: str,
        node_channel_is_animated: bool,
        export_settings
        ):

    pose_bone = export_settings['vtree'].nodes[armature_uuid].blender_object.pose.bones[bone]

    keyframes = __gather_keyframes(
        armature_uuid,
        bone,
        channel,
        action_name,
        node_channel_is_animated,
        export_settings)

    if keyframes is None:
        # After check, no need to animate this node for this channel
        return None

    # Now we are raw input/output, we need to convert to glTF data
    input, output = __convert_keyframes(armature_uuid, bone, channel, keyframes, export_settings)

    sampler = gltf2_io.AnimationSampler(
        extensions=None,
        extras=None,
        input=input,
        interpolation=__gather_interpolation(export_settings),
        output=output
    )

    export_user_extensions('gather_animation_sampler_hook',
                            export_settings,
                            sampler,
                            export_settings['vtree'].nodes[armature_uuid].blender_object,
                            pose_bone,
                            action_name,
                            node_channel_is_animated)

    return sampler

@cached
def __gather_keyframes(
        armature_uuid: str,
        bone: str,
        channel: str,
        action_name: str,
        node_channel_is_animated: bool,
        export_settings
        ):

    keyframes = gather_bone_sampled_keyframes(
        armature_uuid,
        bone,
        channel,
        action_name,
        node_channel_is_animated,
        export_settings
    )

    if keyframes is None:
        # After check, no need to animation this node
        return None

    return keyframes

def __convert_keyframes(armature_uuid, bone_name, channel, keyframes, export_settings):

    times = [k.seconds for k in keyframes]
    input =  gltf2_blender_gather_accessors.gather_accessor(
        gltf2_io_binary_data.BinaryData.from_list(times, gltf2_io_constants.ComponentType.Float),
        gltf2_io_constants.ComponentType.Float,
        len(times),
        tuple([max(times)]),
        tuple([min(times)]),
        gltf2_io_constants.DataType.Scalar,
        export_settings)

    is_yup = export_settings['gltf_yup']

    bone = export_settings['vtree'].nodes[armature_uuid].blender_object.pose.bones[bone_name]
    target_datapath = "pose.bones['" + bone_name + "']." + channel

    if bone.parent is None:
        # bone at root of armature
        axis_basis_change = mathutils.Matrix.Identity(4)
        if is_yup:
            axis_basis_change = mathutils.Matrix(
                ((1.0, 0.0, 0.0, 0.0),
                    (0.0, 0.0, 1.0, 0.0),
                    (0.0, -1.0, 0.0, 0.0),
                    (0.0, 0.0, 0.0, 1.0)))
        correction_matrix_local = axis_basis_change @ bone.bone.matrix_local
    else:
        # Bone is not at root of armature
        # There are 2 cases :
        parent_uuid = export_settings['vtree'].nodes[export_settings['vtree'].nodes[armature_uuid].bones[bone.name]].parent_uuid
        if parent_uuid is not None and export_settings['vtree'].nodes[parent_uuid].blender_type == VExportNode.BONE:
            # export bone is not at root of armature neither
            blender_bone_parent = export_settings['vtree'].nodes[parent_uuid].blender_bone
            correction_matrix_local = (
                blender_bone_parent.bone.matrix_local.inverted_safe() @
                bone.bone.matrix_local
            )
        else:
            # exported bone (after filter) is at root of armature
            axis_basis_change = mathutils.Matrix.Identity(4)
            if is_yup:
                axis_basis_change = mathutils.Matrix(
                    ((1.0, 0.0, 0.0, 0.0),
                    (0.0, 0.0, 1.0, 0.0),
                    (0.0, -1.0, 0.0, 0.0),
                    (0.0, 0.0, 0.0, 1.0)))
            correction_matrix_local = axis_basis_change
    transform = correction_matrix_local

    values = []
    fps = bpy.context.scene.render.fps
    for keyframe in keyframes:
        # Transform the data and build gltf control points
        value = gltf2_blender_math.transform(keyframe.value, target_datapath, transform, False)
        keyframe_value = gltf2_blender_math.mathutils_to_gltf(value)

        if keyframe.in_tangent is not None:
            # we can directly transform the tangent as it currently is represented by a control point
            in_tangent = gltf2_blender_math.transform(keyframe.in_tangent, target_datapath, transform, False)

            # the tangent in glTF is relative to the keyframe value and uses seconds
            if not isinstance(value, list):
                in_tangent = fps * (in_tangent - value)
            else:
                in_tangent = [fps * (in_tangent[i] - value[i]) for i in range(len(value))]
            keyframe_value = gltf2_blender_math.mathutils_to_gltf(in_tangent) + keyframe_value  # append

        if keyframe.out_tangent is not None:
            # we can directly transform the tangent as it currently is represented by a control point
            out_tangent = gltf2_blender_math.transform(keyframe.out_tangent, target_datapath, transform, False)
            
            # the tangent in glTF is relative to the keyframe value and uses seconds
            if not isinstance(value, list):
                out_tangent = fps * (out_tangent - value)
            else:
                out_tangent = [fps * (out_tangent[i] - value[i]) for i in range(len(value))]
            keyframe_value = keyframe_value + gltf2_blender_math.mathutils_to_gltf(out_tangent)  # append

        values += keyframe_value

     # store the keyframe data in a binary buffer
    component_type = gltf2_io_constants.ComponentType.Float
    data_type = gltf2_io_constants.DataType.vec_type_from_num(len(keyframes[0].value))

    output =  gltf2_io.Accessor(
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

    return input, output

def __gather_interpolation(export_settings):
    # TODO: check if the bone was animated with CONSTANT
    return 'LINEAR'