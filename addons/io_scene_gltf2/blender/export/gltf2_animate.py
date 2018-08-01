# Copyright (c) 2017 The Khronos Group Inc.
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
import math
import mathutils

from .gltf2_debug import *
from .gltf2_extract import *

#
# Globals
#

#
# Functions
#

def animate_get_interpolation(export_settings, blender_fcurve_list):
    """
    Retrieves the glTF interpolation, depending on a fcurve list.
    Blender allows mixing and more variations of interpolations.  
    In such a case, a conversion is needed.
    """
    
    if export_settings['gltf_force_sampling']:
        return 'CONVERSION_NEEDED'
    
    #
    
    interpolation = None
    
    keyframeCount = None
    
    for blender_fcurve in blender_fcurve_list:
        if blender_fcurve is None:
            continue
        
        #
        
        currentKeyframeCount = len(blender_fcurve.keyframe_points)

        if keyframeCount is None:
            keyframeCount = currentKeyframeCount
        
        if currentKeyframeCount > 0 and blender_fcurve.keyframe_points[0].co[0] < 0:
            return 'CONVERSION_NEEDED'
            
        if keyframeCount != currentKeyframeCount:
            return 'CONVERSION_NEEDED'
        
        #
        
        for blender_keyframe in blender_fcurve.keyframe_points:
            if interpolation is None:
                if blender_keyframe.interpolation == 'BEZIER': 
                    interpolation = 'CUBICSPLINE'
                elif blender_keyframe.interpolation == 'LINEAR': 
                    interpolation = 'LINEAR'
                elif blender_keyframe.interpolation == 'CONSTANT': 
                    interpolation = 'STEP'
                else:
                    interpolation = 'CONVERSION_NEEDED'
                    return interpolation 
            else:
                if blender_keyframe.interpolation == 'BEZIER' and interpolation != 'CUBICSPLINE': 
                    interpolation = 'CONVERSION_NEEDED'
                    return interpolation
                elif blender_keyframe.interpolation == 'LINEAR' and interpolation != 'LINEAR': 
                    interpolation = 'CONVERSION_NEEDED'
                    return interpolation
                elif blender_keyframe.interpolation == 'CONSTANT' and interpolation != 'STEP':
                    interpolation = 'CONVERSION_NEEDED'
                    return interpolation
                elif blender_keyframe.interpolation != 'BEZIER' and blender_keyframe.interpolation != 'LINEAR' and blender_keyframe.interpolation != 'CONSTANT':
                    interpolation = 'CONVERSION_NEEDED'
                    return interpolation

    if interpolation is None:
        interpolation = 'CONVERSION_NEEDED'
    
    return interpolation
    

def animate_convert_rotation_axis_angle(axis_angle):
    """
    Converts an axis angle to a quaternion rotation. 
    """
    q = mathutils.Quaternion((axis_angle[1], axis_angle[2], axis_angle[3]), axis_angle[0])
    
    return [q.x, q.y, q.z, q.w]


def animate_convert_rotation_euler(euler, rotation_mode):
    """
    Converts an euler angle to a quaternion rotation. 
    """
    rotation = mathutils.Euler((euler[0], euler[1], euler[2]), rotation_mode).to_quaternion()

    return [rotation.x, rotation.y, rotation.z, rotation.w]


def animate_convert_keys(key_list):
    """
    Converts Blender key frames to glTF time keys depending on the applied frames per second. 
    """
    times = []
    
    for key in key_list:
        times.append(key / bpy.context.scene.render.fps)

    return times


def animate_gather_keys(export_settings, fcurve_list, interpolation):
    """
    Merges and sorts several key frames to one set. 
    If an interpolation conversion is needed, the sample key frames are created as well.
    """
    keys = []
    
    if interpolation == 'CONVERSION_NEEDED':
        start = None
        end = None
        
        for blender_fcurve in fcurve_list:
            if blender_fcurve is None:
                continue
            
            if start == None:
                start = blender_fcurve.range()[0]
            else:
                start = min(start, blender_fcurve.range()[0])
                
            if end == None:
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
                
                if blender_keyframe.interpolation == 'CONSTANT':
                    add_epsilon_keyframe = True
            
            if add_epsilon_keyframe:
                key = end - 0.001
                
                if key not in keys:
                    keys.append(key)

        key = start
        while key <= end:
            if not export_settings['gltf_frame_range'] or (export_settings['gltf_frame_range'] and key >= bpy.context.scene.frame_start and key <= bpy.context.scene.frame_end): 
                keys.append(key)
            key += export_settings['gltf_frame_step']
            
        keys.sort()
        
    else: 
        for blender_fcurve in fcurve_list:
            if blender_fcurve is None:
                continue
            
            for blender_keyframe in blender_fcurve.keyframe_points:
                key = blender_keyframe.co[0]
                if not export_settings['gltf_frame_range'] or (export_settings['gltf_frame_range'] and key >= bpy.context.scene.frame_start and key <= bpy.context.scene.frame_end): 
                    if key not in keys:
                        keys.append(key)

        keys.sort()
    
    return keys


def animate_location(export_settings, location, interpolation, node_type, node_name, action_name, matrix_correction, matrix_basis):
    """
    Calculates/gathers the key value pairs for location transformations.
    """
    joint_cache = export_settings['gltf_joint_cache'][action_name]
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
        
        if node_type == 'JOINT':
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
                    
                    if interpolation == 'CUBICSPLINE':
                        blender_key_frame = blender_fcurve.keyframe_points[keyframe_index]

                        translation[channel_index] = blender_key_frame.co[1]

                        if timeIndex == 0:
                            in_tangent_value = 0.0
                        else:
                            in_tangent_value = 3.0 * (blender_key_frame.co[1] - blender_key_frame.handle_left[1]) / (time - times[timeIndex - 1])

                        if timeIndex == len(times) - 1:
                            out_tangent_value = 0.0
                        else:
                            out_tangent_value = 3.0 * (blender_key_frame.handle_right[1] - blender_key_frame.co[1]) / (times[timeIndex + 1] - time)

                        in_tangent[channel_index] = in_tangent_value
                        out_tangent[channel_index] = out_tangent_value
                    else: 
                        value = blender_fcurve.evaluate(keys[keyframe_index]) 

                        translation[channel_index] = value
                
                channel_index += 1 
            
            # handle parent inverse
            matrix = mathutils.Matrix.Translation(translation)
            matrix = matrix_correction * matrix
            translation = matrix.to_translation()
        
            translation = convert_swizzle_location(translation, export_settings)
            in_tangent = convert_swizzle_location(in_tangent, export_settings)
            out_tangent = convert_swizzle_location(out_tangent, export_settings)
        
        result[time] = translation
        result_in_tangent[time] = in_tangent
        result_out_tangent[time] = out_tangent
        
        keyframe_index += 1 

    return result, result_in_tangent, result_out_tangent


def animate_rotation_axis_angle(export_settings, rotation_axis_angle, interpolation, node_type, node_name, action_name, matrix_correction, matrix_basis):
    """
    Calculates/gathers the key value pairs for axis angle transformations.
    """
    joint_cache = export_settings['gltf_joint_cache'][action_name]
    if not joint_cache.get(node_name):
        joint_cache[node_name] = {}
    
    keys = animate_gather_keys(export_settings, rotation_axis_angle, interpolation)
    
    times = animate_convert_keys(keys)
    
    result = {}
    
    keyframe_index = 0
    for time in times:
        axis_angle_rotation = [1.0, 0.0, 0.0, 0.0]
        
        rotation = [1.0, 0.0, 0.0, 0.0]
        
        if node_type == 'JOINT':
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
            rotation = mathutils.Quaternion((rotation[3], rotation[0], rotation[1], rotation[2]))
            matrix = rotation.to_matrix().to_4x4()
            matrix = matrix_correction * matrix
            rotation = matrix.to_quaternion()

            # Bring back to internal Quaternion notation.
            rotation = convert_swizzle_rotation([rotation[0], rotation[1], rotation[2], rotation[3]], export_settings)
            
        # Bring back to glTF Quaternion notation.
        rotation = [rotation[1], rotation[2], rotation[3], rotation[0]]
        
        result[time] = rotation
        
        keyframe_index += 1 

    return result


def animate_rotation_euler(export_settings, rotation_euler, rotation_mode, interpolation, node_type, node_name, action_name, matrix_correction, matrix_basis):
    """
    Calculates/gathers the key value pairs for euler angle transformations.
    """
    joint_cache = export_settings['gltf_joint_cache'][action_name]
    if not joint_cache.get(node_name):
        joint_cache[node_name] = {}
    
    keys = animate_gather_keys(export_settings, rotation_euler, interpolation)

    times = animate_convert_keys(keys)

    result = {}
    
    keyframe_index = 0
    for time in times:
        euler_rotation = [0.0, 0.0, 0.0]
        
        rotation = [1.0, 0.0, 0.0, 0.0]
        
        if node_type == 'JOINT':
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
            rotation = mathutils.Quaternion((rotation[3], rotation[0], rotation[1], rotation[2]))
            matrix = rotation.to_matrix().to_4x4()
            matrix = matrix_correction * matrix
            rotation = matrix.to_quaternion()

            # Bring back to internal Quaternion notation.
            rotation = convert_swizzle_rotation([rotation[0], rotation[1], rotation[2], rotation[3]], export_settings)
            
        # Bring back to glTF Quaternion notation.
        rotation = [rotation[1], rotation[2], rotation[3], rotation[0]]
        
        result[time] = rotation
        
        keyframe_index += 1 

    return result


def animate_rotation_quaternion(export_settings, rotation_quaternion, interpolation, node_type, node_name, action_name, matrix_correction, matrix_basis):
    """
    Calculates/gathers the key value pairs for quaternion transformations.
    """
    joint_cache = export_settings['gltf_joint_cache'][action_name]
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
        
        if node_type == 'JOINT':
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
                    if interpolation == 'CUBICSPLINE':
                        blender_key_frame = blender_fcurve.keyframe_points[keyframe_index]

                        rotation[channel_index] = blender_key_frame.co[1]

                        if timeIndex == 0:
                            in_tangent_value = 0.0
                        else:
                            in_tangent_value = 3.0 * (blender_key_frame.co[1] - blender_key_frame.handle_left[1]) / (time - times[timeIndex - 1])

                        if timeIndex == len(times) - 1:
                            out_tangent_value = 0.0
                        else:
                            out_tangent_value = 3.0 * (blender_key_frame.handle_right[1] - blender_key_frame.co[1]) / (times[timeIndex + 1] - time)

                        in_tangent[channel_index] = in_tangent_value
                        out_tangent[channel_index] = out_tangent_value
                    else: 
                        value = blender_fcurve.evaluate(keys[keyframe_index]) 
                        
                        rotation[channel_index] = value
                
                channel_index += 1 
        
            rotation = mathutils.Quaternion((rotation[0], rotation[1], rotation[2], rotation[3]))
            in_tangent = convert_swizzle_rotation(in_tangent, export_settings)
            out_tangent = convert_swizzle_rotation(out_tangent, export_settings)

            # handle parent inverse
            matrix = rotation.to_matrix().to_4x4()
            matrix = matrix_correction * matrix
            rotation = matrix.to_quaternion()

            # Bring back to internal Quaternion notation.
            rotation = convert_swizzle_rotation([rotation[0], rotation[1], rotation[2], rotation[3]], export_settings)

        # Bring to glTF Quaternion notation.
        rotation = [rotation[1], rotation[2], rotation[3], rotation[0]]
        in_tangent = [in_tangent[1], in_tangent[2], in_tangent[3], in_tangent[0]]
        out_tangent = [out_tangent[1], out_tangent[2], out_tangent[3], out_tangent[0]]
        
        result[time] = rotation
        result_in_tangent[time] = in_tangent
        result_out_tangent[time] = out_tangent
        
        keyframe_index += 1 

    return result, result_in_tangent, result_out_tangent


def animate_scale(export_settings, scale, interpolation, node_type, node_name, action_name, matrix_correction, matrix_basis):
    """
    Calculates/gathers the key value pairs for scale transformations.
    """
    joint_cache = export_settings['gltf_joint_cache'][action_name]
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
        
        if node_type == 'JOINT':
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
                    if interpolation == 'CUBICSPLINE':
                        blender_key_frame = blender_fcurve.keyframe_points[keyframe_index]

                        scale_data[channel_index] = blender_key_frame.co[1]

                        if timeIndex == 0:
                            in_tangent_value = 0.0
                        else:
                            in_tangent_value = 3.0 * (blender_key_frame.co[1] - blender_key_frame.handle_left[1]) / (time - times[timeIndex - 1])

                        if timeIndex == len(times) - 1:
                            out_tangent_value = 0.0
                        else:
                            out_tangent_value = 3.0 * (blender_key_frame.handle_right[1] - blender_key_frame.co[1]) / (times[timeIndex + 1] - time)

                        in_tangent[channel_index] = in_tangent_value
                        out_tangent[channel_index] = out_tangent_value
                    else: 
                        value = blender_fcurve.evaluate(keys[keyframe_index]) 
                        
                        scale_data[channel_index] = value
                
                channel_index += 1 
        
            scale_data = convert_swizzle_scale(scale_data, export_settings)
            in_tangent = convert_swizzle_scale(in_tangent, export_settings)
            out_tangent = convert_swizzle_scale(out_tangent, export_settings)
        
            # handle parent inverse
            matrix = mathutils.Matrix()
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


def animate_value(export_settings, value_parameter, interpolation, node_type, node_name, matrix_correction, matrix_basis):
    """
    Calculates/gathers the key value pairs for scalar anaimations.
    """
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
                if interpolation == 'CUBICSPLINE':
                    blender_key_frame = blender_fcurve.keyframe_points[keyframe_index]

                    value_data.append(blender_key_frame.co[1])

                    if timeIndex == 0:
                        in_tangent_value = 0.0
                    else:
                        in_tangent_value = 3.0 * (blender_key_frame.co[1] - blender_key_frame.handle_left[1]) / (time - times[timeIndex - 1])

                    if timeIndex == len(times) - 1:
                        out_tangent_value = 0.0
                    else:
                        out_tangent_value = 3.0 * (blender_key_frame.handle_right[1] - blender_key_frame.co[1]) / (times[timeIndex + 1] - time)

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
