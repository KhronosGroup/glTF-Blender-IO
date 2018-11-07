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

#
# Imports
#

import bpy
from . import export_keys
from . import gltf2_blender_extract
from mathutils import Matrix, Quaternion, Euler


#
# Globals
#

JOINT_NODE = 'JOINT'

NEEDS_CONVERSION = 'CONVERSION_NEEDED'
CUBIC_INTERPOLATION = 'CUBICSPLINE'
LINEAR_INTERPOLATION = 'LINEAR'
STEP_INTERPOLATION = 'STEP'
BEZIER_INTERPOLATION = 'BEZIER'
CONSTANT_INTERPOLATION = 'CONSTANT'


#
# Functions
#

def animate_get_interpolation(export_settings, blender_fcurve_list):
    """
    Retrieve the glTF interpolation, depending on a fcurve list.

    Blender allows mixing and more variations of interpolations.
    In such a case, a conversion is needed.
    """
    if export_settings[export_keys.FORCE_SAMPLING]:
        return NEEDS_CONVERSION

    #

    interpolation = None

    keyframe_count = None

    for blender_fcurve in blender_fcurve_list:
        if blender_fcurve is None:
            continue

        #

        current_keyframe_count = len(blender_fcurve.keyframe_points)

        if keyframe_count is None:
            keyframe_count = current_keyframe_count

        if current_keyframe_count > 0 > blender_fcurve.keyframe_points[0].co[0]:
            return NEEDS_CONVERSION

        if keyframe_count != current_keyframe_count:
            return NEEDS_CONVERSION

        #

        for blender_keyframe in blender_fcurve.keyframe_points:
            is_bezier = blender_keyframe.interpolation == BEZIER_INTERPOLATION
            is_linear = blender_keyframe.interpolation == LINEAR_INTERPOLATION
            is_constant = blender_keyframe.interpolation == CONSTANT_INTERPOLATION

            if interpolation is None:
                if is_bezier:
                    interpolation = CUBIC_INTERPOLATION
                elif is_linear:
                    interpolation = LINEAR_INTERPOLATION
                elif is_constant:
                    interpolation = STEP_INTERPOLATION
                else:
                    interpolation = NEEDS_CONVERSION
                    return interpolation
            else:
                if is_bezier and interpolation != CUBIC_INTERPOLATION:
                    interpolation = NEEDS_CONVERSION
                    return interpolation
                elif is_linear and interpolation != LINEAR_INTERPOLATION:
                    interpolation = NEEDS_CONVERSION
                    return interpolation
                elif is_constant and interpolation != STEP_INTERPOLATION:
                    interpolation = NEEDS_CONVERSION
                    return interpolation
                elif not is_bezier and not is_linear and not is_constant:
                    interpolation = NEEDS_CONVERSION
                    return interpolation

    if interpolation is None:
        interpolation = NEEDS_CONVERSION

    return interpolation


def animate_convert_rotation_axis_angle(axis_angle):
    """Convert an axis angle to a quaternion rotation."""
    q = Quaternion((axis_angle[1], axis_angle[2], axis_angle[3]), axis_angle[0])

    return [q.x, q.y, q.z, q.w]


def animate_convert_rotation_euler(euler, rotation_mode):
    """Convert an euler angle to a quaternion rotation."""
    rotation = Euler((euler[0], euler[1], euler[2]), rotation_mode).to_quaternion()

    return [rotation.x, rotation.y, rotation.z, rotation.w]


def animate_convert_keys(key_list):
    """Convert Blender key frames to glTF time keys depending on the applied frames per second."""
    times = []

    for key in key_list:
        times.append(key / bpy.context.scene.render.fps)

    return times


def animate_gather_keys(export_settings, fcurve_list, interpolation):
    """
    Merge and sort several key frames to one set.

    If an interpolation conversion is needed, the sample key frames are created as well.
    """
    keys = []

    frame_start = bpy.context.scene.frame_start
    frame_end = bpy.context.scene.frame_end

    if interpolation == NEEDS_CONVERSION:
        start = None
        end = None

        for blender_fcurve in fcurve_list:
            if blender_fcurve is None:
                continue

            if start is None:
                start = blender_fcurve.range()[0]
            else:
                start = min(start, blender_fcurve.range()[0])

            if end is None:
                end = blender_fcurve.range()[1]
            else:
                end = max(end, blender_fcurve.range()[1])

            #

            add_epsilon_keyframe = False
            for blender_keyframe in blender_fcurve.keyframe_points:
                if add_epsilon_keyframe:
                    key = blender_keyframe.co[0] - 0.001

                    if key not in keys:
                        keys.append(key)

                    add_epsilon_keyframe = False

                if blender_keyframe.interpolation == CONSTANT_INTERPOLATION:
                    add_epsilon_keyframe = True

            if add_epsilon_keyframe:
                key = end - 0.001

                if key not in keys:
                    keys.append(key)

        key = start
        while key <= end:
            if not export_settings[export_keys.FRAME_RANGE] or (frame_start <= key <= frame_end):
                keys.append(key)
            key += export_settings[export_keys.FRAME_STEP]

        keys.sort()

    else:
        for blender_fcurve in fcurve_list:
            if blender_fcurve is None:
                continue

            for blender_keyframe in blender_fcurve.keyframe_points:
                key = blender_keyframe.co[0]
                if not export_settings[export_keys.FRAME_RANGE] or (frame_start <= key <= frame_end):
                    if key not in keys:
                        keys.append(key)

        keys.sort()

    return keys


def animate_location(export_settings, location, interpolation, node_type, node_name, action_name, matrix_correction,
                     matrix_basis):
    """Calculate/gather the key value pairs for location transformations."""
    joint_cache = export_settings[export_keys.JOINT_CACHE][action_name]
    if not joint_cache.get(node_name):
        joint_cache[node_name] = {}

    keys = animate_gather_keys(export_settings, location, interpolation)

    times = animate_convert_keys(keys)

    result = {}
    result_in_tangent = {}
    result_out_tangent = {}

    keyframe_index = 0
    for timeIndex, time in enumerate(times):
        translation = [0.0, 0.0, 0.0]
        in_tangent = [0.0, 0.0, 0.0]
        out_tangent = [0.0, 0.0, 0.0]

        if node_type == JOINT_NODE:
            if joint_cache[node_name].get(keys[keyframe_index]):
                translation, tmp_rotation, tmp_scale = joint_cache[node_name][keys[keyframe_index]]
            else:
                bpy.context.scene.frame_set(keys[keyframe_index])

                matrix = matrix_correction * matrix_basis

                translation, tmp_rotation, tmp_scale = matrix.decompose()

                joint_cache[node_name][keys[keyframe_index]] = [translation, tmp_rotation, tmp_scale]
        else:
            channel_index = 0
            for blender_fcurve in location:

                if blender_fcurve is not None:

                    if interpolation == CUBIC_INTERPOLATION:
                        blender_key_frame = blender_fcurve.keyframe_points[keyframe_index]

                        translation[channel_index] = blender_key_frame.co[1]

                        if timeIndex == 0:
                            in_tangent_value = 0.0
                        else:
                            factor = 3.0 / (time - times[timeIndex - 1])
                            in_tangent_value = (blender_key_frame.co[1] - blender_key_frame.handle_left[1]) * factor

                        if timeIndex == len(times) - 1:
                            out_tangent_value = 0.0
                        else:
                            factor = 3.0 / (times[timeIndex + 1] - time)
                            out_tangent_value = (blender_key_frame.handle_right[1] - blender_key_frame.co[1]) * factor

                        in_tangent[channel_index] = in_tangent_value
                        out_tangent[channel_index] = out_tangent_value
                    else:
                        value = blender_fcurve.evaluate(keys[keyframe_index])

                        translation[channel_index] = value

                channel_index += 1

            # handle parent inverse
            matrix = Matrix.Translation(translation)
            matrix = matrix_correction * matrix
            translation = matrix.to_translation()

            translation = gltf2_blender_extract.convert_swizzle_location(translation, export_settings)
            in_tangent = gltf2_blender_extract.convert_swizzle_location(in_tangent, export_settings)
            out_tangent = gltf2_blender_extract.convert_swizzle_location(out_tangent, export_settings)

        result[time] = translation
        result_in_tangent[time] = in_tangent
        result_out_tangent[time] = out_tangent

        keyframe_index += 1

    return result, result_in_tangent, result_out_tangent


def animate_rotation_axis_angle(export_settings, rotation_axis_angle, interpolation, node_type, node_name, action_name,
                                matrix_correction, matrix_basis):
    """Calculate/gather the key value pairs for axis angle transformations."""
    joint_cache = export_settings[export_keys.JOINT_CACHE][action_name]
    if not joint_cache.get(node_name):
        joint_cache[node_name] = {}

    keys = animate_gather_keys(export_settings, rotation_axis_angle, interpolation)

    times = animate_convert_keys(keys)

    result = {}

    keyframe_index = 0
    for time in times:
        axis_angle_rotation = [1.0, 0.0, 0.0, 0.0]

        if node_type == JOINT_NODE:
            if joint_cache[node_name].get(keys[keyframe_index]):
                tmp_location, rotation, tmp_scale = joint_cache[node_name][keys[keyframe_index]]
            else:
                bpy.context.scene.frame_set(keys[keyframe_index])

                matrix = matrix_correction * matrix_basis

                tmp_location, rotation, tmp_scale = matrix.decompose()

                joint_cache[node_name][keys[keyframe_index]] = [tmp_location, rotation, tmp_scale]
        else:
            channel_index = 0
            for blender_fcurve in rotation_axis_angle:
                if blender_fcurve is not None:
                    value = blender_fcurve.evaluate(keys[keyframe_index])

                    axis_angle_rotation[channel_index] = value

                channel_index += 1

            rotation = animate_convert_rotation_axis_angle(axis_angle_rotation)

            # handle parent inverse
            rotation = Quaternion((rotation[3], rotation[0], rotation[1], rotation[2]))
            matrix = rotation.to_matrix().to_4x4()
            matrix = matrix_correction * matrix
            rotation = matrix.to_quaternion()

            # Bring back to internal Quaternion notation.
            rotation = gltf2_blender_extract.convert_swizzle_rotation(
                [rotation[0], rotation[1], rotation[2], rotation[3]], export_settings)

        # Bring back to glTF Quaternion notation.
        rotation = [rotation[1], rotation[2], rotation[3], rotation[0]]

        result[time] = rotation

        keyframe_index += 1

    return result


def animate_rotation_euler(export_settings, rotation_euler, rotation_mode, interpolation, node_type, node_name,
                           action_name, matrix_correction, matrix_basis):
    """Calculate/gather the key value pairs for euler angle transformations."""
    joint_cache = export_settings[export_keys.JOINT_CACHE][action_name]
    if not joint_cache.get(node_name):
        joint_cache[node_name] = {}

    keys = animate_gather_keys(export_settings, rotation_euler, interpolation)

    times = animate_convert_keys(keys)

    result = {}

    keyframe_index = 0
    for time in times:
        euler_rotation = [0.0, 0.0, 0.0]

        if node_type == JOINT_NODE:
            if joint_cache[node_name].get(keys[keyframe_index]):
                tmp_location, rotation, tmp_scale = joint_cache[node_name][keys[keyframe_index]]
            else:
                bpy.context.scene.frame_set(keys[keyframe_index])

                matrix = matrix_correction * matrix_basis

                tmp_location, rotation, tmp_scale = matrix.decompose()

                joint_cache[node_name][keys[keyframe_index]] = [tmp_location, rotation, tmp_scale]
        else:
            channel_index = 0
            for blender_fcurve in rotation_euler:
                if blender_fcurve is not None:
                    value = blender_fcurve.evaluate(keys[keyframe_index])

                    euler_rotation[channel_index] = value

                channel_index += 1

            rotation = animate_convert_rotation_euler(euler_rotation, rotation_mode)

            # handle parent inverse
            rotation = Quaternion((rotation[3], rotation[0], rotation[1], rotation[2]))
            matrix = rotation.to_matrix().to_4x4()
            matrix = matrix_correction * matrix
            rotation = matrix.to_quaternion()

            # Bring back to internal Quaternion notation.
            rotation = gltf2_blender_extract.convert_swizzle_rotation(
                [rotation[0], rotation[1], rotation[2], rotation[3]], export_settings)

        # Bring back to glTF Quaternion notation.
        rotation = [rotation[1], rotation[2], rotation[3], rotation[0]]

        result[time] = rotation

        keyframe_index += 1

    return result


def animate_rotation_quaternion(export_settings, rotation_quaternion, interpolation, node_type, node_name, action_name,
                                matrix_correction, matrix_basis):
    """Calculate/gather the key value pairs for quaternion transformations."""
    joint_cache = export_settings[export_keys.JOINT_CACHE][action_name]
    if not joint_cache.get(node_name):
        joint_cache[node_name] = {}

    keys = animate_gather_keys(export_settings, rotation_quaternion, interpolation)

    times = animate_convert_keys(keys)

    result = {}
    result_in_tangent = {}
    result_out_tangent = {}

    keyframe_index = 0
    for timeIndex, time in enumerate(times):
        rotation = [1.0, 0.0, 0.0, 0.0]
        in_tangent = [1.0, 0.0, 0.0, 0.0]
        out_tangent = [1.0, 0.0, 0.0, 0.0]

        if node_type == JOINT_NODE:
            if joint_cache[node_name].get(keys[keyframe_index]):
                tmp_location, rotation, tmp_scale = joint_cache[node_name][keys[keyframe_index]]
            else:
                bpy.context.scene.frame_set(keys[keyframe_index])

                matrix = matrix_correction * matrix_basis

                tmp_location, rotation, tmp_scale = matrix.decompose()

                joint_cache[node_name][keys[keyframe_index]] = [tmp_location, rotation, tmp_scale]
        else:
            channel_index = 0
            for blender_fcurve in rotation_quaternion:

                if blender_fcurve is not None:
                    if interpolation == CUBIC_INTERPOLATION:
                        blender_key_frame = blender_fcurve.keyframe_points[keyframe_index]

                        rotation[channel_index] = blender_key_frame.co[1]

                        if timeIndex == 0:
                            in_tangent_value = 0.0
                        else:
                            factor = 3.0 / (time - times[timeIndex - 1])
                            in_tangent_value = (blender_key_frame.co[1] - blender_key_frame.handle_left[1]) * factor

                        if timeIndex == len(times) - 1:
                            out_tangent_value = 0.0
                        else:
                            factor = 3.0 / (times[timeIndex + 1] - time)
                            out_tangent_value = (blender_key_frame.handle_right[1] - blender_key_frame.co[1]) * factor

                        in_tangent[channel_index] = in_tangent_value
                        out_tangent[channel_index] = out_tangent_value
                    else:
                        value = blender_fcurve.evaluate(keys[keyframe_index])

                        rotation[channel_index] = value

                channel_index += 1

            rotation = Quaternion((rotation[0], rotation[1], rotation[2], rotation[3]))
            in_tangent = gltf2_blender_extract.convert_swizzle_rotation(in_tangent, export_settings)
            out_tangent = gltf2_blender_extract.convert_swizzle_rotation(out_tangent, export_settings)

            # handle parent inverse
            matrix = rotation.to_matrix().to_4x4()
            matrix = matrix_correction * matrix
            rotation = matrix.to_quaternion()

            # Bring back to internal Quaternion notation.
            rotation = gltf2_blender_extract.convert_swizzle_rotation(
                [rotation[0], rotation[1], rotation[2], rotation[3]], export_settings)

        # Bring to glTF Quaternion notation.
        rotation = [rotation[1], rotation[2], rotation[3], rotation[0]]
        in_tangent = [in_tangent[1], in_tangent[2], in_tangent[3], in_tangent[0]]
        out_tangent = [out_tangent[1], out_tangent[2], out_tangent[3], out_tangent[0]]

        result[time] = rotation
        result_in_tangent[time] = in_tangent
        result_out_tangent[time] = out_tangent

        keyframe_index += 1

    return result, result_in_tangent, result_out_tangent


def animate_scale(export_settings, scale, interpolation, node_type, node_name, action_name, matrix_correction,
                  matrix_basis):
    """Calculate/gather the key value pairs for scale transformations."""
    joint_cache = export_settings[export_keys.JOINT_CACHE][action_name]
    if not joint_cache.get(node_name):
        joint_cache[node_name] = {}

    keys = animate_gather_keys(export_settings, scale, interpolation)

    times = animate_convert_keys(keys)

    result = {}
    result_in_tangent = {}
    result_out_tangent = {}

    keyframe_index = 0
    for timeIndex, time in enumerate(times):
        scale_data = [1.0, 1.0, 1.0]
        in_tangent = [0.0, 0.0, 0.0]
        out_tangent = [0.0, 0.0, 0.0]

        if node_type == JOINT_NODE:
            if joint_cache[node_name].get(keys[keyframe_index]):
                tmp_location, tmp_rotation, scale_data = joint_cache[node_name][keys[keyframe_index]]
            else:
                bpy.context.scene.frame_set(keys[keyframe_index])

                matrix = matrix_correction * matrix_basis

                tmp_location, tmp_rotation, scale_data = matrix.decompose()

                joint_cache[node_name][keys[keyframe_index]] = [tmp_location, tmp_rotation, scale_data]
        else:
            channel_index = 0
            for blender_fcurve in scale:

                if blender_fcurve is not None:
                    if interpolation == CUBIC_INTERPOLATION:
                        blender_key_frame = blender_fcurve.keyframe_points[keyframe_index]

                        scale_data[channel_index] = blender_key_frame.co[1]

                        if timeIndex == 0:
                            in_tangent_value = 0.0
                        else:
                            factor = 3.0 / (time - times[timeIndex - 1])
                            in_tangent_value = (blender_key_frame.co[1] - blender_key_frame.handle_left[1]) * factor

                        if timeIndex == len(times) - 1:
                            out_tangent_value = 0.0
                        else:
                            factor = 3.0 / (times[timeIndex + 1] - time)
                            out_tangent_value = (blender_key_frame.handle_right[1] - blender_key_frame.co[1]) * factor

                        in_tangent[channel_index] = in_tangent_value
                        out_tangent[channel_index] = out_tangent_value
                    else:
                        value = blender_fcurve.evaluate(keys[keyframe_index])

                        scale_data[channel_index] = value

                channel_index += 1

            scale_data = gltf2_blender_extract.convert_swizzle_scale(scale_data, export_settings)
            in_tangent = gltf2_blender_extract.convert_swizzle_scale(in_tangent, export_settings)
            out_tangent = gltf2_blender_extract.convert_swizzle_scale(out_tangent, export_settings)

            # handle parent inverse
            matrix = Matrix()
            matrix[0][0] = scale_data.x
            matrix[1][1] = scale_data.y
            matrix[2][2] = scale_data.z
            matrix = matrix_correction * matrix
            scale_data = matrix.to_scale()

        result[time] = scale_data
        result_in_tangent[time] = in_tangent
        result_out_tangent[time] = out_tangent

        keyframe_index += 1

    return result, result_in_tangent, result_out_tangent


def animate_value(export_settings, value_parameter, interpolation,
                  node_type, node_name, matrix_correction, matrix_basis):
    """Calculate/gather the key value pairs for scalar anaimations."""
    keys = animate_gather_keys(export_settings, value_parameter, interpolation)

    times = animate_convert_keys(keys)

    result = {}
    result_in_tangent = {}
    result_out_tangent = {}

    keyframe_index = 0
    for timeIndex, time in enumerate(times):
        value_data = []
        in_tangent = []
        out_tangent = []

        for blender_fcurve in value_parameter:

            if blender_fcurve is not None:
                if interpolation == CUBIC_INTERPOLATION:
                    blender_key_frame = blender_fcurve.keyframe_points[keyframe_index]

                    value_data.append(blender_key_frame.co[1])

                    if timeIndex == 0:
                        in_tangent_value = 0.0
                    else:
                        factor = 3.0 / (time - times[timeIndex - 1])
                        in_tangent_value = (blender_key_frame.co[1] - blender_key_frame.handle_left[1]) * factor

                    if timeIndex == len(times) - 1:
                        out_tangent_value = 0.0
                    else:
                        factor = 3.0 / (times[timeIndex + 1] - time)
                        out_tangent_value = (blender_key_frame.handle_right[1] - blender_key_frame.co[1]) * factor

                    in_tangent.append(in_tangent_value)
                    out_tangent.append(out_tangent_value)
                else:
                    value = blender_fcurve.evaluate(keys[keyframe_index])

                    value_data.append(value)

        result[time] = value_data
        result_in_tangent[time] = in_tangent
        result_out_tangent[time] = out_tangent

        keyframe_index += 1

    return result, result_in_tangent, result_out_tangent
