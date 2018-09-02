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

from ..com.gltf2_io_primitive import *
from .gltf2_io_accessor import *
from .gltf2_io_material import *

class PrimitiveImporter():

    @staticmethod
    def read(pyprimitive):

        # reading attributes
        if 'attributes' in pyprimitive.json.keys():
            for attr in pyprimitive.json['attributes'].keys():
                pyprimitive.gltf.log.debug("Primitive attribute " + attr)
                pyprimitive.attributes[attr] = {}
                if pyprimitive.json['attributes'][attr] not in pyprimitive.gltf.accessors.keys():
                    pyprimitive.gltf.accessors[pyprimitive.json['attributes'][attr]], pyprimitive.attributes[attr]['result'] = AccessorImporter.importer(pyprimitive.json['attributes'][attr], pyprimitive.gltf.json['accessors'][pyprimitive.json['attributes'][attr]], pyprimitive.gltf)
                    pyprimitive.attributes[attr]['accessor'] = pyprimitive.gltf.accessors[pyprimitive.json['attributes'][attr]]
                else:
                    pyprimitive.attributes[attr]['accessor'] = pyprimitive.gltf.accessors[pyprimitive.json['attributes'][attr]]
                    pyprimitive.attributes[attr]['result'] = pyprimitive.attributes[attr]['accessor'].data

                # Convert data if needed
                if attr in ['TEXCOORD_0', 'TEXCOORD_1', 'COLOR_0', 'WEIGHTS_0']:
                    if pyprimitive.attributes[attr]['accessor'].normalized == True:
                        if pyprimitive.attributes[attr]['accessor'].json['componentType'] == 5121:
                            for idx_tab, i in enumerate(pyprimitive.attributes[attr]['result']):
                                new_tuple = ()
                                for idx, it in enumerate(i):
                                    new_tuple += (float(it/255.0),)
                                pyprimitive.attributes[attr]['result'][idx_tab] = new_tuple

        # reading indices
        if 'indices' in pyprimitive.json.keys():
            pyprimitive.gltf.log.debug("Primitive indices")
            if pyprimitive.json['indices'] not in pyprimitive.gltf.accessors.keys():
                pyprimitive.gltf.accessors[pyprimitive.json['indices']], pyprimitive.indices = AccessorImporter.importer(pyprimitive.json['indices'], pyprimitive.gltf.json['accessors'][pyprimitive.json['indices']], pyprimitive.gltf)
                pyprimitive.accessor = pyprimitive.gltf.accessors[pyprimitive.json['indices']]
            else:
                pyprimitive.accessor = pyprimitive.gltf.accessors[pyprimitive.json['indices']]
                pyprimitive.indices  = pyprimitive.accessor.data

            pyprimitive.indices  = [ind[0] for ind in pyprimitive.indices]
        else:
            pyprimitive.indices = range(0, len(pyprimitive.attributes['POSITION']['result']))


        # reading materials
        if 'material' in pyprimitive.json.keys():
            # create material if not already exits
            if pyprimitive.json['material'] not in pyprimitive.gltf.materials.keys():
                pyprimitive.mat = MaterialImporter.importer(pyprimitive.json['material'], pyprimitive.gltf.json['materials'][pyprimitive.json['material']], pyprimitive.gltf)
                pyprimitive.gltf.materials[pyprimitive.json['material']] = pyprimitive.mat

                if 'COLOR_0' in pyprimitive.attributes.keys():
                    pyprimitive.mat.use_vertex_color()

            else:
                # Use already existing material
                pyprimitive.mat = pyprimitive.gltf.materials[pyprimitive.json['material']]

        else:
            # If there is a COLOR_0, we are going to use it in material
            if 'COLOR_0' in pyprimitive.attributes.keys():
                pyprimitive.mat = MaterialImporter.importer(None, None, pyprimitive.gltf)
                MaterialImporter.use_vertex_color(pyprimitive.mat)
            else:
                # No material, use default one
                if pyprimitive.gltf.default_material is None:
                    pyprimitive.gltf.default_material = MaterialImporter.importer(None, None, pyprimitive.gltf)

                pyprimitive.mat = pyprimitive.gltf.default_material

        # reading targets (shapekeys) if any
        if 'targets' in pyprimitive.json.keys():
            for targ in pyprimitive.json['targets']:
                target = {}
                for attr in targ.keys():
                    target[attr] = {}
                    if targ[attr] not in pyprimitive.gltf.accessors.keys():
                        pyprimitive.gltf.accessors[targ[attr]], target[attr]['result'] = AccessorImporter.importer(targ[attr], pyprimitive.gltf.json['accessors'][targ[attr]], pyprimitive.gltf)
                        target[attr]['accessor'] = pyprimitive.gltf.accessors[targ[attr]]
                    else:
                        target[attr]['accessor'] = pyprimitive.gltf.accessors[targ[attr]]
                        target[attr]['result']   = target[attr]['accessor'].data

                pyprimitive.targets.append(target)

    @staticmethod
    def importer(idx, json, gltf):
        primitive = PyPrimitive(idx, json, gltf)
        PrimitiveImporter.read(primitive)
        return primitive
