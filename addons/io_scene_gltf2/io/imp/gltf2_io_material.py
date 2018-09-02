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

from ..com.gltf2_io_material import *
from .gltf2_io_pbrMetallicRoughness import *

class MaterialImporter():

    @staticmethod
    def read(pymaterial):

        # If no index, this is the default material
        if pymaterial.index is None:
            pymaterial.pbr = PbrImporter.importer(None, pymaterial.gltf)
            pymaterial.name = "Default Material"
            return

        if 'extensions' in pymaterial.json.keys():
            if 'KHR_materials_pbrSpecularGlossiness' in pymaterial.json['extensions'].keys():
                pymaterial.KHR_materials_pbrSpecularGlossiness = PyKHR_materials_pbrSpecularGlossiness(pymaterial.json['extensions']['KHR_materials_pbrSpecularGlossiness'], pymaterial.gltf)
                pymaterial.KHR_materials_pbrSpecularGlossiness.read()

        # Not default material
        if 'name' in pymaterial.json.keys():
            pymaterial.name = pymaterial.json['name']

        if 'pbrMetallicRoughness' in pymaterial.json.keys():
            pymaterial.pbr = PbrImporter.importer(pymaterial.json['pbrMetallicRoughness'], pymaterial.gltf)
        else:
            pymaterial.pbr = PbrImporter.importer(None, pymaterial.gltf)

        # Emission
        if 'emissiveTexture' in pymaterial.json.keys():
            if 'emissiveFactor' in pymaterial.json.keys():
                factor = pymaterial.json['emissiveFactor'] #TODO use pymaterial.emissiveFactor
            else:
                factor = [1.0, 1.0, 1.0]

            pymaterial.emissivemap = PyMap(pymaterial.json['emissiveTexture'], factor, pymaterial.gltf)
            pymaterial.emissivemap.read()

        # Normal Map
        if 'normalTexture' in pymaterial.json.keys():
            pymaterial.normalmap = PyMap(pymaterial.json['normalTexture'], 1.0, pymaterial.gltf)
            pymaterial.normalmap.read()

        # Occlusion Map
        if 'occlusionTexture' in pymaterial.json.keys():
            pymaterial.occlusionmap = PyMap(pymaterial.json['occlusionTexture'], 1.0, pymaterial.gltf)
            pymaterial.occlusionmap.read()

    @staticmethod
    def use_vertex_color(pymaterial):
        if hasattr(pymaterial, 'KHR_materials_pbrSpecularGlossiness'):
            pymaterial.KHR_materials_pbrSpecularGlossiness.use_vertex_color()
        else:
            pymaterial.pbr.use_vertex_color()

    @staticmethod
    def importer(idx, json, gltf):
        material = PyMaterial(idx, json, gltf)
        MaterialImporter.read(material)
        return material
