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
from mathutils import Vector

from ..com.gltf2_blender_conversion import Conversion
from ...io.imp.gltf2_io_binary import BinaryData


class BlenderNodeAnim():

    @staticmethod
    def set_interpolation(interpolation, kf):
        if interpolation == "LINEAR":
            kf.interpolation = 'LINEAR'
        elif interpolation == "STEP":
            kf.interpolation = 'CONSTANT'
        elif interpolation == "CATMULLROMSPLINE":
            kf.interpolation = 'BEZIER'  # TODO
        elif interpolation == "CUBICSPLINE":
            kf.interpolation = 'BEZIER'  # TODO
        else:
            kf.interpolation = 'BEZIER'

    @staticmethod
    def anim(gltf, anim_idx, node_idx):

        node = gltf.data.nodes[node_idx]
        obj = bpy.data.objects[node.blender_object]
        fps = bpy.context.scene.render.fps

        if anim_idx not in node.animations.keys():
            return

        animation = gltf.data.animations[anim_idx]

        if animation.name:
            name = animation.name + "_" + obj.name
        else:
            name = "Animation_" + str(anim_idx) + "_" + obj.name
        action = bpy.data.actions.new(name)
        if not obj.animation_data:
            obj.animation_data_create()
        obj.animation_data.action = bpy.data.actions[action.name]

        for channel_idx in node.animations[anim_idx]:
            channel = animation.channels[channel_idx]

            keys = BinaryData.get_data_from_accessor(gltf, animation.samplers[channel.sampler].input)
            values = BinaryData.get_data_from_accessor(gltf, animation.samplers[channel.sampler].output)

            if channel.target.path in ['translation', 'rotation', 'scale']:

                if channel.target.path == "translation":
                    blender_path = "location"
                    for idx, key in enumerate(keys):
                        obj.location = Vector(Conversion.loc_gltf_to_blender(list(values[idx])))
                        obj.keyframe_insert(blender_path, frame=key[0] * fps, group='location')

                    # Setting interpolation
                    for fcurve in [curve for curve in obj.animation_data.action.fcurves
                                   if curve.group.name == "location"]:
                        for kf in fcurve.keyframe_points:
                            BlenderNodeAnim.set_interpolation(animation.samplers[channel.sampler].interpolation, kf)

                elif channel.target.path == "rotation":
                    blender_path = "rotation_quaternion"
                    for idx, key in enumerate(keys):
                        obj.rotation_quaternion = Conversion.quaternion_gltf_to_blender(values[idx])
                        obj.keyframe_insert(blender_path, frame=key[0] * fps, group='rotation')

                    # Setting interpolation
                    for fcurve in [curve for curve in obj.animation_data.action.fcurves
                                   if curve.group.name == "rotation"]:
                        for kf in fcurve.keyframe_points:
                            BlenderNodeAnim.set_interpolation(animation.samplers[channel.sampler].interpolation, kf)

                elif channel.target.path == "scale":
                    blender_path = "scale"
                    for idx, key in enumerate(keys):
                        obj.scale = Vector(Conversion.scale_gltf_to_blender(list(values[idx])))
                        obj.keyframe_insert(blender_path, frame=key[0] * fps, group='scale')

                    # Setting interpolation
                    for fcurve in [curve for curve in obj.animation_data.action.fcurves if curve.group.name == "scale"]:
                        for kf in fcurve.keyframe_points:
                            BlenderNodeAnim.set_interpolation(animation.samplers[channel.sampler].interpolation, kf)

            elif channel.target.path == 'weights':

                # retrieve number of targets
                nb_targets = 0
                for prim in gltf.data.meshes[gltf.data.nodes[node_idx].mesh].primitives:
                    if prim.targets:
                        if len(prim.targets) > nb_targets:
                            nb_targets = len(prim.targets)

                for idx, key in enumerate(keys):
                    for sk in range(nb_targets):
                        obj.data.shape_keys.key_blocks[sk + 1].value = values[idx * nb_targets + sk][0]
                        obj.data.shape_keys.key_blocks[sk + 1].keyframe_insert(
                            "value",
                            frame=key[0] * fps,
                            group='ShapeKeys'
                        )
