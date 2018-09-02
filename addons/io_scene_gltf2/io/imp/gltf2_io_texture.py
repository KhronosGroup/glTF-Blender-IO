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

from ..com.gltf2_io_texture import *
from .gltf2_io_image import *

class TextureImporter():

    @staticmethod
    def read(pytexture):
        if 'source' in pytexture.json.keys():

            if pytexture.json['source'] not in pytexture.gltf.images.keys():
                image = ImageImporter.importer(pytexture.json['source'], pytexture.gltf.json['images'][pytexture.json['source']], pytexture.gltf)
                pytexture.gltf.images[pytexture.json['source']] = image

            pytexture.image = pytexture.gltf.images[pytexture.json['source']]

    @staticmethod
    def importer(idx, json, gltf):
        texture = PyTexture(idx, json, gltf)
        TextureImporter.read(texture)
        return texture
