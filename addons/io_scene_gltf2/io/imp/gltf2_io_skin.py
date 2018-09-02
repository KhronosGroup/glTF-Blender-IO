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

from ..com.gltf2_io_skin import *
from .gltf2_io_accessor import *

class SkinImporter():

    @staticmethod
    def read(pyskin):
        if 'skeleton' in pyskin.json.keys():
            pyskin.root = pyskin.json['skeleton']

        if 'joints' in pyskin.json.keys():
            pyskin.bones = pyskin.json['joints']

        if 'name' in pyskin.json.keys():
            pyskin.name = pyskin.json['name']

        if 'inverseBindMatrices' in pyskin.json.keys():
            if pyskin.json['inverseBindMatrices'] not in pyskin.gltf.accessors.keys():
                pyskin.gltf.accessors[pyskin.json['inverseBindMatrices']], data = AccessorImporter.importer(pyskin.json['inverseBindMatrices'], pyskin.gltf.json['accessors'][pyskin.json['inverseBindMatrices']], pyskin.gltf)
                pyskin.inverseBindMatrices = pyskin.gltf.accessors[pyskin.json['inverseBindMatrices']]
                pyskin.data = data
            else:
                pyskin.inverseBindMatrices = pyskin.gltf.accessors[pyskin.json['inverseBindMatrices']]
                pyskin.data = pyskin.inverseBindMatrices.data

    @staticmethod
    def importer(idx, json, gltf):
        skin = PySkin(idx, json, gltf)
        SkinImporter.read(skin)
        return skin
