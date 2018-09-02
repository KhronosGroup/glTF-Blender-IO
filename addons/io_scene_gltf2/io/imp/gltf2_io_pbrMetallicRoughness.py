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

from ..com.gltf2_io_pbrMetallicRoughness import *
from .gltf2_io_texture import *

class PbrImporter():

    @staticmethod
    def read(pypbr):
        if pypbr.json is None:
            return # will use default values

        if 'baseColorTexture' in pypbr.json.keys():
            pypbr.color_type = pypbr.TEXTURE
            pypbr.baseColorTexture = TextureImporter.importer(pypbr.json['baseColorTexture']['index'], pypbr.gltf.json['textures'][pypbr.json['baseColorTexture']['index']], pypbr.gltf)

            if 'texCoord' in pypbr.json['baseColorTexture']:
                pypbr.baseColorTexture.texcoord = int(pypbr.json['baseColorTexture']['texCoord'])
            else:
                pypbr.baseColorTexture.texcoord = 0

        if 'metallicRoughnessTexture' in pypbr.json.keys():
            pypbr.metallic_type = pypbr.TEXTURE
            pypbr.metallicRoughnessTexture = TextureImporter.importer(pypbr.json['metallicRoughnessTexture']['index'], pypbr.gltf.json['textures'][pypbr.json['metallicRoughnessTexture']['index']], pypbr.gltf)

            if 'texCoord' in pypbr.json['metallicRoughnessTexture']:
                pypbr.metallicRoughnessTexture.texcoord = int(pypbr.json['metallicRoughnessTexture']['texCoord'])
            else:
                pypbr.metallicRoughnessTexture.texcoord = 0

        if 'baseColorFactor' in pypbr.json.keys():
            pypbr.baseColorFactor = pypbr.json['baseColorFactor']
            if pypbr.color_type == pypbr.TEXTURE and pypbr.baseColorFactor != [1.0,1.0,1.0]:
                pypbr.color_type = pypbr.TEXTURE_FACTOR

        if 'metallicFactor' in pypbr.json.keys():
            pypbr.metallicFactor = pypbr.json['metallicFactor']
            if pypbr.metallic_type == pypbr.TEXTURE and pypbr.metallicFactor != 1.0 and pypbr.roughnessFactor != 1.0:
                pypbr.metallic_type = pypbr.TEXTURE_FACTOR

        if 'roughnessFactor' in pypbr.json.keys():
            pypbr.roughnessFactor = pypbr.json['roughnessFactor']
            if pypbr.metallic_type == pypbr.TEXTURE and pypbr.roughnessFactor != 1.0 and pypbr.metallicFactor != 1.0:
                pypbr.metallic_type = pypbr.TEXTURE_FACTOR

    @staticmethod
    def importer(json, gltf):
        pbr = PyPbr(json, gltf)
        PbrImporter.read(pbr)
        return pbr
