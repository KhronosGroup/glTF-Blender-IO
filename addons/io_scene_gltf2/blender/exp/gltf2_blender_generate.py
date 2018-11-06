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

import copy
import base64

from .gltf2_blender_animate import *
from .gltf2_blender_extract import *
from .gltf2_blender_generate_materials import *
from .gltf2_blender_generate_extras import generate_extras
from ..com.gltf2_blender_image_util import *
from io_scene_gltf2.io.com import gltf2_io

#
# Functions
#
FRAME_STEP = 'gltf_frame_step'
JOINT_CACHE = 'gltf_joint_cache'


def generate_animations_parameter(
        operator,
        context,
        export_settings,
        glTF,
        action,
        channels,
        samplers,
        blender_node_name,
        blender_bone_name,
        rotation_mode,
        matrix_correction,
        matrix_basis,
        is_morph_data
):
    """
    Helper function for storing animation parameters.
    """

    name = blender_node_name

    prefix = ""
    postfix = ""

    node_type = 'NODE'
    used_node_name = blender_node_name
    if blender_bone_name is not None:
        node_type = 'JOINT'
        used_node_name = blender_bone_name

    #

    location = [None, None, None]
    rotation_axis_angle = [None, None, None, None]
    rotation_euler = [None, None, None]
    rotation_quaternion = [None, None, None, None]
    scale = [None, None, None]
    value = []

    data = {
        'location': location,
        'rotation_axis_angle': rotation_axis_angle,
        'rotation_euler': rotation_euler,
        'rotation_quaternion': rotation_quaternion,
        'scale': scale,
        'value': value
    }

    # Gather fcurves by transform
    for blender_fcurve in action.fcurves:
        node_name = get_node(blender_fcurve.data_path)

        if node_name is not None and not is_morph_data:
            if blender_bone_name is None:
                continue
            elif blender_bone_name != node_name:
                continue
            else:
                prefix = node_name + "_"
                postfix = "_" + node_name

        data_path = get_data_path(blender_fcurve.data_path)

        if data_path == 'value':
            data[data_path].append(blender_fcurve)
        elif data_path in ['location', 'rotation_axis_angle', 'rotation_euler', 'rotation_quaternion', 'scale']:
            data[data_path][blender_fcurve.array_index] = blender_fcurve

    #

    if location.count(None) < 3:

        sampler_name = prefix + action.name + "_translation"

        if get_index(samplers, sampler_name) == -1:
            # Sampler doesn't exist, lets create it

            sampler = {}

            #

            interpolation = animate_get_interpolation(export_settings, location)
            if interpolation == 'CUBICSPLINE' and node_type == 'JOINT':
                interpolation = 'CONVERSION_NEEDED'

            if interpolation == 'CONVERSION_NEEDED':
                sampler['interpolation'] = 'LINEAR'
            else:
                sampler['interpolation'] = interpolation

            translation_data, in_tangent_data, out_tangent_data = animate_location(
                export_settings,
                location,
                interpolation,
                node_type,
                used_node_name,
                action.name,
                matrix_correction,
                matrix_basis
            )

            #

            keys = sorted(translation_data.keys())
            values = []
            final_keys = []

            key_offset = 0.0
            if len(keys) > 0 and export_settings[export_keys.MOVE_KEYFRAMES]:
                key_offset = bpy.context.scene.frame_start / bpy.context.scene.render.fps

            for key in keys:
                if key - key_offset < 0.0:
                    continue

                final_keys.append(key - key_offset)

                if interpolation == 'CUBICSPLINE':
                    for i in range(0, 3):
                        values.append(in_tangent_data[key][i])
                for i in range(0, 3):
                    values.append(translation_data[key][i])
                if interpolation == 'CUBICSPLINE':
                    for i in range(0, 3):
                        values.append(out_tangent_data[key][i])

            #

            count = len(final_keys)
            sampler['input'] = generate_accessor(
                export_settings,
                glTF,
                final_keys,
                GLTF_COMPONENT_TYPE_FLOAT,
                count,
                GLTF_DATA_TYPE_SCALAR,
                ""
            )

            #

            count = len(values) // 3

            sampler['output'] = generate_accessor(
                export_settings,
                glTF,
                values,
                GLTF_COMPONENT_TYPE_FLOAT,
                count,
                GLTF_DATA_TYPE_VEC3,
                ""
            )

            #

            sampler['name'] = sampler_name

            #

            if sampler['output'] != -1 and sampler['input'] != -1:
                samplers.append(sampler)
            else:
                print_console('WARNING', 'Skipping sampler ' + sampler_name + ', found missing or invalid data.')

            #
    #

    rotation_data = None
    rotation_in_tangent_data = [0.0, 0.0, 0.0, 0.0]
    rotation_out_tangent_data = [0.0, 0.0, 0.0, 0.0]
    interpolation = None

    sampler_name = prefix + action.name + "_rotation"

    if get_index(samplers, sampler_name) == -1:
        if rotation_axis_angle.count(None) < 4:
            interpolation = animate_get_interpolation(export_settings, rotation_axis_angle)
            # Conversion required in any case.
            if interpolation == 'CUBICSPLINE':
                interpolation = 'CONVERSION_NEEDED'
            rotation_data = animate_rotation_axis_angle(export_settings, rotation_axis_angle, interpolation, node_type,
                                                        used_node_name, action.name, matrix_correction, matrix_basis)

        if rotation_euler.count(None) < 3:
            interpolation = animate_get_interpolation(export_settings, rotation_euler)
            # Conversion required in any case.
            if interpolation == 'CUBICSPLINE':
                interpolation = 'CONVERSION_NEEDED'
            rotation_data = animate_rotation_euler(export_settings, rotation_euler, rotation_mode, interpolation,
                                                   node_type, used_node_name, action.name, matrix_correction,
                                                   matrix_basis)

        if rotation_quaternion.count(None) < 4:
            interpolation = animate_get_interpolation(export_settings, rotation_quaternion)
            if interpolation == 'CUBICSPLINE' and node_type == 'JOINT':
                interpolation = 'CONVERSION_NEEDED'
            rotation_data, rotation_in_tangent_data, rotation_out_tangent_data = animate_rotation_quaternion(
                export_settings, rotation_quaternion, interpolation, node_type, used_node_name, action.name,
                matrix_correction, matrix_basis)

    if rotation_data is not None:

        #

        keys = sorted(rotation_data.keys())
        values = []
        final_keys = []

        key_offset = 0.0
        if len(keys) > 0 and export_settings[export_keys.MOVE_KEYFRAMES]:
            key_offset = bpy.context.scene.frame_start / bpy.context.scene.render.fps

        for key in keys:
            if key - key_offset < 0.0:
                continue

            final_keys.append(key - key_offset)

            if interpolation == 'CUBICSPLINE':
                for i in range(0, 4):
                    values.append(rotation_in_tangent_data[key][i])
            for i in range(0, 4):
                values.append(rotation_data[key][i])
            if interpolation == 'CUBICSPLINE':
                for i in range(0, 4):
                    values.append(rotation_out_tangent_data[key][i])

        #

        sampler = {}

        #

        count = len(final_keys)

        sampler['input'] = generate_accessor(
            export_settings,
            glTF,
            final_keys,
            GLTF_COMPONENT_TYPE_FLOAT,
            count,
            GLTF_DATA_TYPE_SCALAR,
            ""
        )

        #
        count = len(values) // 4

        sampler['output'] = generate_accessor(
            export_settings,
            glTF,
            values,
            GLTF_COMPONENT_TYPE_FLOAT,
            count,
            GLTF_DATA_TYPE_VEC4,
            ""
        )

        #

        sampler['interpolation'] = interpolation
        if interpolation == 'CONVERSION_NEEDED':
            sampler['interpolation'] = 'LINEAR'

        #

        sampler['name'] = sampler_name

        #

        if sampler['output'] != -1 and sampler['input'] != -1:
            samplers.append(sampler)
        else:
            print_console('WARNING', 'Skipping sampler ' + sampler_name + ', found missing or invalid data.')

        #
    #

    if scale.count(None) < 3:
        sampler_name = prefix + action.name + "_scale"

        if get_index(samplers, sampler_name) == -1:

            sampler = {}

            #

            interpolation = animate_get_interpolation(export_settings, scale)
            if interpolation == 'CUBICSPLINE' and node_type == 'JOINT':
                interpolation = 'CONVERSION_NEEDED'

            sampler['interpolation'] = interpolation
            if interpolation == 'CONVERSION_NEEDED':
                sampler['interpolation'] = 'LINEAR'

            scale_data, in_tangent_data, out_tangent_data = animate_scale(
                export_settings,
                scale,
                interpolation,
                node_type,
                used_node_name,
                action.name,
                matrix_correction,
                matrix_basis
            )

            #

            keys = sorted(scale_data.keys())
            values = []
            final_keys = []

            key_offset = 0.0
            if len(keys) > 0 and export_settings[export_keys.MOVE_KEYFRAMES]:
                key_offset = bpy.context.scene.frame_start / bpy.context.scene.render.fps

            for key in keys:
                if key - key_offset < 0.0:
                    continue

                final_keys.append(key - key_offset)

                if interpolation == 'CUBICSPLINE':
                    for i in range(0, 3):
                        values.append(in_tangent_data[key][i])
                for i in range(0, 3):
                    values.append(scale_data[key][i])
                if interpolation == 'CUBICSPLINE':
                    for i in range(0, 3):
                        values.append(out_tangent_data[key][i])

            #

            count = len(final_keys)

            sampler['input'] = generate_accessor(
                export_settings,
                glTF,
                final_keys,
                GLTF_COMPONENT_TYPE_FLOAT,
                count,
                GLTF_DATA_TYPE_SCALAR,
                ""
            )

            #

            count = len(values) // 3

            sampler['output'] = generate_accessor(
                export_settings,
                glTF,
                values,
                GLTF_COMPONENT_TYPE_FLOAT,
                count,
                GLTF_DATA_TYPE_VEC3,
                ""
            )

            #

            sampler['name'] = sampler_name

            #

            if sampler['output'] != -1 and sampler['input'] != -1:
                samplers.append(sampler)
            else:
                print_console('WARNING', 'Skipping sampler ' + sampler_name + ', found missing or invalid data.')

    #
    #

    if len(value) > 0 and is_morph_data:
        sampler_name = prefix + action.name + "_weights"

        if get_index(samplers, sampler_name) == -1:

            sampler = {}

            #

            interpolation = animate_get_interpolation(export_settings, value)
            if interpolation == 'CUBICSPLINE' and node_type == 'JOINT':
                interpolation = 'CONVERSION_NEEDED'

            sampler['interpolation'] = interpolation
            if interpolation == 'CONVERSION_NEEDED':
                sampler['interpolation'] = 'LINEAR'

            value_data, in_tangent_data, out_tangent_data = animate_value(export_settings, value, interpolation,
                                                                          node_type, used_node_name, matrix_correction,
                                                                          matrix_basis)

            #

            keys = sorted(value_data.keys())
            values = []
            final_keys = []

            key_offset = 0.0
            if len(keys) > 0 and export_settings[export_keys.MOVE_KEYFRAMES]:
                key_offset = bpy.context.scene.frame_start / bpy.context.scene.render.fps

            for key in keys:
                if key - key_offset < 0.0:
                    continue

                final_keys.append(key - key_offset)

                if interpolation == 'CUBICSPLINE':
                    for i in range(0, len(in_tangent_data[key])):
                        values.append(in_tangent_data[key][i])
                for i in range(0, len(value_data[key])):
                    values.append(value_data[key][i])
                if interpolation == 'CUBICSPLINE':
                    for i in range(0, len(out_tangent_data[key])):
                        values.append(out_tangent_data[key][i])

            #

            count = len(final_keys)

            sampler['input'] = generate_accessor(
                export_settings,
                glTF,
                final_keys,
                GLTF_COMPONENT_TYPE_FLOAT,
                count,
                GLTF_DATA_TYPE_SCALAR,
                ""
            )

            #

            count = len(values)

            sampler['output'] = generate_accessor(
                export_settings,
                glTF,
                values,
                GLTF_COMPONENT_TYPE_FLOAT,
                count,
                GLTF_DATA_TYPE_SCALAR,
                ""
            )

            #

            sampler['name'] = sampler_name

            #

            if sampler['output'] != -1 and sampler['input'] != -1:
                samplers.append(sampler)
            else:
                print_console('WARNING', 'Skipping sampler ' + sampler_name + ', found missing or invalid data.')

    #
    #
    #
    #

    write_transform = [False, False, False, False]

    # Gather fcurves by transform
    for blender_fcurve in action.fcurves:
        node_name = get_node(blender_fcurve.data_path)

        if node_name is not None and not is_morph_data:
            if blender_bone_name is None:
                continue
            elif blender_bone_name != node_name:
                continue
            else:
                prefix = node_name + "_"
                postfix = "_" + node_name

        data_path = get_data_path(blender_fcurve.data_path)

        if data_path == 'location':
            write_transform[0] = True
        if data_path in ['rotation_axis_angle', 'rotation_euler', 'rotation_quaternion']:
            write_transform[1] = True
        if data_path == 'scale':
            write_transform[2] = True
        if data_path == 'value':
            write_transform[3] = True

    #

    write_transform_index = 0
    for path in ['translation', 'rotation', 'scale', 'weights']:

        if write_transform[write_transform_index]:
            sampler_name = prefix + action.name + "_" + path

            sampler_index = get_index(samplers, sampler_name)

            # Skip channels containing skipped samplers.
            if sampler_index == -1:
                print_console('WARNING', 'Skipped channel in action ' + action.name + ', missing sampler.')
                continue

            #

            channel = {}
            channel['sampler'] = sampler_index

            #

            target_name = name + postfix

            channel['target'] = {
                'path': path,
                'node': get_node_index(glTF, target_name)
            }

            #

            channels.append(channel)

        write_transform_index += 1


#
# Property: animations
#
def generate_animations(operator,
                        context,
                        export_settings,
                        glTF):
    """
    Generates the top level animations entry.
    """

    def process_object_animations(blender_object, blender_action):
        correction_matrix_local = blender_object.matrix_parent_inverse
        matrix_basis = mathutils.Matrix.Identity(4)

        #

        if export_settings[export_keys.BAKE_SKINS]:
            blender_action = bake_action(export_settings, blender_object, blender_action)

        #

        if blender_action.name not in animations:
            animations[blender_action.name] = {
                'name': blender_action.name,
                'channels': [],
                'samplers': []
            }

        channels = animations[blender_action.name]['channels']
        samplers = animations[blender_action.name]['samplers']

        # Add entry to joint cache. Current action may not need skinnning,
        # but there are too many places to check for and add it later.
        gltf_joint_cache = export_settings[export_keys.JOINT_CACHE]
        if not gltf_joint_cache.get(blender_action.name):
            gltf_joint_cache[blender_action.name] = {}

        #

        generate_animations_parameter(
            operator,
            context,
            export_settings,
            glTF,
            blender_action,
            channels,
            samplers,
            blender_object.name,
            None,
            blender_object.rotation_mode,
            correction_matrix_local,
            matrix_basis,
            False
        )

        if export_settings[export_keys.SKINS]:
            if blender_object.type == 'ARMATURE' and len(blender_object.pose.bones) > 0:

                #

                if export_settings[export_keys.YUP]:
                    axis_basis_change = mathutils.Matrix(
                        ((1.0, 0.0, 0.0, 0.0),
                         (0.0, 0.0, 1.0, 0.0),
                         (0.0, -1.0, 0.0, 0.0),
                         (0.0, 0.0, 0.0, 1.0))
                    )
                else:
                    axis_basis_change = mathutils.Matrix.Identity(4)

                # Precalculate joint animation data.

                start, end = compute_action_range(export_settings, [blender_action])

                # Iterate over frames in export range
                for frame in range(int(start), int(end) + 1):
                    bpy.context.scene.frame_set(frame)

                    # Iterate over object's bones
                    for blender_bone in blender_object.pose.bones:

                        correction_matrix_local, matrix_basis = compute_bone_matrices(
                            axis_basis_change,
                            blender_bone,
                            blender_object,
                            export_settings
                        )

                        if not gltf_joint_cache[blender_action.name].get(blender_bone.name):
                            gltf_joint_cache[blender_action.name][blender_bone.name] = {}

                        matrix = correction_matrix_local * matrix_basis

                        tmp_location, tmp_rotation, tmp_scale = matrix.decompose()

                        gltf_joint_cache[blender_action.name][blender_bone.name][float(frame)] = [tmp_location,
                                                                                                  tmp_rotation,
                                                                                                  tmp_scale]

                #

                for blender_bone in blender_object.pose.bones:
                    correction_matrix_local, matrix_basis = compute_bone_matrices(
                        axis_basis_change,
                        blender_bone,
                        blender_object,
                        export_settings
                    )

                    generate_animations_parameter(
                        operator,
                        context,
                        export_settings,
                        glTF,
                        blender_action,
                        channels,
                        samplers,
                        blender_object.name,
                        blender_bone.name,
                        blender_bone.rotation_mode,
                        correction_matrix_local,
                        matrix_basis,
                        False
                    )

    animations = {}

    #
    #

    filtered_objects = export_settings[export_keys.FILTERED_OBJECTS]

    #
    #

    processed_meshes = {}

    def process_mesh_object(blender_object, blender_action):
        blender_mesh = blender_object.data

        if blender_action.name not in processed_meshes:
            processed_meshes[blender_action.name] = []

        if blender_mesh in processed_meshes[blender_action.name]:
            return

        #

        if blender_action.name not in animations:
            animations[blender_action.name] = {
                'name': blender_action.name,
                'channels': [],
                'samplers': []
            }

        channels = animations[blender_action.name]['channels']
        samplers = animations[blender_action.name]['samplers']

        #

        correction_matrix_local = mathutils.Matrix.Identity(4)
        matrix_basis = mathutils.Matrix.Identity(4)

        generate_animations_parameter(operator, context, export_settings, glTF, blender_action, channels, samplers,
                                      blender_object.name, None, blender_object.rotation_mode, correction_matrix_local,
                                      matrix_basis, True)

        processed_meshes[blender_action.name].append(blender_mesh)

    for blender_object in filtered_objects:

        animation_data = blender_object.animation_data

        if animation_data is not None:
            object_actions = []

            # Collect active action.
            if animation_data.action:
                object_actions.append(animation_data.action)

            # Collect associated strips from NLA tracks.
            for track in animation_data.nla_tracks:
                # Multi-strip tracks do not export correctly yet (they need to be baked),
                # so skip them for now and only write single-strip tracks.
                if track.strips is None or len(track.strips) != 1:
                    continue
                for strip in track.strips:
                    object_actions.append(strip.action)

            # Remove duplicate actions.
            object_actions = list(set(object_actions))

            # Export all collected actions.
            for action in object_actions:
                active_action = animation_data.action
                animation_data.action = action

                process_object_animations(blender_object, action)

                animation_data.action = active_action

        #

        # Export shape keys.
        is_mesh = blender_object.type == 'MESH'
        has_data = blender_object.data is not None
        has_shape_keys = blender_object.data.shape_keys is not None
        has_animation_data = blender_object.data.shape_keys.animation_data is not None
        if not (is_mesh and has_data and has_shape_keys and has_animation_data):
            continue

        shape_keys = blender_object.data.shape_keys
        shape_key_actions = []

        if shape_keys.animation_data.action:
            shape_key_actions.append(shape_keys.animation_data.action)

        for track in shape_keys.animation_data.nla_tracks:
            for strip in track.strips:
                shape_key_actions.append(strip.action)

        for action in shape_key_actions:
            active_action = shape_keys.animation_data.action
            shape_keys.animation_data.action = action

            process_mesh_object(blender_object, action)

            shape_keys.animation_data.action = active_action

    #
    #

    if len(animations) > 0:
        # Sampler 'name' is used to gather the index. However, 'name' is no property of sampler and has to be removed.
        for animation in animations.values():
            for sampler in animation['samplers']:
                del sampler['name']
            if len(animation['channels']) > 0:
                glTF.animations.append(gltf2_io.Animation.from_dict(animation))


def compute_bone_matrices(axis_basis_change, blender_bone, blender_object, export_settings):
    matrix_basis = blender_bone.matrix_basis

    if blender_bone.parent is None:
        # Bone has no parent
        correction_matrix_local = axis_basis_change * blender_bone.bone.matrix_local
    else:
        # Transform matrix by parent bone's matrix
        correction_matrix_local = blender_bone.parent.bone.matrix_local.inverted() * blender_bone.bone.matrix_local

    if export_settings[export_keys.BAKE_SKINS]:
        matrix_basis = blender_object.convert_space(
            blender_bone,
            blender_bone.matrix,
            from_space='POSE',
            to_space='LOCAL'
        )

    return correction_matrix_local, matrix_basis


def bake_action(export_settings, blender_object, blender_action):
    start, end = compute_action_range(export_settings, [blender_action])
    step = export_settings[export_keys.FRAME_STEP]

    #

    bpy.context.scene.objects.active = blender_object
    blender_object.animation_data.action = blender_action

    #

    bpy.ops.nla.bake(frame_start=start, frame_end=end, step=step, only_selected=True, visual_keying=True,
                     clear_constraints=False, use_current_action=True, bake_types={'POSE'})

    #

    return blender_object.animation_data.action


def compute_action_range(export_settings, actions):
    start = None
    end = None
    for current_blender_action in actions:
        for current_blender_fcurve in current_blender_action.fcurves:
            if current_blender_fcurve is None:
                continue

            if start is None:
                start = current_blender_fcurve.range()[0]
            else:
                start = min(start, current_blender_fcurve.range()[0])

            if end is None:
                end = current_blender_fcurve.range()[1]
            else:
                end = max(end, current_blender_fcurve.range()[1])
    if start is None or end is None or export_settings[export_keys.FRAME_RANGE]:
        start = bpy.context.scene.frame_start
        end = bpy.context.scene.frame_end
    return start, end


def generate_cameras(export_settings, glTF):
    """
    Generates the top level cameras entry.
    """

    cameras = []

    #
    #

    filtered_cameras = export_settings[export_keys.FILTERED_CAMERAS]

    for blender_camera in filtered_cameras:

        #
        # Property: camera
        #

        camera = {}

        if blender_camera.type == 'PERSP':
            camera['type'] = 'perspective'

            perspective = {}

            #

            # None of them can get 0, as Blender checks this.
            width = bpy.context.scene.render.pixel_aspect_x * bpy.context.scene.render.resolution_x
            height = bpy.context.scene.render.pixel_aspect_y * bpy.context.scene.render.resolution_y

            aspectRatio = width / height

            perspective['aspectRatio'] = aspectRatio

            yfov = None

            if width >= height:
                if blender_camera.sensor_fit != 'VERTICAL':
                    yfov = 2.0 * math.atan(math.tan(blender_camera.angle * 0.5) / aspectRatio)
                else:
                    yfov = blender_camera.angle
            else:
                if blender_camera.sensor_fit != 'HORIZONTAL':
                    yfov = blender_camera.angle
                else:
                    yfov = 2.0 * math.atan(math.tan(blender_camera.angle * 0.5) / aspectRatio)

            perspective['yfov'] = yfov

            perspective['znear'] = blender_camera.clip_start

            if not export_settings[export_keys.CAMERA_INFINITE]:
                perspective['zfar'] = blender_camera.clip_end

            #

            camera['perspective'] = perspective
        elif blender_camera.type == 'ORTHO':
            camera['type'] = 'orthographic'

            orthographic = {}

            #

            orthographic['xmag'] = blender_camera.ortho_scale
            orthographic['ymag'] = blender_camera.ortho_scale

            orthographic['znear'] = blender_camera.clip_start
            orthographic['zfar'] = blender_camera.clip_end

            #

            camera['orthographic'] = orthographic
        else:
            continue

        #

        camera['name'] = blender_camera.name

        #
        #

        cameras.append(gltf2_io.Camera.from_dict(camera))

    #
    #

    if len(cameras) > 0:
        glTF.cameras = cameras


def generate_lights(operator,
                    context,
                    export_settings,
                    glTF):
    """
    Generates the top level lights entry.
    Note: This is currently an experimental feature.
    """

    lights = []

    #
    #

    filtered_lights = export_settings[export_keys.FILTERED_LIGHTS]

    for blender_light in filtered_lights:

        #
        # Property: light
        #

        light = {}

        if blender_light.type == 'SUN':
            light['type'] = 'directional'
        elif blender_light.type == 'POINT':
            light['type'] = 'point'
        elif blender_light.type == 'SPOT':
            light['type'] = 'spot'
        else:
            continue

        if blender_light.type == 'SPOT':
            spot = {}

            angle = blender_light.spot_size * 0.5

            spot['outerConeAngle'] = angle
            spot['innerConeAngle'] = angle - angle * blender_light.spot_blend

            light['spot'] = spot

        light_color = [blender_light.color[0], blender_light.color[1], blender_light.color[2]]
        light_intensity = blender_light.energy

        if blender_light.use_nodes and blender_light.node_tree:
            for currentNode in blender_light.node_tree.nodes:
                if isinstance(currentNode, bpy.types.ShaderNodeOutputLamp):
                    if not currentNode.is_active_output:
                        continue
                    emission_node = get_emission_node_from_lamp_output_node(currentNode)
                    if emission_node is None:
                        continue
                    emission_color = emission_node.inputs["Color"].default_value
                    if blender_light.type != 'SUN':
                        quadratic_falloff_node = get_ligth_falloff_node_from_emission_node(emission_node, 'Quadratic')
                        if quadratic_falloff_node is None:
                            print_console('WARNING',
                                          'No quadratic light falloff node attached to emission strength property')
                            continue
                        emission_strength = quadratic_falloff_node.inputs["Strength"].default_value / (math.pi * 4.0)
                    else:
                        emission_strength = emission_node.inputs["Strength"].default_value
                    light_color = [emission_color[0], emission_color[1], emission_color[2]]
                    light_intensity = emission_strength
                    break

        light['color'] = light_color
        light['intensity'] = light_intensity

        #

        light['name'] = blender_light.name

        #
        #

        lights.append(light)

    #
    #
    #

    if len(lights) > 0:
        generate_extensionsUsed(export_settings, glTF, 'KHR_lights_punctual')
        generate_extensionsRequired(export_settings, glTF, 'KHR_lights_punctual')

        extensions = glTF.extensions

        extensions['KHR_lights_punctual'] = {
            'lights': lights
        }


def generate_meshes(operator,
                    context,
                    export_settings,
                    glTF):
    """
    Generates the top level meshes entry.
    """

    meshes = []

    #
    #

    filtered_meshes = export_settings[export_keys.FILTERED_MESHES]

    filtered_vertex_groups = export_settings[export_keys.FILTERED_VERTEX_GROUPS]

    for name, blender_mesh in filtered_meshes.items():

        internal_primitives = extract_primitives(glTF, blender_mesh, filtered_vertex_groups[name], export_settings)

        if len(internal_primitives) == 0:
            continue

        #
        # Property: mesh
        #

        primitives = []

        mesh = gltf2_io.Mesh(
            extensions=None,
            extras=None,
            name=name,
            primitives=primitives,
            weights=None
        )

        #

        for internal_primitive in internal_primitives:

            attributes = {}

            primitive = gltf2_io.MeshPrimitive(
                attributes=attributes,
                extensions=None,
                extras=None,
                indices=None,
                material=None,
                mode=None,
                targets=None
            )

            #
            #

            if export_settings[export_keys.MATERIALS]:
                material = get_material_index(glTF, internal_primitive['material'])

                if get_material_requires_texcoords(glTF, material) and not export_settings[export_keys.TEX_COORDS]:
                    material = -1

                if get_material_requires_normals(glTF, material) and not export_settings[export_keys.NORMALS]:
                    material = -1

                # Meshes/primitives without material are allowed.
                if material >= 0:
                    primitive.material = material
                else:
                    message = "Material {} not found. " \
                              "Please assign glTF 2.0 material or enable Blinn-Phong material in export." \
                        .format(internal_primitive['material'])
                    print_console('WARNING', message)

            #
            #

            indices = internal_primitive['indices']

            componentType = GLTF_COMPONENT_TYPE_UNSIGNED_SHORT

            max_index = max(indices)

            if max_index < 65535:
                componentType = GLTF_COMPONENT_TYPE_UNSIGNED_SHORT
            elif max_index < 4294967295:
                componentType = GLTF_COMPONENT_TYPE_UNSIGNED_INT
            else:
                message = "A mesh contains too many vertices ({}) and needs to be split before export." \
                    .format(str(max_index))
                print_console('ERROR', message)
                continue

            if export_settings[export_keys.FORCE_INDICES]:
                componentType = export_settings[export_keys.INDICES]

            count = len(indices)

            type = GLTF_DATA_TYPE_SCALAR

            indices_index = generate_accessor(export_settings, glTF, indices, componentType, count,
                                              type, "ELEMENT_ARRAY_BUFFER")

            if indices_index < 0:
                print_console('ERROR', 'Could not create accessor for indices')
                continue

            primitive.indices = indices_index

            #

            internal_attributes = internal_primitive['attributes']

            #
            #

            internal_position = internal_attributes['POSITION']

            componentType = GLTF_COMPONENT_TYPE_FLOAT

            count = len(internal_position) // 3

            position = generate_accessor(export_settings, glTF, internal_position, componentType,
                                         count, GLTF_DATA_TYPE_VEC3, "ARRAY_BUFFER")

            if position < 0:
                print_console('ERROR', 'Could not create accessor for position')
                continue

            attributes['POSITION'] = position

            #

            if export_settings[export_keys.NORMALS]:
                internal_normal = internal_attributes['NORMAL']

                count = len(internal_normal) // 3

                normal = generate_accessor(export_settings, glTF, internal_normal,
                                           GLTF_COMPONENT_TYPE_FLOAT,
                                           count, GLTF_DATA_TYPE_VEC3, "ARRAY_BUFFER")

                if normal < 0:
                    print_console('ERROR', 'Could not create accessor for normal')
                    continue

                attributes['NORMAL'] = normal

            #

            if export_settings[export_keys.TANGENTS]:
                if internal_attributes.get('TANGENT') is not None:
                    internal_tangent = internal_attributes['TANGENT']

                    count = len(internal_tangent) // 4

                    tangent = generate_accessor(export_settings, glTF, internal_tangent,
                                                GLTF_COMPONENT_TYPE_FLOAT,
                                                count, GLTF_DATA_TYPE_VEC4, "ARRAY_BUFFER")

                    if tangent < 0:
                        print_console('ERROR', 'Could not create accessor for tangent')
                        continue

                    attributes['TANGENT'] = tangent

            #

            if export_settings[export_keys.TEX_COORDS]:
                texcoord_index = 0

                process_texcoord = True
                while process_texcoord:
                    texcoord_id = 'TEXCOORD_' + str(texcoord_index)

                    if internal_attributes.get(texcoord_id) is not None:
                        internal_texcoord = internal_attributes[texcoord_id]

                        count = len(internal_texcoord) // 2

                        texcoord = generate_accessor(export_settings, glTF, internal_texcoord,
                                                     GLTF_COMPONENT_TYPE_FLOAT, count, GLTF_DATA_TYPE_VEC2,
                                                     "ARRAY_BUFFER")

                        if texcoord < 0:
                            process_texcoord = False
                            print_console('ERROR', 'Could not create accessor for ' + texcoord_id)
                            continue

                        attributes[texcoord_id] = texcoord

                        texcoord_index += 1
                    else:
                        process_texcoord = False

            #

            if export_settings[export_keys.COLORS]:
                color_index = 0

                process_color = True
                while process_color:
                    color_id = 'COLOR_' + str(color_index)

                    if internal_attributes.get(color_id) is not None:
                        internal_color = internal_attributes[color_id]

                        count = len(internal_color) // 4

                        color = generate_accessor(export_settings, glTF, internal_color,
                                                  GLTF_COMPONENT_TYPE_FLOAT,
                                                  count, GLTF_DATA_TYPE_VEC4, "ARRAY_BUFFER")

                        if color < 0:
                            process_color = False
                            print_console('ERROR', 'Could not create accessor for ' + color_id)
                            continue

                        attributes[color_id] = color

                        color_index += 1
                    else:
                        process_color = False

            #

            if export_settings[export_keys.SKINS]:
                bone_index = 0

                process_bone = True
                while process_bone:
                    joint_id = 'JOINTS_' + str(bone_index)
                    weight_id = 'WEIGHTS_' + str(bone_index)

                    if internal_attributes.get(joint_id) is not None and internal_attributes.get(weight_id) is not None:
                        internal_joint = internal_attributes[joint_id]

                        count = len(internal_joint) // 4

                        joint = generate_accessor(export_settings, glTF, internal_joint,
                                                  GLTF_COMPONENT_TYPE_UNSIGNED_SHORT,
                                                  count, GLTF_DATA_TYPE_VEC4, "ARRAY_BUFFER")

                        if joint < 0:
                            process_bone = False
                            print_console('ERROR', 'Could not create accessor for ' + joint_id)
                            continue

                        attributes[joint_id] = joint

                        #
                        #

                        internal_weight = internal_attributes[weight_id]

                        count = len(internal_weight) // 4

                        weight = generate_accessor(
                            export_settings,
                            glTF,
                            internal_weight,
                            GLTF_COMPONENT_TYPE_FLOAT,
                            count,
                            GLTF_DATA_TYPE_VEC4,
                            "ARRAY_BUFFER"
                        )

                        if weight < 0:
                            process_bone = False
                            print_console('ERROR', 'Could not create accessor for ' + weight_id)
                            continue

                        attributes[weight_id] = weight

                        #
                        #

                        bone_index += 1
                    else:
                        process_bone = False

            #

            if export_settings[export_keys.MORPH]:
                if blender_mesh.shape_keys is not None:
                    targets = []

                    morph_index = 0
                    for blender_shape_key in blender_mesh.shape_keys.key_blocks:
                        if blender_shape_key != blender_shape_key.relative_key:

                            target_position_id = 'MORPH_POSITION_' + str(morph_index)
                            target_normal_id = 'MORPH_NORMAL_' + str(morph_index)
                            target_tangent_id = 'MORPH_TANGENT_' + str(morph_index)

                            if internal_attributes.get(target_position_id) is not None:
                                internal_target_position = internal_attributes[target_position_id]

                                count = len(internal_target_position) // 3

                                target_position = generate_accessor(
                                    export_settings,
                                    glTF,
                                    internal_target_position,
                                    GLTF_COMPONENT_TYPE_FLOAT,
                                    count,
                                    GLTF_DATA_TYPE_VEC3,
                                    ""
                                )

                                if target_position < 0:
                                    print_console('ERROR', 'Could not create accessor for ' + target_position_id)
                                    continue

                                #

                                target = {
                                    'POSITION': target_position
                                }

                                #

                                if export_settings[export_keys.NORMALS] and export_settings[export_keys.MORPH_NORMAL] \
                                        and internal_attributes.get(target_normal_id) is not None:

                                    internal_target_normal = internal_attributes[target_normal_id]

                                    count = len(internal_target_normal) // 3

                                    target_normal = generate_accessor(
                                        export_settings,
                                        glTF,
                                        internal_target_normal,
                                        GLTF_COMPONENT_TYPE_FLOAT,
                                        count,
                                        GLTF_DATA_TYPE_VEC3,
                                        ""
                                    )

                                    if target_normal < 0:
                                        print_console('ERROR', 'Could not create accessor for ' + target_normal_id)
                                        continue

                                    target['NORMAL'] = target_normal
                                #

                                if export_settings[export_keys.TANGENTS] and export_settings[export_keys.MORPH_TANGENT]\
                                        and internal_attributes.get(target_tangent_id) is not None:

                                    internal_target_tangent = internal_attributes[target_tangent_id]

                                    count = len(internal_target_tangent) // 3

                                    target_tangent = generate_accessor(
                                        export_settings,
                                        glTF,
                                        internal_target_tangent,
                                        GLTF_COMPONENT_TYPE_FLOAT,
                                        count,
                                        GLTF_DATA_TYPE_VEC3,
                                        "")

                                    if target_tangent < 0:
                                        print_console('ERROR', 'Could not create accessor for ' + target_tangent_id)
                                        continue

                                    target['TANGENT'] = target_tangent

                                #
                                #

                                targets.append(target)

                                morph_index += 1

                    if len(targets) > 0:
                        primitive.targets = targets

            #
            #

            primitives.append(primitive)

        #

        if export_settings[export_keys.EXTRAS]:
            extras = generate_extras(blender_mesh)

            if extras is not None:
                mesh.extras = extras

        #

        if export_settings[export_keys.MORPH]:
            if blender_mesh.shape_keys is not None:
                morph_max = len(blender_mesh.shape_keys.key_blocks) - 1
                if morph_max > 0:
                    weights = []
                    target_names = []

                    for blender_shape_key in blender_mesh.shape_keys.key_blocks:
                        if blender_shape_key != blender_shape_key.relative_key:
                            weights.append(blender_shape_key.value)
                            target_names.append(blender_shape_key.name)

                    mesh.weights = weights

                    if not mesh.extras:
                        mesh.extras = {}

                    mesh.extras['targetNames'] = target_names

        #
        #

        meshes.append(mesh)

    #
    #

    if len(meshes) > 0:
        glTF.meshes = meshes


def generate_duplicate_mesh(glTF, blender_object):
    """
    Helper function for dublicating meshes with linked object materials.
    """

    if blender_object is None:
        return -1

    if not hasattr(blender_object, 'data'):
        return -1

    mesh_index = get_mesh_index(glTF, blender_object.data.name)

    if mesh_index == -1:
        return False

    copy_obj = glTF.meshes[mesh_index].to_dict()
    new_mesh = gltf2_io.Mesh.from_dict(copy.deepcopy(copy_obj))  # deep copy

    #

    primitives = new_mesh.primitives

    primitive_index = 0
    for blender_material_slot in blender_object.material_slots:
        if blender_material_slot.link == 'OBJECT':
            material = get_material_index(glTF, blender_material_slot.material.name)

            # Meshes/primitives without material are allowed.
            if material >= 0:
                primitives[primitive_index].material = material
            else:
                message = "Material {} not found." \
                          "Please assign glTF 2.0 material or enable Blinn-Phong material in export." \
                    .format(blender_material_slot.material.name)
                print_console('WARNING', message)

        primitive_index += 1

    #

    new_name = blender_object.data.name + '_' + blender_object.name

    new_mesh.name = new_name

    glTF.meshes.append(new_mesh)

    return get_mesh_index(glTF, new_name)


def generate_node_parameter(
        export_settings,
        matrix,
        node,
        node_type
):
    """
    Helper function for storing node parameters.
    """

    translation, rotation, scale = decompose_transition(matrix, node_type, export_settings)

    #

    if translation[0] != 0.0 or translation[1] != 0.0 or translation[2] != 0.0:
        node.translation = [translation[0], translation[1], translation[2]]

    #

    if rotation[0] != 0.0 or rotation[1] != 0.0 or rotation[2] != 0.0 or rotation[3] != 1.0:
        node.rotation = [rotation[0], rotation[1], rotation[2], rotation[3]]

    #

    if scale[0] != 1.0 or scale[1] != 1.0 or scale[2] != 1.0:
        node.scale = [scale[0], scale[1], scale[2]]


def generate_node_instance(context,
                           export_settings,
                           glTF,
                           nodes,
                           blender_object,
                           force_visible):
    """
    Helper function for storing node instances.
    """

    correction_quaternion = convert_swizzle_rotation(mathutils.Quaternion((1.0, 0.0, 0.0), math.radians(-90.0)),
                                                     export_settings)

    #
    # Property: node
    #

    node = gltf2_io.Node(
        camera=None,
        children=None,
        extensions=None,
        extras=None,
        matrix=None,
        mesh=None,
        name=None,
        rotation=None,
        scale=None,
        skin=None,
        translation=None,
        weights=None
    )

    #
    #

    generate_node_parameter(export_settings, blender_object.matrix_local, node, 'NODE')

    #
    #

    if export_settings[export_keys.LAYERS] or blender_object.layers[0] or force_visible:

        #
        #

        if blender_object.type in ('MESH', 'CURVE', 'FONT'):
            mesh = get_mesh_index(glTF, blender_object.data.name)

            if mesh >= 0:

                need_duplicate = False

                if blender_object.material_slots:
                    for blender_material_slot in blender_object.material_slots:
                        if blender_material_slot.link == 'OBJECT':
                            need_duplicate = True
                            break

                if need_duplicate:
                    mesh = generate_duplicate_mesh(glTF, blender_object)

                #

                if mesh >= 0:
                    node.mesh = mesh

        #
        #

        if export_settings[export_keys.CAMERAS]:
            if blender_object.type == 'CAMERA':
                camera = get_camera_index(glTF, blender_object.data.name)

                if camera >= 0:
                    if export_settings[export_keys.YUP]:
                        # Add correction node for camera, as default direction is different to Blender.
                        correction_node = gltf2_io.Node(
                            camera=None,
                            children=None,
                            extensions=None,
                            extras=None,
                            matrix=None,
                            mesh=None,
                            name=None,
                            rotation=None,
                            scale=None,
                            skin=None,
                            translation=None,
                            weights=None
                        )

                        correction_node.name = 'Correction_' + blender_object.name
                        correction_node.rotation = [correction_quaternion[1], correction_quaternion[2],
                                                    correction_quaternion[3], correction_quaternion[0]]

                        correction_node.camera = camera

                        nodes.append(correction_node)
                    else:
                        node.camera = camera

        if export_settings[export_keys.LIGHTS]:
            if blender_object.type == 'LAMP':
                light = get_light_index(glTF, blender_object.data.name)
                if light >= 0:
                    khr_lights_punctual = {'light': light}
                    extensions = {'KHR_lights_punctual': khr_lights_punctual}

                    if export_settings[export_keys.YUP]:
                        # Add correction node for light, as default direction is different to Blender.
                        correction_node = gltf2_io.Node(
                            camera=None,
                            children=None,
                            extensions=None,
                            extras=None,
                            matrix=None,
                            mesh=None,
                            name=None,
                            rotation=None,
                            scale=None,
                            skin=None,
                            translation=None,
                            weights=None
                        )

                        correction_node.name = 'Correction_' + blender_object.name
                        correction_node.rotation = [correction_quaternion[1], correction_quaternion[2],
                                                    correction_quaternion[3], correction_quaternion[0]]

                        correction_node.extensions = extensions

                        nodes.append(correction_node)
                    else:
                        node.extensions = extensions

    #

    if export_settings[export_keys.EXTRAS]:
        extras = generate_extras(blender_object)

        if extras is not None:
            node.extras = extras

            #

    node.name = blender_object.name

    #

    return node


def generate_nodes(operator,
                   context,
                   export_settings,
                   glTF):
    """
    Generates the top level nodes entry.
    """

    nodes = []

    skins = []

    #
    #

    filtered_objects = export_settings[export_keys.FILTERED_OBJECTS]

    for blender_object in filtered_objects:
        node = generate_node_instance(context, export_settings, glTF, nodes, blender_object, False)

        #
        #

        nodes.append(node)

    #
    #

    for blender_object in filtered_objects:
        if blender_object.dupli_type == 'GROUP' and blender_object.dupli_group is not None:

            if export_settings[export_keys.LAYERS] or \
                    (blender_object.layers[0] and blender_object.dupli_group.layers[0]):

                for blender_dupli_object in blender_object.dupli_group.objects:
                    node = generate_node_instance(context, export_settings, glTF, nodes, blender_dupli_object,
                                                  True)

                    node.name = 'Duplication_' + blender_object.name + '_' + blender_dupli_object.name

                    #
                    #

                    nodes.append(node)

                #

                node = gltf2_io.Node(
                    camera=None,
                    children=None,
                    extensions=None,
                    extras=None,
                    matrix=[],
                    mesh=None,
                    name=None,
                    rotation=None,
                    scale=None,
                    skin=None,
                    translation=None,
                    weights=None
                )

                node.name = 'Duplication_Offset_' + blender_object.name

                translation = convert_swizzle_location(blender_object.dupli_group.dupli_offset, export_settings)

                node.translation = [-translation[0], -translation[1], -translation[2]]

                nodes.append(node)

    #
    #

    if len(nodes) > 0:
        glTF.nodes = nodes

    #
    #

    if export_settings[export_keys.SKINS]:
        for blender_object in filtered_objects:
            if blender_object.type != 'ARMATURE' or len(blender_object.pose.bones) == 0:
                continue

            temp_action = None

            if export_settings[export_keys.BAKE_SKINS] and not export_settings[export_keys.ANIMATIONS]:
                # TODO: this has to be added to the gather animation/ skins
                if blender_object.animation_data is not None:
                    temp_action = blender_object.animation_data.action

                bpy.context.scene.objects.active = blender_object
                bpy.ops.object.mode_set(mode='POSE')
                bpy.ops.nla.bake(frame_start=bpy.context.scene.frame_current, frame_end=bpy.context.scene.frame_current,
                                 only_selected=False, visual_keying=True, clear_constraints=False,
                                 use_current_action=False, bake_types={'POSE'})

            joints = []

            joints_written = False

            #

            children_list = list(blender_object.children)

            for blender_check_object in filtered_objects:
                blender_check_armature = blender_check_object.find_armature()

                if blender_check_armature is not None and blender_check_object not in children_list:
                    children_list.append(blender_check_object)

            #

            for blender_object_child in children_list:
                #
                # Property: skin and node
                #

                inverse_matrices = []

                for blender_bone in blender_object.pose.bones:

                    if export_settings[export_keys.YUP]:
                        axis_basis_change = mathutils.Matrix(
                            ((1.0, 0.0, 0.0, 0.0), (0.0, 0.0, 1.0, 0.0), (0.0, -1.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0)))
                    else:
                        axis_basis_change = mathutils.Matrix.Identity(4)

                    if not joints_written:
                        node = gltf2_io.Node(
                            camera=None,
                            children=None,
                            extensions=None,
                            extras=None,
                            matrix=None,
                            mesh=None,
                            name=None,
                            rotation=None,
                            scale=None,
                            skin=None,
                            translation=None,
                            weights=None
                        )

                        if blender_bone.parent is None:
                            correction_matrix_local = axis_basis_change * blender_bone.bone.matrix_local
                        else:
                            inverted_parent = blender_bone.parent.bone.matrix_local.inverted()
                            correction_matrix_local = inverted_parent * blender_bone.bone.matrix_local

                        matrix_basis = blender_bone.matrix_basis

                        if export_settings[export_keys.BAKE_SKINS]:
                            matrix_basis = blender_object.convert_space(blender_bone, blender_bone.matrix,
                                                                        from_space='POSE', to_space='LOCAL')

                        generate_node_parameter(export_settings, correction_matrix_local * matrix_basis, node, 'JOINT')

                        #

                        node.name = blender_object.name + "_" + blender_bone.name

                        #
                        #

                        joints.append(len(nodes))

                        nodes.append(node)

                    #
                    #

                    world_inverted = blender_object.matrix_world.inverted()
                    child_world = blender_object_child.matrix_world
                    bind_shape_matrix = axis_basis_change * world_inverted * child_world * axis_basis_change.inverted()

                    inverse_bind_matrix = axis_basis_change * blender_bone.bone.matrix_local
                    inverse_bind_matrix = inverse_bind_matrix.inverted() * bind_shape_matrix

                    for column in range(0, 4):
                        for row in range(0, 4):
                            inverse_matrices.append(inverse_bind_matrix[row][column])

                #

                joints_written = True

                #

                skin = gltf2_io.Skin(
                    extensions=None,
                    extras=None,
                    inverse_bind_matrices=None,
                    joints=None,
                    name=None,
                    skeleton=None
                )

                skin.skeleton = get_node_index(glTF, blender_object.name)

                skin.joints = joints

                #
                count = len(inverse_matrices) // 16

                inverseBindMatrices = generate_accessor(
                    export_settings,
                    glTF,
                    inverse_matrices,
                    GLTF_COMPONENT_TYPE_FLOAT,
                    count,
                    GLTF_DATA_TYPE_MAT4,
                    ""
                )

                skin.inverse_bind_matrices = inverseBindMatrices

                #

                skins.append(skin)

            #

            if temp_action is not None:
                blender_object.animation_data.action = temp_action

    #
    #

    if len(skins) > 0:
        glTF.skins = skins

    #
    # Resolve children etc.
    #

    for blender_object in filtered_objects:
        node_index = get_node_index(glTF, blender_object.name)

        node = nodes[node_index]

        #

        if export_settings[export_keys.SKINS]:
            blender_armature = blender_object.find_armature()
            if blender_armature is not None:

                if blender_object in blender_armature.children:
                    index_offset = blender_armature.children.index(blender_object)
                else:
                    index_local_offset = 0

                    for blender_check_object in filtered_objects:
                        blender_check_armature = blender_check_object.find_armature()
                        if blender_check_armature == blender_armature:
                            index_local_offset += 1

                        if blender_object == blender_check_object:
                            index_local_offset -= 1
                            break

                    index_offset = len(blender_armature.children) + index_local_offset

                node.skin = get_skin_index(glTF, blender_armature.name, index_offset)

        #

        children = []

        # Camera
        if export_settings[export_keys.CAMERAS]:
            if blender_object.type == 'CAMERA':
                child_index = get_node_index(glTF, 'Correction_' + blender_object.name)
                if child_index >= 0:
                    children.append(child_index)

        # Light
        if export_settings[export_keys.LIGHTS]:
            if blender_object.type == 'LAMP':
                child_index = get_node_index(glTF, 'Correction_' + blender_object.name)
                if child_index >= 0:
                    children.append(child_index)

        # Nodes
        for blender_child_node in blender_object.children:
            child_index = get_node_index(glTF, blender_child_node.name)

            if blender_child_node.parent_type == 'BONE' and export_settings[export_keys.SKINS]:
                continue

            if child_index < 0:
                continue

            children.append(child_index)

        # Duplications
        if blender_object.dupli_type == 'GROUP' and blender_object.dupli_group is not None:

            child_index = get_node_index(glTF, 'Duplication_Offset_' + blender_object.name)
            if child_index >= 0:
                children.append(child_index)

                duplication_node = nodes[child_index]

                duplication_children = []

                for blender_dupli_object in blender_object.dupli_group.objects:
                    child_index = get_node_index(
                        glTF,
                        'Duplication_' + blender_object.name + '_' + blender_dupli_object.name
                    )
                    if child_index >= 0:
                        duplication_children.append(child_index)

                duplication_node.children = duplication_children

                #

        if export_settings[export_keys.SKINS]:
            # Joint
            if blender_object.type == 'ARMATURE' and len(blender_object.pose.bones) > 0:

                #

                blender_object_to_bone = {}

                if export_settings[export_keys.SKINS]:
                    for blender_child_node in blender_object.children:
                        if blender_child_node.parent_type == 'BONE':
                            blender_object_to_bone[blender_child_node.name] = blender_child_node.parent_bone

                #

                for blender_bone in blender_object.pose.bones:

                    if blender_bone.parent:
                        continue

                    child_index = get_node_index(glTF, blender_object.name + "_" + blender_bone.name)

                    if child_index < 0:
                        continue

                    children.append(child_index)

                for blender_bone in blender_object.pose.bones:
                    joint_children = []
                    for blender_bone_child in blender_bone.children:
                        child_index = get_node_index(glTF, blender_object.name + "_" + blender_bone_child.name)

                        if child_index < 0:
                            continue

                        joint_children.append(child_index)

                    for blender_object_name in blender_object_to_bone:
                        blender_bone_name = blender_object_to_bone[blender_object_name]
                        if blender_bone_name == blender_bone.name:
                            child_index = get_node_index(glTF, blender_object_name)

                            if child_index < 0:
                                continue

                            joint_children.append(child_index)

                    if len(joint_children) > 0:
                        node_index = get_node_index(glTF, blender_object.name + "_" + blender_bone.name)

                        child_node = nodes[node_index]

                        child_node.children = joint_children

        if len(children) > 0:
            node.children = children


def generate_images(operator,
                    context,
                    export_settings,
                    glTF):
    """
    Generates the top level images entry.
    """

    filtered_images = export_settings[export_keys.FILTERED_IMAGES]

    images = []

    #
    #

    for blender_image in filtered_images:
        #
        # Property: image
        #

        image = {'name': get_image_name(blender_image.name)}

        file_format = get_image_format(export_settings, blender_image)
        mime_type = 'image/jpeg' if file_format == 'JPEG' else 'image/png'

        #

        if export_settings[export_keys.FORMAT] == 'ASCII':

            if export_settings[export_keys.EMBED_IMAGES]:
                # Embed image as Base64.

                image_data = create_image_data(context, export_settings, blender_image, file_format)

                # Required

                image['mimeType'] = mime_type

                image['uri'] = 'data:' + mime_type + ';base64,' + base64.b64encode(image_data).decode('ascii')

            else:
                # Store image external.

                uri = get_image_uri(export_settings, blender_image)
                path = export_settings[export_keys.FILEDIRECTORY] + uri

                create_image_file(context, blender_image, path, file_format)

                # Required

                image['uri'] = uri

        else:
            # Store image as glb.

            image_data = create_image_data(context, export_settings, blender_image, file_format)

            bufferView = generate_bufferView(export_settings, glTF, image_data, 0, 0)

            # Required

            image['mimeType'] = mime_type

            image['bufferView'] = bufferView

        #
        #

        images.append(gltf2_io.Image.from_dict(image))

    filtered_merged_images = export_settings[export_keys.FILTERED_MERGED_IMAGES]

    for gltf2_image in filtered_merged_images:
        #
        # Property: image
        #

        image = {'name': get_image_name(gltf2_image.name)}

        # We can only write pngs from blender, so we have to stick to that
        mime_type = 'image/png'

        #

        if export_settings[export_keys.FORMAT] == 'ASCII':

            if export_settings[export_keys.EMBED_IMAGES]:
                # Embed image as Base64.

                image_data = gltf2_image.to_image_data(mime_type)

                # Required

                image['mimeType'] = mime_type

                image['uri'] = 'data:' + mime_type + ';base64,' + base64.b64encode(image_data).decode('ascii')

            else:
                # Store image external.

                uri = get_image_uri(export_settings, gltf2_image)
                path = export_settings[export_keys.FILEDIRECTORY] + uri

                gltf2_image.save_png(path)

                # Required

                image['uri'] = uri

        else:
            # Store image as glb.
            # We can only write pngs from blender, so we have to stick to that
            mime_type = 'image/png'
            image_data = gltf2_image.to_image_data(mime_type)

            bufferView = generate_bufferView(export_settings, glTF, image_data, 0, 0)

            # Required

            image['mimeType'] = mime_type

            image['bufferView'] = bufferView

        #
        #

        images.append(gltf2_io.Image.from_dict(image))
    #
    #

    if len(images) > 0:
        glTF.images = images


def generate_textures(operator,
                      context,
                      export_settings,
                      glTF):
    """
    Generates the top level textures entry.
    """

    filtered_textures = export_settings[export_keys.FILTERED_TEXTURES]

    textures = []

    #
    #

    for blender_texture in filtered_textures:
        #
        # Property: texture
        #

        texture = {}

        #

        if isinstance(blender_texture, bpy.types.ShaderNodeTexImage):
            magFilter = 9729
            if blender_texture.interpolation == 'Closest':
                magFilter = 9728
            wrap = 10497
            if blender_texture.extension == 'CLIP':
                wrap = 33071

            texture['sampler'] = generate_sampler(export_settings, glTF, magFilter, wrap)

            texture['source'] = get_image_index(glTF, blender_texture.image.name)

            #
            #

            textures.append(gltf2_io.Texture.from_dict(texture))

        elif isinstance(blender_texture, bpy.types.TextureSlot):
            magFilter = 9729
            wrap = 10497
            if blender_texture.texture.extension == 'CLIP':
                wrap = 33071

            texture['sampler'] = generate_sampler(export_settings, glTF, magFilter, wrap)

            texture['source'] = get_image_index(glTF, blender_texture.texture.image.name)

            #
            #

            textures.append(gltf2_io.Texture.from_dict(texture))

        else:
            print(blender_texture.name)
            magFilter = 9729
            wrap = 10497

            texture['sampler'] = generate_sampler(export_settings, glTF, magFilter, wrap)

            texture['source'] = get_image_index(glTF, blender_texture.name)

            #
            #

            textures.append(gltf2_io.Texture.from_dict(texture))

    #
    #

    if len(textures) > 0:
        glTF.textures = textures


def generate_scenes(export_settings,
                    glTF):
    """
    Generates the top level scenes entry.
    """

    scenes = []

    #

    for blender_scene in bpy.data.scenes:
        #
        # Property: scene
        #

        nodes = []

        scene = gltf2_io.Scene(
            extensions=None,
            extras=None,
            name=blender_scene.name,
            nodes=nodes
        )

        for blender_object in blender_scene.objects:
            if blender_object.parent is None:
                node_index = get_node_index(glTF, blender_object.name)

                if node_index < 0:
                    continue

                nodes.append(node_index)

        #

        if export_settings[export_keys.LIGHTS]:
            light = get_light_index(glTF, 'Ambient_' + blender_scene.name)
            if light >= 0:
                khr_lights_punctual = {'light': light}
                extensions = {'KHR_lights_punctual': khr_lights_punctual}
                scene.extensions = extensions

        #

        if export_settings[export_keys.EXTRAS]:
            extras = generate_extras(blender_scene.world)

            if extras is not None:
                scene.extras = extras

                #

        #
        #

        scenes.append(scene)

    #
    #

    if len(scenes) > 0:
        glTF.scenes = scenes


def generate_scene(glTF):
    """
    Generates the top level scene entry.
    """

    index = get_scene_index(glTF, bpy.context.screen.scene.name)

    #
    #

    if index >= 0:
        glTF.scene = index


def generate_glTF(operator,
                  context,
                  export_settings,
                  glTF):
    """
    Generates the main glTF structure.
    """

    profile_start()
    generate_asset(export_settings, glTF)
    profile_end('asset')
    bpy.context.window_manager.progress_update(5)

    #

    if export_settings[export_keys.MATERIALS]:
        profile_start()
        generate_images(operator, context, export_settings, glTF)
        profile_end('images')
        bpy.context.window_manager.progress_update(10)

        profile_start()
        generate_textures(operator, context, export_settings, glTF)
        profile_end('textures')
        bpy.context.window_manager.progress_update(20)

        profile_start()
        generate_materials(operator, context, export_settings, glTF)
        profile_end('materials')
        bpy.context.window_manager.progress_update(30)

    bpy.context.window_manager.progress_update(30)

    #

    if export_settings[export_keys.CAMERAS]:
        profile_start()
        generate_cameras(export_settings, glTF)
        profile_end('cameras')
        bpy.context.window_manager.progress_update(40)

    if export_settings[export_keys.LIGHTS]:
        profile_start()
        generate_lights(operator, context, export_settings, glTF)
        profile_end('lights')
        bpy.context.window_manager.progress_update(50)

    bpy.context.window_manager.progress_update(50)

    #

    profile_start()
    generate_meshes(operator, context, export_settings, glTF)
    profile_end('meshes')
    bpy.context.window_manager.progress_update(60)

    #

    profile_start()
    generate_nodes(operator, context, export_settings, glTF)
    profile_end('nodes')
    bpy.context.window_manager.progress_update(70)

    #

    if export_settings[export_keys.ANIMATIONS]:
        profile_start()
        generate_animations(operator, context, export_settings, glTF)
        profile_end('animations')
        bpy.context.window_manager.progress_update(80)

    bpy.context.window_manager.progress_update(80)

    #

    profile_start()
    generate_scenes(export_settings, glTF)
    profile_end('scenes')

    bpy.context.window_manager.progress_update(95)

    profile_start()
    generate_scene(glTF)
    profile_end('scene')

    bpy.context.window_manager.progress_update(100)

    #

    byteLength = len(export_settings[export_keys.BINARY])

    if byteLength > 0:
        glTF.buffers = []

        buffer = {
            'byteLength': byteLength
        }

        if export_settings[export_keys.FORMAT] == 'ASCII':
            uri = export_settings[export_keys.BINARY_FILENAME]

            if export_settings[export_keys.EMBED_BUFFERS]:
                uri = 'data:application/octet-stream;base64,' + base64.b64encode(
                    export_settings[export_keys.BINARY]).decode('ascii')

            buffer['uri'] = uri

        glTF.buffers.append(gltf2_io.Buffer.from_dict(buffer))
