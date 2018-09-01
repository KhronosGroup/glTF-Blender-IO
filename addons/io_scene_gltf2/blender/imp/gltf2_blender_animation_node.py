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

from .gltf2_blender_animation_data import *

class BlenderNodeAnim():

    @staticmethod
    def anim(pyanim):
        obj = bpy.data.objects[pyanim.animation.node.blender_object]
        fps = bpy.context.scene.render.fps

        for anim in pyanim.animation.anims.keys():
            if pyanim.animation.gltf.animations[anim].name:
                name = pyanim.animation.gltf.animations[anim].name + "_" + obj.name
            else:
                name = "pyanim.animation_" + str(pyanim.animation.gltf.animations[anim].index) + "_" + obj.name
            action = bpy.data.actions.new(name)
            if not obj.animation_data:
                obj.animation_data_create()
            obj.animation_data.action = bpy.data.actions[action.name]

            for channel in pyanim.animation.anims[anim]:
                if channel.path in ['translation', 'rotation', 'scale']:

                    if channel.path == "translation":
                        blender_path = "location"
                        for key in channel.data:
                           obj.location = Vector(pyanim.animation.gltf.convert.location(list(key[1])))
                           obj.keyframe_insert(blender_path, frame = key[0] * fps, group='location')

                        # Setting interpolation
                        for fcurve in [curve for curve in obj.animation_data.action.fcurves if curve.group.name == "rotation"]:
                            for kf in fcurve.keyframe_points:
                                BlenderAnimationData.set_interpolation(channel.interpolation, kf)

                    elif channel.path == "rotation":
                        blender_path = "rotation_quaternion"
                        for key in channel.data:
                            obj.rotation_quaternion = pyanim.animation.gltf.convert.quaternion(key[1])
                            obj.keyframe_insert(blender_path, frame = key[0] * fps, group='rotation')

                        # Setting interpolation
                        for fcurve in [curve for curve in obj.animation_data.action.fcurves if curve.group.name == "rotation"]:
                            for kf in fcurve.keyframe_points:
                                BlenderAnimationData.set_interpolation(channel.interpolation, kf)


                    elif channel.path == "scale":
                        blender_path = "scale"
                        for key in channel.data:
                            obj.scale = Vector(pyanim.animation.gltf.convert.scale(list(key[1])))
                            obj.keyframe_insert(blender_path, frame = key[0] * fps, group='scale')

                        # Setting interpolation
                        for fcurve in [curve for curve in obj.animation_data.action.fcurves if curve.group.name == "rotation"]:
                            for kf in fcurve.keyframe_points:
                                BlenderAnimationData.set_interpolation(channel.interpolation, kf)

                elif channel.path == 'weights':
                    cpt_sk = 0
                    for sk in channel.data:
                        for key in sk:
                            obj.data.shape_keys.key_blocks[cpt_sk+1].value = key[1]
                            obj.data.shape_keys.key_blocks[cpt_sk+1].keyframe_insert("value", frame=key[0] * fps, group='ShapeKeys')

                        cpt_sk += 1
