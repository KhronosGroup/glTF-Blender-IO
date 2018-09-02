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

from ..com.gltf2_io_camera import *

class CameraImporter():

    @staticmethod
    def read(pycamera):
        if 'type' in pycamera.json.keys():
            pycamera.type = pycamera.json['type']

        if pycamera.type in pycamera.json.keys():
            if 'zfar' in pycamera.json[pycamera.type].keys():
                pycamera.zfar = pycamera.json[pycamera.type]['zfar']
            if 'znear' in pycamera.json[pycamera.type].keys():
                pycamera.znear = pycamera.json[pycamera.type]['znear']

            if pycamera.type == "perspective":
                if 'aspectRatio' in pycamera.json[pycamera.type].keys():
                    pycamera.aspectRatio = pycamera.json[pycamera.type]['aspectRatio']
                if 'yfov' in pycamera.json[pycamera.type].keys():
                    pycamera.yfoc = pycamera.json[pycamera.type]['yfov']
            elif pycamera.type == "orthographic":
                if 'xmag' in pycamera.json[pycamera.type].keys():
                    pycamera.xmag = pycamera.json[pycamera.type]['xmag']
                if 'ymag' in pycamera.json[pycamera.type].keys():
                    pycamera.ymag = pycamera.json[pycamera.type]['ymag']

    @staticmethod
    def importer(idx, name, json, gltf):
        pycamera = PyCamera(idx, name, json, gltf)
        CameraImporter.read(pycamera)
        return pycamera
