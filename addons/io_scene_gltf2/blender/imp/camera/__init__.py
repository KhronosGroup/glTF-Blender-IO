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
 * This development is done in strong collaboration with Airbus Defence & Space
 """

import bpy

class Camera():
    def __init__(self, index, name, json, gltf):
        self.index = index
        self.json  = json # Camera json
        self.gltf =  gltf # Reference to global glTF instance
        self.name = name

    def read(self):
        if 'type' in self.json.keys():
            self.type = self.json['type']

        if self.type in self.json.keys():
            if 'zfar' in self.json[self.type].keys():
                self.zfar = self.json[self.type]['zfar']
            if 'znear' in self.json[self.type].keys():
                self.znear = self.json[self.type]['znear']

            if self.type == "perspective":
                if 'aspectRatio' in self.json[self.type].keys():
                    self.aspectRatio = self.json[self.type]['aspectRatio']
                if 'yfov' in self.json[self.type].keys():
                    self.yfoc = self.json[self.type]['yfov']
            elif self.type == "orthographic":
                if 'xmag' in self.json[self.type].keys():
                    self.xmag = self.json[self.type]['xmag']
                if 'ymag' in self.json[self.type].keys():
                    self.ymag = self.json[self.type]['ymag']

    def create_blender(self):
        if not self.name:
            self.name = "Camera"

        cam = bpy.data.cameras.new(self.name)

        # Blender create a perspective camera by default
        if self.type == "orthographic":
            cam.type = "ORTHO"

        if hasattr(self, "znear"):
            cam.clip_start = self.znear

        if hasattr(self, "zfar"):
            cam.clip_end = self.zfar


        obj = bpy.data.objects.new(self.name, cam)
        bpy.data.scenes[self.gltf.blender_scene].objects.link(obj)
        return obj

    def debug_missing(self):
        keys = [
                'type',
                'perspective',
                'orthographic'
                ]

        for key in self.json.keys():
            if key not in keys:
                self.gltf.log.debug("CAMERA MISSING " + key)
