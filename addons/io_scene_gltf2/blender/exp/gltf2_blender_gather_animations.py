# Copyright (c) 2018 The Khronos Group Inc.
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

import mathutils

from io_scene_gltf2.blender.exp.gltf2_blender_gather import cached
from io_scene_gltf2.io.com import gltf2_io


@cached
def gather_animations(blender_object, export_settings):
    """
    Gather all animations which contribute to the objects property
    :param blender_object: The blender object which is animated
    :param export_settings:
    :return: A list of glTF2 animations
    """
    if not __filter_animation(blender_object, export_settings):
        return None

    return gltf2_io.Animation(
        channels=__gather_channels(blender_object, export_settings),
        extensions=__gather_extensions(blender_object, export_settings),
        extras=__gather_extras(blender_object, export_settings),
        name=__gather_name(blender_object, export_settings),
        samplers=__gather_samples(blender_object, export_settings)
    )


def __filter_animation(blender_object, export_settings):
    if blender_object.animation_data is None:
        return False

    return True


def __gather_channels(blender_object, export_settings):
    return None


def __gather_extensions(blender_object, export_settings):
    return None


def __gather_extras(blender_object, export_settings):
    return None


def __gather_name(blender_object, export_settings):
    return None


def __gather_samples(blender_object, export_settings):
    return None


def __gather_actions(blender_object, export_settings):

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

            __process_object_animations(blender_object, export_settings, action)

            animation_data.action = active_action


def __process_object_animations(blender_object, export_settings, action):
    correction_matrix_local = blender_object.matrix_parent_inverse
    matrix_basis = mathutils.Matrix.Identity(4)

    #

    if export_settings['gltf_bake_skins']:
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
    gltf_joint_cache = export_settings['gltf_joint_cache']
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

    if export_settings['gltf_skins']:
        if blender_object.type == 'ARMATURE' and len(blender_object.pose.bones) > 0:

            #

            if export_settings['gltf_yup']:
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