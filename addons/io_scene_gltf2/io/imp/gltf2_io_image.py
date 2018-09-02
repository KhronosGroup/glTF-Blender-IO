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

from ..com.gltf2_io_image import *

class ImageImporter():

    @staticmethod
    def read(pyimage):

        pyimage.image_name = "Image_" + str(pyimage.index)

        if 'uri' in pyimage.json.keys():
            sep = ';base64,'
            if pyimage.json['uri'][:5] == 'data:':
                idx = pyimage.json['uri'].find(sep)
                if idx != -1:
                    data = pyimage.json['uri'][idx+len(sep):]
                    pyimage.data = base64.b64decode(data)
                    return

            if isfile(join(dirname(pyimage.gltf.filename), pyimage.json['uri'])):
                with open(join(dirname(pyimage.gltf.filename), pyimage.json['uri']), 'rb') as f_:
                    pyimage.data = f_.read()
                    pyimage.image_name = basename(join(dirname(pyimage.gltf.filename), pyimage.json['uri']))
                    return
            else:
                pyimage.gltf.log.error("Missing file (index " + str(pyimage.index) + "): " + pyimage.json['uri'])
                return

        if 'bufferView' not in pyimage.json.keys():
            return

        if pyimage.json['bufferView'] not in pyimage.gltf.bufferViews.keys():
            pyimage.gltf.bufferViews[pyimage.json['bufferView']] = BufferView(pyimage.json['bufferView'], pyimage.gltf.json['bufferViews'][pyimage.json['bufferView']], pyimage.gltf)
            pyimage.gltf.bufferViews[pyimage.json['bufferView']].read()

        pyimage.bufferView = pyimage.gltf.bufferViews[pyimage.json['bufferView']]

        pyimage.data = BufferViewImporter.read_binary_data(pyimage.bufferView)

    @staticmethod
    def importer(idx, json, gltf):
        image = PyImage(idx, json, gltf)
        ImageImporter.read(image)
        return image
