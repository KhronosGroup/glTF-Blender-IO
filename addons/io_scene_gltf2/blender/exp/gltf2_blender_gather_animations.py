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

from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached
from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.blender.exp import gltf2_blender_gather_animation_channels


def gather_animations(blender_object: bpy.types.Object, export_settings) -> typing.List[gltf2_io.Animation]:
    """
    Gather all animations which contribute to the objects property
    :param blender_object: The blender object which is animated
    :param export_settings:
    :return: A list of glTF2 animations
    """

    if blender_object.animation_data is None:
        return []

    animations = typing.List[gltf2_io.Animation]()

    # Collect all 'actions' affecting this object. There is a direct mapping between blender actions and glTF animations
    blender_actions = __get_blender_actions(blender_object)

    # Export all collected actions.
    for blender_action in blender_actions:
        animation = __gather_animation(blender_object, blender_action, export_settings)
        if animation is not None:
            animations.append(animation)

    return animations


def __gather_animation(blender_object: bpy.types.Object, blender_action: bpy.types.Action, export_settings):
    if not __filter_animation(blender_object, blender_action, export_settings):
        return None

    animation = gltf2_io.Animation(
        channels=__gather_channels(blender_object, blender_action, export_settings),
        extensions=__gather_extensions(blender_object, blender_action, export_settings),
        extras=__gather_extras(blender_object, blender_action, export_settings),
        name=__gather_name(blender_object, blender_action, export_settings),
        samplers=__gather_samplers(blender_object, blender_action, export_settings)
    )


def __filter_animation(blender_object, blender_action, export_settings) -> bool:
    if blender_action.users == 0:
        return False

    return True


def __gather_channels(blender_object, blender_action, export_settings):
    return gltf2_blender_gather_animation_channels.gather_animation_channels(blender_object, blender_action, export_settings)


def __gather_extensions(blender_object, blender_action, export_settings):
    return None


def __gather_extras(blender_object, blender_action, export_settings):
    return None


def __gather_name(blender_object, blender_action, export_settings):
    return None


def __gather_samplers(blender_object, blender_action, export_settings):
    # We need to gather the samplers after gathering all channels --> populate this list in __link_samplers
    return []


def __link_samplers(animation: gltf2_io.Animation, export_settings):
    """
    After gathering, samplers are stored in the channels properties of the animation and need to be moved
    to their own list while storing an index into this list at the position where they previously were.
    This behaviour is similar to that of the glTFExporter that traverses all nodes
    :param animation:
    :param export_settings:
    :return:
    """





def __get_blender_actions(blender_object: bpy.types.Object) -> typing.List[bpy.types.Action]:
    blender_actions = []

    # Collect active action.
    if blender_object.animation_data.action is not None:
        blender_actions.append(blender_object.animation_data.action)
    # Collect associated strips from NLA tracks.
    for track in blender_object.animation_data.nla_tracks:
        # Multi-strip tracks do not export correctly yet (they need to be baked),
        # so skip them for now and only write single-strip tracks.
        if track.strips is None or len(track.strips) != 1:
            continue
        for strip in track.strips:
            blender_actions.append(strip.action)
    # Remove duplicate actions.
    blender_actions = list(set(blender_actions))

    return blender_actions


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