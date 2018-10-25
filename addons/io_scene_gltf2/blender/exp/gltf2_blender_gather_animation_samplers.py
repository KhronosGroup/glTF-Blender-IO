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
import math
import typing
from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached
from io_scene_gltf2.blender.exp import gltf2_blender_animate
from io_scene_gltf2.io.exp import gltf2_io_binary_data
from io_scene_gltf2.io.com import gltf2_io_constants
from io_scene_gltf2.blender.com import gltf2_blender_conversion
from io_scene_gltf2.io.com import gltf2_io_debug
from io_scene_gltf2.blender.exp import gltf2_blender_extract


@cached
def gather_animation_sampler(action_group: bpy.types.ActionGroup,
                             blender_object: bpy.types.Object,
                             export_settings
                             ) -> gltf2_io.AnimationSampler:
    return gltf2_io.AnimationSampler(
        extensions=__gather_extensions(action_group, blender_object, export_settings),
        extras=__gather_extras(action_group, blender_object, export_settings),
        input=__gather_input(action_group, blender_object, export_settings),
        interpolation=__gather_interpolation(action_group, blender_object, export_settings),
        output=__gather_output(action_group, blender_object, export_settings)
    )


def __gather_extensions(action_group: bpy.types.ActionGroup,
                        blender_object: bpy.types.Object,
                        export_settings
                        ) -> typing.Any:
    return None


def __gather_extras(action_group: bpy.types.ActionGroup,
                    blender_object: bpy.types.Object,
                    export_settings
                    ) -> typing.Any:
    return None


def __gather_input(action_group: bpy.types.ActionGroup,
                   blender_object: bpy.types.Object,
                   export_settings
                   ) -> gltf2_io.Accessor:
    """Gather the key time codes"""
    keyframes = __gather_keyframes(action_group, export_settings)
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


def __gather_interpolation(action_group: bpy.types.ActionGroup,
                           blender_object: bpy.types.Object,
                           export_settings
                           ) -> str:
    if __needs_baking(action_group, export_settings):
        return 'STEP'

    blender_keyframe = action_group.channels[0].keyframe_points[0]

    # Select the interpolation method. Any unsupported method will fallback to STEP
    return {
        "BEZIER": "CUBICSPLINE",
        "LINEAR": "LINEAR",
        "CONSTANT": "STEP"
    }[blender_keyframe.interpolation]


def __gather_output(action_group: bpy.types.ActionGroup,
                    blender_object: bpy.types.Object,
                    export_settings
                    ) -> gltf2_io.Accessor:
    """The data of the keyframes"""
    keyframes = __gather_keyframes(action_group, export_settings)

    # TODO: support bones coordinate system
    transform = mathutils.Matrix.Identity(4)

    target = action_group.channels[0].data_path.split('.')[-1]
    transform_func = {
        "location": __transform_location,
        "rotation_axis_angle": __transform_rotation,
        "rotation_euler": __transform_rotation,
        "rotation_quaternion": __transform_rotation,
        "scale": __transform_scale,
        "value": transform_value
    }.get(target)

    if transform_func is None:
        raise NotImplementedError("The specified animation target {} is not currently supported by the glTF exporter".format(target))

    values = []
    for keyframe in keyframes:
        keyframe_value = list(transform_func(keyframe.value, transform))
        if keyframe.in_tangent is not None:
            keyframe_value = list(transform_func(keyframe.in_tangent, transform)) + keyframe_value
        if keyframe.out_tangent is not None:
            keyframe_value = keyframe_value + list(transform_func(keyframe.out_tangent, transform))
        values += keyframe_value

    component_type = gltf2_io_constants.ComponentType.Float
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


def __needs_baking(action_group: bpy.types.ActionGroup,
                   export_settings
                   ) -> bool:
    """
    Some blender animations need to be baked as they can not directly be expressed in glTF
    """
    # if blender_object.type == "ARMATURE":
    #     return True

    if export_settings['gltf_force_sampling']:
        return True

    interpolation = action_group.channels[0].keyframe_points[0].interpolation
    if interpolation not in ["BEZIER", "LINEAR", "CONSTANT"]:
        return True

    if any(any(k.interpolation != interpolation for k in c.keyframe_points) for c in action_group.channels):
        # There are different interpolation methods in one action group
        return True

    def all_equal(lst): return lst[1:] == lst[:-1]
    if not all(all_equal( [k.co[0] for k in c.keyframe_points] ) for c in action_group.channels):
        # The channels have differently located keyframes
        return True

    return False


# TODO: If blender ever moves to python 3.7 this should be a dataclass
class Keyframe:
    def __init__(self):
        self.seconds = 0.0
        self.value = None
        self.in_tangent = None
        self.out_tangent = None

    @staticmethod
    def from_action_group(action_group: bpy.types.ActionGroup, time: float):
        key = Keyframe()
        key.seconds = time / bpy.context.scene.render.fps
        values = [c.evaluate(time) for c in action_group.channels]
        key.value = gltf2_blender_conversion.list_to_mathutils(values, action_group.channels[0].data_path)
        return key


def __transform_location(location: mathutils.Vector, transform: mathutils.Matrix = mathutils.Matrix.Identity(4)) -> mathutils.Vector:
    m = mathutils.Matrix.Translation(location)
    m = transform * m
    return m.to_translation()


def __transform_rotation(rotation: mathutils.Quaternion, transform: mathutils.Matrix = mathutils.Matrix.Identity(4)) -> mathutils.Quaternion:
    m = rotation.to_matrix().to_4x4()
    m = transform * m
    return m.to_quaternion()


def __transform_scale(scale: mathutils.Vector, transform: mathutils.Matrix = mathutils.Matrix.Identity(4)) -> mathutils.Vector:
    m = mathutils.Matrix()
    m[0][0] = scale.x
    m[1][1] = scale.y
    m[2][2] = scale.z
    m = transform * m
    return m.to_scale()


def transform_value(value: mathutils.Vector, transform: mathutils.Matrix = mathutils.Matrix.Identity(4)) -> mathutils.Vector:
    return value


# cache for performance reasons
@cached
def __gather_keyframes(action_group: bpy.types.ActionGroup, export_settings) \
        -> typing.List[Keyframe]:
    """
    Convert the blender action groups' fcurves to keyframes for use in glTF
    """

    # Find the start and end of the whole action group
    start = min([channel.range()[0] for channel in action_group.channels])
    end = max([channel.range()[1] for channel in action_group.channels])

    keyframes = []
    if __needs_baking(action_group, export_settings):
        # Bake the animation, by evaluating it at a high frequency
        time = start
        # TODO: make user controllable
        step = 1.0 / bpy.context.scene.render.fps
        while time <= end:
            key = Keyframe.from_action_group(action_group, time)
            keyframes.append(key)
            time += step
    else:
        # Just use the keyframes as they are specified in blender
        times = [ keyframe.co[0] for keyframe in action_group.channels[0].keyframe_points]
        for i, time in enumerate(times):
            key = Keyframe.from_action_group(action_group, time)
            # compute tangents for cubic spline interpolation
            if action_group.channels[0].keyframe_points[0].interpolation == "BEZIER":
                if time != start:
                    in_tangent = [3.0 * (c.keyframe_points[i].co[1] - c.keyframe_points[i].handle_left[1]) / (time - times[i-1]) for c in action_group.channels]
                    key.in_tangent = gltf2_blender_conversion.list_to_mathutils(in_tangent, action_group.channels[0].data_path)
                if time != end:
                    out_tangent = [3.0 * (c.keyframe_points[i].handle_right[1] - c.keyframe_points[i].co[1]) / (times[i+1] - time) for c in action_group.channels]
                    key.out_tangent = gltf2_blender_conversion.list_to_mathutils(out_tangent, action_group.channels[0].data_path)
            keyframes.append(key)

    return keyframes
