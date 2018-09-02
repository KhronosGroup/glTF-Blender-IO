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

from ..com.gltf2_io_KHR_materials_pbrSpecularGlossiness import *
from .gltf2_io_texture import *

class KHR_materials_pbrSpecularGlossinessImporter():

    @staticmethod
    def read(pykhr):
        if pykhr.json is None:
            return # will use default values

        if 'diffuseTexture' in pykhr.json.keys():
            pykhr.diffuse_type = pykhr.TEXTURE
            pykhr.diffuseTexture = TextureImporter.importer(pykhr.json['diffuseTexture']['index'], pykhr.gltf.json['textures'][pykhr.json['diffuseTexture']['index']], pykhr.gltf)

            if 'texCoord' in pykhr.json['diffuseTexture']:
                pykhr.diffuseTexture.texcoord = int(pykhr.json['diffuseTexture']['texCoord'])
            else:
                pykhr.diffuseTexture.texcoord = 0

        if 'diffuseFactor' in pykhr.json.keys():
            pykhr.diffuseFactor = pykhr.json['diffuseFactor']
            if pykhr.diffuse_type == pykhr.TEXTURE and pykhr.diffuseFactor != [1.0,1.0,1.0,1.0]:
                pykhr.diffuse_type = pykhr.TEXTURE_FACTOR

        if 'specularGlossinessTexture' in pykhr.json.keys():
            pykhr.specgloss_type = pykhr.TEXTURE
            pykhr.specularGlossinessTexture = TextureImporter.importer(pykhr.json['specularGlossinessTexture']['index'], pykhr.gltf.json['textures'][pykhr.json['specularGlossinessTexture']['index']], pykhr.gltf)

            if 'texCoord' in pykhr.json['specularGlossinessTexture']:
                pykhr.specularGlossinessTexture.texcoord = int(pykhr.json['specularGlossinessTexture']['texCoord'])
            else:
                pykhr.specularGlossinessTexture.texcoord = 0

        if 'glossinessFactor' in pykhr.json.keys():
            pykhr.glossinessFactor = pykhr.json['glossinessFactor']

        if 'specularFactor' in pykhr.json.keys():
            pykhr.specularFactor = pykhr.json['specularFactor']
            if pykhr.specgloss_type == pykhr.TEXTURE and pykhr.specgloss_type != [1.0,1.0,1.0]:
                pykhr.specgloss_type = pykhr.TEXTURE_FACTOR

    @staticmethod
    def use_vertex_color(pykhr):
        pykhr.vertex_color = True

    @staticmethod
    def importer(json, gltf):
        khr = PyKHR_materials_pbrSpecularGlossiness(json, gltf)
        KHR_materials_pbrSpecularGlossinessImporter.read(khr)
        return khr
