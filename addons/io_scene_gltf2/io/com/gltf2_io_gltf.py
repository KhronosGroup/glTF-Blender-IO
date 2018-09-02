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

import json

from .gltf2_io_scene import *
from .gltf2_io_animation import *
from .gltf2_io_asset import *
from .gltf2_io_debug import *

class PyglTF():

    def __init__(self, filename, loglevel=logging.ERROR):

        # glTF properties required
        self.asset = None

        # glTF properties not required
        #TODO : note that all these are not managed yet
        self.extensionsUsed = ""
        self.extensionsRequired = ""
        self.accessors = {}
        self.animations = {}
        self.buffers = {}
        self.bufferViews = {}
        self.cameras = {}
        self.images = {}
        self.materials = {}
        self.meshes = {}
        self.nodes = {}
        self.samplers = {}
        self.scene = -1
        self.scenes = {}
        self.skins = {}
        self.textures = {}
        self.extensions = {}
        self.extras = {}

        # PyGlTF specific
        self.filename = filename
        self.other_scenes = []

        #TODO move somewhere else, not in python classes
        log = Log(loglevel)
        self.log = log.logger
        self.log_handler = log.hdlr

        self.default_material = None #TODO move somewhere else, not in python classes

        self.extensions_managed = [
            "KHR_materials_pbrSpecularGlossiness"
        ]

        #TODO : merge with io_constants
        self.fmt_char_dict = {}
        self.fmt_char_dict[5120] = 'b' # Byte
        self.fmt_char_dict[5121] = 'B' # Unsigned Byte
        self.fmt_char_dict[5122] = 'h' # Short
        self.fmt_char_dict[5123] = 'H' # Unsigned Short
        self.fmt_char_dict[5125] = 'I' # Unsigned Int
        self.fmt_char_dict[5126] = 'f' # Float

        self.component_nb_dict = {}
        self.component_nb_dict['SCALAR'] = 1
        self.component_nb_dict['VEC2']   = 2
        self.component_nb_dict['VEC3']   = 3
        self.component_nb_dict['VEC4']   = 4
        self.component_nb_dict['MAT2']   = 4
        self.component_nb_dict['MAT3']   = 9
        self.component_nb_dict['MAT4']   = 16
