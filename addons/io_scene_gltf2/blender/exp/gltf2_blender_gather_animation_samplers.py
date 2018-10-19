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
import typing
from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached
from io_scene_gltf2.blender.exp import gltf2_blender_animate
from io_scene_gltf2.io.exp import gltf2_io_binary_data
from io_scene_gltf2.io.com import gltf2_io_constants
from io_scene_gltf2.blender.exp import gltf2_blender_utils
from io_scene_gltf2.io.com import gltf2_io_debug

@cached
def gather_animation_sampler(action_group: bpy.types.ActionGroup,
                             blender_object: bpy.types.Object,
                             export_settings
                             ) -> gltf2_io.AnimationSampler:
    if not __filter_sampler(action_group, export_settings):
        raise RuntimeError("The animation sampler could not be created")

    return gltf2_io.AnimationSampler(
        extensions=__gather_extensions(action_group, blender_object, export_settings),
        extras=__gather_extras(action_group, blender_object, export_settings),
        input=__gather_input(action_group, blender_object, export_settings),
        interpolation=__gather_interpolation(action_group, blender_object, export_settings),
        output=__gather_output(action_group, blender_object, export_settings)
    )


def __filter_sampler(action_group: bpy.types.ActionGroup,
                     blender_object: bpy.types.Object,
                     export_settings
                     ) -> bool:
    return True


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
    # TODO: replace with cleaner code, once the old exporter is removed
    interpolation = ""
    if __needs_baking(action_group, blender_object, export_settings):
        interpolation = "CONVERSION_NEEDED"
    # Extract time codes from keyframes
    keys = gltf2_blender_animate.animate_gather_keys(export_settings, action_group.channels, interpolation)

    return gltf2_io.Accessor(
        buffer_view=gltf2_io_binary_data.BinaryData.from_list(keys, gltf2_io_constants.DataType.Scalar),
        byte_offset=None,
        component_type=gltf2_io_constants.ComponentType.Float,
        count=len(keys),
        extensions=None,
        extras=None,
        max=max(keys),
        min=min(keys),
        name=None,
        normalized=None,
        sparse=None,
        type=gltf2_io_constants.DataType.Scalar
    )


def __gather_interpolation(action_group: bpy.types.ActionGroup,
                           blender_object: bpy.types.Object,
                           export_settings
                           ) -> str:
    if __needs_baking(action_group, blender_object, export_settings):
        return 'LINEAR'


    blender_keyframe = action_group.channels[0].keyframe_points[0]

    # Select the interpolation method. Any unsupported method will fallback to LINEAR
    interpolation_mapping = {
        "BEZIER": "CUBICSPLINE",
        "LINEAR": "LINEAR",
        "CONSTANT": "STEP"
    }
    if blender_keyframe.interpolation not in interpolation_mapping:
        gltf2_io_debug.print_console(
            "Unsupported animation interpolation method: {}. Falling back to linear".format(blender_keyframe.interpolation)
        )
        return "LINEAR"



def __gather_output(action_group: bpy.types.ActionGroup,
                    blender_object: bpy.types.Object,
                    export_settings
                    ) -> gltf2_io.Accessor:
    """The data of the keyframes"""
    interpolation = ""
    if __needs_baking(action_group, blender_object, export_settings):
        interpolation = "CONVERSION_NEEDED"
    # Extract time codes from keyframes
    keys = gltf2_blender_animate.animate_gather_keys(export_settings, action_group.channels, interpolation)

    # Iterate all keyframes and evaluate the properties
    values = typing.List[float]()
    for key in keys:
        values += __evaluate_animation(key, action_group, blender_object)

    component_type = gltf2_io_constants.ComponentType.Float
    data_type = gltf2_io_constants.DataType.vec_type_from_num(len(action_group.channels))
    return gltf2_io.Accessor(
        buffer_view=gltf2_io_binary_data.BinaryData.from_list(values, data_type),
        byte_offset=None,
        component_type=component_type,
        count=len(values),
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
                   blender_object: bpy.types.Object,
                   export_settings
                   ) -> bool:
    """
    Some blender animations need to be baked as they can not directly be expressed in glTF
    """
    if blender_object.type == "ARMATURE":
        return True

    if export_settings['gltf_force_sampling']:
        return True

    return False


def __evaluate_animation(key,
                         action_group: bpy.types.ActionGroup,
                         blender_object: bpy.types.Object
                         ) -> typing.List[float]:
    def action_group_target(action_group: bpy.types.ActionGroup):
        return action_group.channels[0].data_path.split(".")[-1]

    return {
        "location": __evaluate_location
    }[action_group_target(action_group)](key, action_group)


def __evaluate_location(key, action_group: bpy.types.ActionGroup) -> typing.List[float]:
    return []