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
from math import sqrt
from mathutils import Quaternion
from .gltf2_blender_node import *
from .gltf2_blender_skin import *
from .gltf2_blender_animation import *

class BlenderScene():

    @staticmethod
    def create(gltf, scene_idx):

        pyscene = gltf.data.scenes[scene_idx]

        # Create Yup2Zup empty
        obj_rotation = bpy.data.objects.new("Yup2Zup", None)
        obj_rotation.rotation_mode = 'QUATERNION'
        obj_rotation.rotation_quaternion = Quaternion((sqrt(2)/2, sqrt(2)/2,0.0,0.0))


    # Create a new scene only if not already exists in .blend file
    # TODO : put in current scene instead ?
        if pyscene.name not in [scene.name for scene in bpy.data.scenes]:
            if pyscene.name:
                scene = bpy.data.scenes.new(pyscene.name)
            else:
                scene = bpy.context.scene
            scene.render.engine = "CYCLES"

            gltf.blender_scene = scene.name
        else:
            gltf.blender_scene = pyscene.name

        for node_idx in pyscene.nodes:
            BlenderNode.create(gltf, node_idx, None) # None => No parent


        # Now that all mesh / bones are created, create vertex groups on mesh
        if gltf.data.skins:
            for skin_id, skin in enumerate(gltf.data.skins):
                BlenderSkin.create_vertex_groups(gltf, skin_id)

            for skin_id, skin in enumerate(gltf.data.skins):
                BlenderSkin.assign_vertex_groups(gltf, skin_id)

            for skin_id, skin in enumerate(gltf.data.skins):
                BlenderSkin.create_armature_modifiers(gltf, skin_id)

        if gltf.data.animations:
            for anim_idx, anim in enumerate(gltf.data.animations):
                for node_idx, node in enumerate(pyscene.nodes):
                    BlenderAnimation.anim(gltf, anim_idx, node_idx)


        # Parent root node to rotation object
        bpy.data.scenes[gltf.blender_scene].objects.link(obj_rotation)
        obj_rotation.hide = True
        for node_idx in pyscene.nodes:
            bpy.data.objects[gltf.data.nodes[node_idx].blender_object].parent = obj_rotation
