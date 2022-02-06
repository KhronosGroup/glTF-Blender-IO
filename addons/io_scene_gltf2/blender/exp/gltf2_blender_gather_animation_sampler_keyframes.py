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
import mathutils
import typing

from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached, bonecache, objectcache
from io_scene_gltf2.blender.com import gltf2_blender_math
from io_scene_gltf2.blender.exp import gltf2_blender_get
from io_scene_gltf2.blender.exp.gltf2_blender_gather_drivers import get_sk_drivers, get_sk_driver_values
from . import gltf2_blender_export_keys
from io_scene_gltf2.io.com import gltf2_io_debug
from io_scene_gltf2.blender.exp.gltf2_blender_gather_tree import VExportNode
import numpy as np


class Keyframe:
    def __init__(self, channels: typing.Tuple[bpy.types.FCurve], frame: float, bake_channel: typing.Union[str, None]):
        self.seconds = frame / bpy.context.scene.render.fps
        self.frame = frame
        self.fps = bpy.context.scene.render.fps
        self.__length_morph = 0
        # Note: channels has some None items only for SK if some SK are not animated
        if bake_channel is None:
            self.target = [c for c in channels if c is not None][0].data_path.split('.')[-1]
            if self.target != "value":
                self.__indices = [c.array_index for c in channels]
            else:
                self.__indices = [i for i, c in enumerate(channels) if c is not None]
                self.__length_morph = len(channels)
        else:
            self.target = bake_channel
            self.__indices = []
            for i in range(self.get_target_len()):
                self.__indices.append(i)


        # Data holders for virtual properties
        self.__value = None
        self.__in_tangent = None
        self.__out_tangent = None

    def get_target_len(self):
        length = {
            "delta_location": 3,
            "delta_rotation_euler": 3,
            "location": 3,
            "rotation_axis_angle": 4,
            "rotation_euler": 3,
            "rotation_quaternion": 4,
            "scale": 3,
            "value": self.__length_morph
        }.get(self.target)

        if length is None:
            raise RuntimeError("Animations with target type '{}' are not supported.".format(self.target))

        return length

    def __set_indexed(self, value):
        # Sometimes blender animations only reference a subset of components of a data target. Keyframe should always
        # contain a complete Vector/ Quaternion --> use the array_index value of the keyframe to set components in such
        # structures
        # For SK, must contains all SK values
        result = [0.0] * self.get_target_len()
        for i, v in zip(self.__indices, value):
            result[i] = v
        return result

    def get_indices(self):
        return self.__indices

    def set_value_index(self, idx, val):
        self.__value[idx] = val

    def set_value_index_in(self, idx, val):
        self.__in_tangent[idx] = val

    def set_value_index_out(self, idx, val):
        self.__out_tangent[idx] = val

    def set_first_tangent(self):
        self.__in_tangent = self.__value

    def set_last_tangent(self):
        self.__out_tangent = self.__value

    @property
    def value(self) -> typing.Union[mathutils.Vector, mathutils.Euler, mathutils.Quaternion, typing.List[float]]:
        if self.target == "value":
            return self.__value
        return gltf2_blender_math.list_to_mathutils(self.__value, self.target)

    @value.setter
    def value(self, value: typing.List[float]):
        self.__value = self.__set_indexed(value)

    @value.setter
    def value_total(self, value: typing.List[float]):
        self.__value = value

    @property
    def in_tangent(self) -> typing.Union[mathutils.Vector, mathutils.Euler, mathutils.Quaternion, typing.List[float]]:
        if self.__in_tangent is None:
            return None
        if self.target == "value":
            return self.__in_tangent
        return gltf2_blender_math.list_to_mathutils(self.__in_tangent, self.target)

    @in_tangent.setter
    def in_tangent(self, value: typing.List[float]):
        self.__in_tangent = self.__set_indexed(value)

    @property
    def out_tangent(self) -> typing.Union[mathutils.Vector, mathutils.Euler, mathutils.Quaternion, typing.List[float]]:
        if self.__out_tangent is None:
            return None
        if self.target == "value":
            return self.__out_tangent
        return gltf2_blender_math.list_to_mathutils(self.__out_tangent, self.target)

    @out_tangent.setter
    def out_tangent(self, value: typing.List[float]):
        self.__out_tangent = self.__set_indexed(value)


@objectcache
def get_object_matrix(blender_obj_uuid: str,
                      action_name: str,
                      bake_range_start: int,
                      bake_range_end: int,
                      current_frame: int,
                      step: int,
                      export_settings
                    ):

    data = {}


    # If we bake (because export selection), we don't know exactly the frame range, 
    # So using min / max of all actions

    if export_settings['gltf_selected'] is True and export_settings['vtree'].tree_troncated is True:
        start_frame = min([v[0] for v in [a.frame_range for a in bpy.data.actions]])
        end_frame = max([v[1] for v in [a.frame_range for a in bpy.data.actions]])
    else:
        start_frame  = bake_range_start
        end_frame = bake_range_end

    frame = start_frame
    while frame <= end_frame:
        bpy.context.scene.frame_set(int(frame))

        for obj_uuid in [uid for (uid, n) in export_settings['vtree'].nodes.items() if n.blender_type not in [VExportNode.BONE]]:
            blender_obj = export_settings['vtree'].nodes[obj_uuid].blender_object

            # if this object is not animated, do not skip :
            # We need this object too in case of bake

            # calculate local matrix
            if export_settings['vtree'].nodes[obj_uuid].parent_uuid is None:
                parent_mat = mathutils.Matrix.Identity(4).freeze()
            else:
                if export_settings['vtree'].nodes[export_settings['vtree'].nodes[obj_uuid].parent_uuid].blender_type not in [VExportNode.BONE]:
                    parent_mat = export_settings['vtree'].nodes[export_settings['vtree'].nodes[obj_uuid].parent_uuid].blender_object.matrix_world
                else:
                    # Object animated is parented to a bone
                    blender_bone = export_settings['vtree'].nodes[export_settings['vtree'].nodes[obj_uuid].parent_bone_uuid].blender_bone
                    armature_object = export_settings['vtree'].nodes[export_settings['vtree'].nodes[export_settings['vtree'].nodes[obj_uuid].parent_bone_uuid].armature].blender_object
                    axis_basis_change = mathutils.Matrix(
                        ((1.0, 0.0, 0.0, 0.0), (0.0, 0.0, 1.0, 0.0), (0.0, -1.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0)))

                    parent_mat = armature_object.matrix_world @ blender_bone.matrix @ axis_basis_change
              
            #For object inside collection (at root), matrix world is already expressed regarding collection parent
            if export_settings['vtree'].nodes[obj_uuid].parent_uuid is not None and export_settings['vtree'].nodes[export_settings['vtree'].nodes[obj_uuid].parent_uuid].blender_type == VExportNode.COLLECTION:
                parent_mat = mathutils.Matrix.Identity(4).freeze()

            mat = parent_mat.inverted_safe() @ blender_obj.matrix_world

            if obj_uuid not in data.keys():
                data[obj_uuid] = {}
            
            if blender_obj.animation_data and blender_obj.animation_data.action:
                if blender_obj.animation_data.action.name not in data[obj_uuid].keys():
                    data[obj_uuid][blender_obj.animation_data.action.name] = {}
                data[obj_uuid][blender_obj.animation_data.action.name][frame] = mat
            else:
                # case of baking selected object.
                # There is no animation, so use uuid of object as key
                if obj_uuid not in data[obj_uuid].keys():
                    data[obj_uuid][obj_uuid] = {}
                data[obj_uuid][obj_uuid][frame] = mat

        frame += step
    return data

@bonecache
def get_bone_matrix(blender_obj_uuid_if_armature: typing.Optional[str],
                     channels: typing.Tuple[bpy.types.FCurve],
                     bake_bone: typing.Union[str, None],
                     bake_channel: typing.Union[str, None],
                     bake_range_start,
                     bake_range_end,
                     action_name: str,
                     current_frame: int,
                     step: int,
                     export_settings
                     ):

    blender_object_if_armature = export_settings['vtree'].nodes[blender_obj_uuid_if_armature].blender_object if blender_obj_uuid_if_armature is not None else None
    data = {}

    # Always using bake_range, because some bones may need to be baked,
    # even if user didn't request it

    start_frame = bake_range_start
    end_frame = bake_range_end


    frame = start_frame
    while frame <= end_frame:
        data[frame] = {}
        bpy.context.scene.frame_set(int(frame))
        bones = export_settings['vtree'].get_all_bones(blender_obj_uuid_if_armature)

        for bone_uuid in bones:
            blender_bone = export_settings['vtree'].nodes[bone_uuid].blender_bone

            if export_settings['vtree'].nodes[bone_uuid].parent_uuid is not None and export_settings['vtree'].nodes[export_settings['vtree'].nodes[bone_uuid].parent_uuid].blender_type == VExportNode.BONE:
                blender_bone_parent = export_settings['vtree'].nodes[export_settings['vtree'].nodes[bone_uuid].parent_uuid].blender_bone
                rest_mat = blender_bone_parent.bone.matrix_local.inverted_safe() @ blender_bone.bone.matrix_local
                matrix = rest_mat.inverted_safe() @ blender_bone_parent.matrix.inverted_safe() @ blender_bone.matrix
            else:
                matrix = blender_bone.bone.matrix_local.inverted_safe() @ blender_bone.matrix

            data[frame][blender_bone.name] = matrix


        # If some drivers must be evaluated, do it here, to avoid to have to change frame by frame later
        drivers_to_manage = get_sk_drivers(blender_obj_uuid_if_armature, export_settings)
        for dr_obj_uuid, dr_fcurves in drivers_to_manage:
            vals = get_sk_driver_values(dr_obj_uuid, frame, dr_fcurves, export_settings)

        frame += step

    return data

# cache for performance reasons
# This function is called 2 times, for input (timing) and output (key values)
@cached
def gather_keyframes(blender_obj_uuid: str,
                     is_armature: bool,
                     channels: typing.Tuple[bpy.types.FCurve],
                     non_keyed_values: typing.Tuple[typing.Optional[float]],
                     bake_bone: typing.Union[str, None],
                     bake_channel: typing.Union[str, None],
                     bake_range_start,
                     bake_range_end,
                     force_range: bool,
                     action_name: str,
                     driver_obj_uuid,
                     node_channel_is_animated: bool,
                     export_settings
                     ) -> typing.Tuple[typing.List[Keyframe], bool]:
    """Convert the blender action groups' fcurves to keyframes for use in glTF."""

    blender_object_if_armature = export_settings['vtree'].nodes[blender_obj_uuid].blender_object if is_armature is True is not None else None
    blender_obj_uuid_if_armature = blender_obj_uuid if is_armature is True else None

    if force_range is True:
        start_frame = bake_range_start
        end_frame = bake_range_end
    else:
        if bake_bone is None and driver_obj_uuid is None:
            # Find the start and end of the whole action group
            # Note: channels has some None items only for SK if some SK are not animated
            ranges = [channel.range() for channel in channels if channel is not None]

            if len(channels) != 0:
                start_frame = min([channel.range()[0] for channel in channels  if channel is not None])
                end_frame = max([channel.range()[1] for channel in channels  if channel is not None])
            else:
                start_frame = bake_range_start
                end_frame = bake_range_end
        else:
            start_frame = bake_range_start
            end_frame = bake_range_end

    keyframes = []
    baking_is_needed = needs_baking(blender_object_if_armature, channels, export_settings)
    if baking_is_needed:
        # Bake the animation, by evaluating the animation for all frames

        if blender_object_if_armature is not None and driver_obj_uuid is None:
            if bake_bone is None:
                pose_bone_if_armature = gltf2_blender_get.get_object_from_datapath(blender_object_if_armature,
                                                                               channels[0].data_path)
            else:
                pose_bone_if_armature = blender_object_if_armature.pose.bones[bake_bone]
        else:
            pose_bone_if_armature = None

        # sample all frames
        frame = start_frame
        step = export_settings['gltf_frame_step']
        while frame <= end_frame:
            key = Keyframe(channels, frame, bake_channel)
            if isinstance(pose_bone_if_armature, bpy.types.PoseBone):

                mat = get_bone_matrix(
                    blender_obj_uuid_if_armature,
                    channels,
                    bake_bone,
                    bake_channel,
                    bake_range_start,
                    bake_range_end,
                    action_name,
                    frame,
                    step,
                    export_settings
                )
                trans, rot, scale = mat.decompose()

                if bake_channel is None:
                    target_property = channels[0].data_path.split('.')[-1]
                else:
                    target_property = bake_channel
                key.value = {
                    "location": trans,
                    "rotation_axis_angle": rot,
                    "rotation_euler": rot,
                    "rotation_quaternion": rot,
                    "scale": scale
                }[target_property]
            else:
                if driver_obj_uuid is None:
                    # If channel is TRS, we bake from world matrix, else this is SK
                    if len(channels) != 0:
                        target = [c for c in channels if c is not None][0].data_path.split('.')[-1]
                    else:
                        target = bake_channel
                    if target == "value": #SK
                        # Note: channels has some None items only for SK if some SK are not animated
                        key.value = [c.evaluate(frame) for c in channels if c is not None]
                        complete_key(key, non_keyed_values)
                    else:

                        mat = get_object_matrix(blender_obj_uuid,
                                action_name,
                                bake_range_start,
                                bake_range_end,
                                frame,
                                step,
                                export_settings)

                        trans, rot, sca = mat.decompose()
                        key.value_total = {
                            "location": trans,
                            "rotation_axis_angle": [rot.to_axis_angle()[1], rot.to_axis_angle()[0][0], rot.to_axis_angle()[0][1], rot.to_axis_angle()[0][2]],
                            "rotation_euler": rot.to_euler(),
                            "rotation_quaternion": rot,
                            "scale": sca
                        }[target]
                else:
                    key.value = get_sk_driver_values(driver_obj_uuid, frame, channels, export_settings)
                    complete_key(key, non_keyed_values)
            keyframes.append(key)
            frame += step
    else:
        # Just use the keyframes as they are specified in blender
        # Note: channels has some None items only for SK if some SK are not animated
        frames = [keyframe.co[0] for keyframe in [c for c in channels if c is not None][0].keyframe_points]
        # some weird files have duplicate frame at same time, removed them
        frames = sorted(set(frames))
        if force_range is True:
            frames = [f for f in frames if f >= bake_range_start and f <= bake_range_end]
        for i, frame in enumerate(frames):
            key = Keyframe(channels, frame, bake_channel)
            # key.value = [c.keyframe_points[i].co[0] for c in action_group.channels]
            key.value = [c.evaluate(frame) for c in channels if c is not None]
            # Complete key with non keyed values, if needed
            if len([c for c in channels if c is not None]) != key.get_target_len():
                complete_key(key, non_keyed_values)

            # compute tangents for cubic spline interpolation
            if [c for c in channels if c is not None][0].keyframe_points[0].interpolation == "BEZIER":
                # Construct the in tangent
                if frame == frames[0]:
                    # start in-tangent should become all zero
                    key.set_first_tangent()
                else:
                    # otherwise construct an in tangent coordinate from the keyframes control points. We intermediately
                    # use a point at t-1 to define the tangent. This allows the tangent control point to be transformed
                    # normally
                    key.in_tangent = [
                        c.keyframe_points[i].co[1] + ((c.keyframe_points[i].co[1] - c.keyframe_points[i].handle_left[1]
                                                       ) / (frame - frames[i - 1]))
                        for c in channels if c is not None
                    ]
                # Construct the out tangent
                if frame == frames[-1]:
                    # end out-tangent should become all zero
                    key.set_last_tangent()
                else:
                    # otherwise construct an in tangent coordinate from the keyframes control points. We intermediately
                    # use a point at t+1 to define the tangent. This allows the tangent control point to be transformed
                    # normally
                    key.out_tangent = [
                        c.keyframe_points[i].co[1] + ((c.keyframe_points[i].handle_right[1] - c.keyframe_points[i].co[1]
                                                       ) / (frames[i + 1] - frame))
                        for c in channels if c is not None
                    ]

                complete_key_tangents(key, non_keyed_values)

            keyframes.append(key)

    # For armature only
    # Check if all values are the same
    # In that case, if there is no real keyframe on this channel for this given bone,
    # We can ignore this keyframes
    # if there are some fcurve, we can keep only 2 keyframes, first and last
    if blender_object_if_armature is not None:
        cst = fcurve_is_constant(keyframes)

        if node_channel_is_animated is True: # fcurve on this bone for this property
             # Keep animation, but keep only 2 keyframes if data are not changing
             return ([keyframes[0], keyframes[-1]], baking_is_needed) if cst is True and len(keyframes) >= 2 else (keyframes, baking_is_needed)
        else: # bone is not animated (no fcurve)
            # Not keeping if not changing property
            return (None, baking_is_needed) if cst is True else (keyframes, baking_is_needed)
    else:
        # For objects, if all values are the same, we keep only first and last
        cst = fcurve_is_constant(keyframes)
        if node_channel_is_animated is True:
            return ([keyframes[0], keyframes[-1]], baking_is_needed) if cst is True and len(keyframes) >= 2 else (keyframes, baking_is_needed)
        else:
            # baked object (selected but not animated)
            return (None, baking_is_needed) if cst is True else (keyframes, baking_is_needed)

    return (keyframes, baking_is_needed)


def fcurve_is_constant(keyframes):
    return all([j < 0.0001 for j in np.ptp([[k.value[i] for i in range(len(keyframes[0].value))] for k in keyframes], axis=0)])

def complete_key(key: Keyframe, non_keyed_values: typing.Tuple[typing.Optional[float]]):
    """
    Complete keyframe with non keyed values
    """
    for i in range(0, key.get_target_len()):
        if i in key.get_indices():
            continue # this is a keyed array_index or a SK animated
        key.set_value_index(i, non_keyed_values[i])

def complete_key_tangents(key: Keyframe, non_keyed_values: typing.Tuple[typing.Optional[float]]):
    """
    Complete keyframe with non keyed values for tangents
    """
    for i in range(0, key.get_target_len()):
        if i in key.get_indices():
            continue # this is a keyed array_index or a SK animated
        if key.in_tangent is not None:
            key.set_value_index_in(i, non_keyed_values[i])
        if key.out_tangent is not None:
            key.set_value_index_out(i, non_keyed_values[i])

def needs_baking(blender_object_if_armature: typing.Optional[bpy.types.Object],
                 channels: typing.Tuple[bpy.types.FCurve],
                 export_settings
                 ) -> bool:
    """
    Check if baking is needed.

    Some blender animations need to be baked as they can not directly be expressed in glTF.
    """
    def all_equal(lst):
        return lst[1:] == lst[:-1]

    # Note: channels has some None items only for SK if some SK are not animated

    # Sampling is forced
    if export_settings[gltf2_blender_export_keys.FORCE_SAMPLING]:
        return True

    # If tree is troncated, sampling is forced
    if export_settings['vtree'].tree_troncated is True:
        return True

    # Sampling due to unsupported interpolation
    interpolation = [c for c in channels if c is not None][0].keyframe_points[0].interpolation
    if interpolation not in ["BEZIER", "LINEAR", "CONSTANT"]:
        gltf2_io_debug.print_console("WARNING",
                                     "Baking animation because of an unsupported interpolation method: {}".format(
                                         interpolation)
                                     )
        return True

    if any(any(k.interpolation != interpolation for k in c.keyframe_points) for c in channels if c is not None):
        # There are different interpolation methods in one action group
        gltf2_io_debug.print_console("WARNING",
                                     "Baking animation because there are keyframes with different "
                                     "interpolation methods in one channel"
                                     )
        return True

    if not all_equal([len(c.keyframe_points) for c in channels if c is not None]):
        gltf2_io_debug.print_console("WARNING",
                                     "Baking animation because the number of keyframes is not "
                                     "equal for all channel tracks")
        return True

    if len([c for c in channels if c is not None][0].keyframe_points) <= 1:
        # we need to bake to 'STEP', as at least two keyframes are required to interpolate
        return True

    if not all_equal(list(zip([[k.co[0] for k in c.keyframe_points] for c in channels if c is not None]))):
        # The channels have differently located keyframes
        gltf2_io_debug.print_console("WARNING",
                                     "Baking animation because of differently located keyframes in one channel")
        return True

    if blender_object_if_armature is not None:
        animation_target = gltf2_blender_get.get_object_from_datapath(blender_object_if_armature, [c for c in channels if c is not None][0].data_path)
        if isinstance(animation_target, bpy.types.PoseBone):
            if len(animation_target.constraints) != 0:
                # Constraints such as IK act on the bone -> can not be represented in glTF atm
                gltf2_io_debug.print_console("WARNING",
                                             "Baking animation because of unsupported constraints acting on the bone")
                return True

    return False
