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

from .gltf2_io_accessor import *
from .gltf2_io_material import *

class PyPrimitive():
    def __init__(self, index, json, gltf):
        self.index = index
        self.json  = json  # Primitive json
        self.gltf = gltf # Reference to global glTF instance

        # glTF2.0 required properties
        self.attributes = {}

        # glTF2.0 not required properties, with default values
        self.mode = 4

        # glTF2.0 not required properties
        self.indices_ = None #TODO: to be renamed, because my code already has a indice attribute
        self.material = None
        self.targets = [] # shapekeys
        self.extensions = {}
        self.extras = {}

        # PyPrimitive specific
        self.mat = None

    def read(self):

        # reading attributes
        if 'attributes' in self.json.keys():
            for attr in self.json['attributes'].keys():
                self.gltf.log.debug("Primitive attribute " + attr)
                self.attributes[attr] = {}
                if self.json['attributes'][attr] not in self.gltf.accessors.keys():
                    self.gltf.accessors[self.json['attributes'][attr]] = Accessor(self.json['attributes'][attr], self.gltf.json['accessors'][self.json['attributes'][attr]], self.gltf)
                    self.attributes[attr]['accessor'] = self.gltf.accessors[self.json['attributes'][attr]]
                    self.attributes[attr]['result']   = self.attributes[attr]['accessor'].read()
                else:
                    self.attributes[attr]['accessor'] = self.gltf.accessors[self.json['attributes'][attr]]
                    self.attributes[attr]['result'] = self.attributes[attr]['accessor'].data

                # Convert data if needed
                if attr in ['TEXCOORD_0', 'TEXCOORD_1', 'COLOR_0', 'WEIGHTS_0']:
                    if self.attributes[attr]['accessor'].normalized == True:
                        if self.attributes[attr]['accessor'].json['componentType'] == 5121:
                            for idx_tab, i in enumerate(self.attributes[attr]['result']):
                                new_tuple = ()
                                for idx, it in enumerate(i):
                                    new_tuple += (float(it/255.0),)
                                self.attributes[attr]['result'][idx_tab] = new_tuple

        # reading indices
        if 'indices' in self.json.keys():
            self.gltf.log.debug("Primitive indices")
            if self.json['indices'] not in self.gltf.accessors.keys():
                self.gltf.accessors[self.json['indices']] = Accessor(self.json['indices'], self.gltf.json['accessors'][self.json['indices']], self.gltf)
                self.accessor = self.gltf.accessors[self.json['indices']]
                self.indices  = self.accessor.read()
            else:
                self.accessor = self.gltf.accessors[self.json['indices']]
                self.indices  = self.accessor.data

            self.indices  = [ind[0] for ind in self.indices]
        else:
            self.indices = range(0, len(self.attributes['POSITION']['result']))


        # reading materials
        if 'material' in self.json.keys():
            # create material if not already exits
            if self.json['material'] not in self.gltf.materials.keys():
                self.mat = PyMaterial(self.json['material'], self.gltf.json['materials'][self.json['material']], self.gltf)
                self.mat.read()
                self.mat.debug_missing()
                self.gltf.materials[self.json['material']] = self.mat

                if 'COLOR_0' in self.attributes.keys():
                    self.mat.use_vertex_color()

            else:
                # Use already existing material
                self.mat = self.gltf.materials[self.json['material']]

        else:
            # If there is a COLOR_0, we are going to use it in material
            if 'COLOR_0' in self.attributes.keys():
                self.mat = PyMaterial(None, None, self.gltf)
                self.mat.read()
                self.mat.debug_missing()
                self.mat.use_vertex_color()
            else:
                # No material, use default one
                if self.gltf.default_material is None:
                    self.gltf.default_material = PyMaterial(None, None, self.gltf)
                    self.gltf.default_material.read()
                    self.gltf.default_material.debug_missing()

                self.mat = self.gltf.default_material

        # reading targets (shapekeys) if any
        if 'targets' in self.json.keys():
            for targ in self.json['targets']:
                target = {}
                for attr in targ.keys():
                    target[attr] = {}
                    if targ[attr] not in self.gltf.accessors.keys():
                        self.gltf.accessors[targ[attr]] = Accessor(targ[attr], self.gltf.json['accessors'][targ[attr]], self.gltf)
                        target[attr]['accessor'] = self.gltf.accessors[targ[attr]]
                        target[attr]['result']   = target[attr]['accessor'].read()
                    else:
                        target[attr]['accessor'] = self.gltf.accessors[targ[attr]]
                        target[attr]['result']   = target[attr]['accessor'].data

                self.targets.append(target)
