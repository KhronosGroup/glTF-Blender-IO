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
from .gltf2_blender_scene import *

class BlenderGlTF():

    @staticmethod
    def create(gltf):

        # Blender attributes initialization
        gltf.blender_scene = None

        for scene in gltf.data.scenes:
            BlenderScene.create(gltf, scene)

        #TODO_SPLIT: seems it will work unchanged, but need to be check
        # Armature correction
        # Try to detect bone chains, and set bone lengths
        # To detect if a bone is in a chain, we try to detect if a bone head is aligned
        # with parent_bone :
        ##          Parent bone defined a line (between head & tail)
        ##          Bone head defined a point
        ##          Calcul of distance between point and line
        ##          If < threshold --> In a chain
        ## Based on an idea of @Menithal, but added alignement detection to avoid some bad cases

        threshold = 0.001
        for armobj in [obj for obj in bpy.data.objects if obj.type == "ARMATURE"]:
            bpy.context.scene.objects.active = armobj
            armature = armobj.data
            bpy.ops.object.mode_set(mode="EDIT")
            for bone in armature.edit_bones:
                if bone.parent is None:
                    continue

                parent = bone.parent

                # case where 2 bones are aligned (not in chain, same head)
                if (bone.head - parent.head).length < threshold:
                    continue

            u = (parent.tail - parent.head).normalized()
            point = bone.head
            distance = ((point - parent.head).cross(u)).length / u.length
            if distance < threshold:
                save_parent_direction = (parent.tail - parent.head).normalized().copy()
                save_parent_tail = parent.tail.copy()
                parent.tail = bone.head

                # case where 2 bones are aligned (not in chain, same head)
                # bone is no more is same direction
                if (parent.tail - parent.head).normalized().dot(save_parent_direction) < 0.9:
                    parent.tail = save_parent_tail
