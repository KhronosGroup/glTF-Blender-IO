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

class BlenderCamera():

    @staticmethod
    def create(gltf, camera_id):

        pycamera = gltf.data.cameras[camera_id]

        if not pycamera.name:
            pycamera.name = "Camera"

        cam = bpy.data.cameras.new(pycamera.name)

        # Blender create a perspective camera by default
        if pycamera.type == "orthographic":
            cam.type = "ORTHO"

        #TODO: lot's of work for camera here...
        if hasattr(pycamera, "znear"):
            cam.clip_start = pycamera.znear

        if hasattr(pycamera, "zfar"):
            cam.clip_end = pycamera.zfar


        obj = bpy.data.objects.new(pycamera.name, cam)
        bpy.data.scenes[gltf.blender_scene].objects.link(obj)
        return obj
