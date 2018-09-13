"""
 * ***** BEGIN GPL LICENSE BLOCK *****
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License
 * as published by the Free Software Foundation; either version 2
 * of the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software Foundation,
 * Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
 *
 * Contributor(s): Julien Duroure.
 *
 * ***** END GPL LICENSE BLOCK *****
 """

import bpy
from mathutils import Quaternion, Matrix, Vector

from .gltf2_blender_animation import *
from ..com.gltf2_blender_conversion import *
from ...io.imp.gltf2_io_binary import *

class BlenderNodeAnim():

    @staticmethod
    def set_interpolation(interpolation, kf):
        if interpolation == "LINEAR":
            kf.interpolation = 'LINEAR'
        elif interpolation == "STEP":
            kf.interpolation = 'CONSTANT'
        elif interpolation == "CATMULLROMSPLINE":
            kf.interpolation = 'BEZIER' #TODO
        elif interpolation == "CUBICSPLINE":
            kf.interpolation = 'BEZIER' #TODO
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

            keys   = BinaryData.get_data_from_accessor(gltf, animation.samplers[channel.sampler].input)
            values = BinaryData.get_data_from_accessor(gltf, animation.samplers[channel.sampler].output)

            if channel.target.path in ['translation', 'rotation', 'scale']:

                if channel.target.path == "translation":
                    blender_path = "location"
                    for idx, key in enumerate(keys):
                       obj.location = Vector(Conversion.loc_gltf_to_blender(list(values[idx])))
                       obj.keyframe_insert(blender_path, frame = key[0] * fps, group='location')

                    # Setting interpolation
                    for fcurve in [curve for curve in obj.animation_data.action.fcurves if curve.group.name == "rotation"]:
                        for kf in fcurve.keyframe_points:
                            BlenderNodeAnim.set_interpolation(animation.samplers[channel.sampler].interpolation, kf)

                elif channel.target.path == "rotation":
                    blender_path = "rotation_quaternion"
                    for idx, key in enumerate(keys):
                        obj.rotation_quaternion = Conversion.quaternion_gltf_to_blender(values[idx])
                        obj.keyframe_insert(blender_path, frame = key[0] * fps, group='rotation')

                    # Setting interpolation
                    for fcurve in [curve for curve in obj.animation_data.action.fcurves if curve.group.name == "rotation"]:
                        for kf in fcurve.keyframe_points:
                            BlenderNodeAnim.set_interpolation(animation.samplers[channel.sampler].interpolation, kf)


                elif channel.target.path == "scale":
                    blender_path = "scale"
                    for idx, key in enumerate(keys):
                        obj.scale = Vector(Conversion.scale_gltf_to_blender(list(values[idx])))
                        obj.keyframe_insert(blender_path, frame = key[0] * fps, group='scale')

                    # Setting interpolation
                    for fcurve in [curve for curve in obj.animation_data.action.fcurves if curve.group.name == "rotation"]:
                        for kf in fcurve.keyframe_points:
                            BlenderNodeAnim.set_interpolation(animation.samplers[channel.sampler].interpolation, kf)

            elif channel.target.path == 'weights':
                for idx, key in enumerate(keys):
                    print(key)
                    # for key in sk:
                    #     obj.data.shape_keys.key_blocks[cpt_sk+1].value = key[1]
                    #     obj.data.shape_keys.key_blocks[cpt_sk+1].keyframe_insert("value", frame=key[0] * fps, group='ShapeKeys')
