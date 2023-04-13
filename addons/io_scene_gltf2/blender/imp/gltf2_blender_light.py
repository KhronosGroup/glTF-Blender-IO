# Copyright 2018-2021 The glTF-Blender-IO authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import bpy
from math import pi

from ...io.imp.gltf2_io_user_extensions import import_user_extensions
from ..com.gltf2_blender_conversion import PBR_WATTS_TO_LUMENS
from ..com.gltf2_blender_extras import set_extras

class BlenderLight():
    """Blender Light."""
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("%s should not be instantiated" % cls)

    @staticmethod
    def create(gltf, vnode, light_id):
        """Light creation."""
        pylight = gltf.data.extensions['KHR_lights_punctual']['lights'][light_id]

        import_user_extensions('gather_import_light_before_hook', gltf, vnode, pylight)

        if pylight['type'] == "directional":
            light = BlenderLight.create_directional(gltf, light_id) # ...Why not pass the pylight?
        elif pylight['type'] == "point":
            light = BlenderLight.create_point(gltf, light_id)
        elif pylight['type'] == "spot":
            light = BlenderLight.create_spot(gltf, light_id)

        if 'color' in pylight.keys():
            light.color = pylight['color']

        # TODO range

        set_extras(light, pylight.get('extras'), gltf.import_settings)

        return light

    @staticmethod
    def create_directional(gltf, light_id):
        pylight = gltf.data.extensions['KHR_lights_punctual']['lights'][light_id]

        if 'name' not in pylight.keys():
            pylight['name'] = "Sun" # Uh... Is it okay to mutate the import data?

        sun = bpy.data.lights.new(name=pylight['name'], type="SUN")

        if 'intensity' in pylight.keys():
            if gltf.import_settings['export_import_convert_lighting_mode'] == 'SPEC':
                sun.energy = pylight['intensity'] / PBR_WATTS_TO_LUMENS
            elif gltf.import_settings['export_import_convert_lighting_mode'] == 'COMPAT':
                sun.energy = pylight['intensity']
            elif gltf.import_settings['export_import_convert_lighting_mode'] == 'RAW':
                sun.energy = pylight['intensity']
            else:
                raise ValueError(gltf.import_settings['export_import_convert_lighting_mode'])

        return sun

    @staticmethod
    def _calc_energy_pointlike(gltf, pylight):
        if gltf.import_settings['export_import_convert_lighting_mode'] == 'SPEC':
            return pylight['intensity'] / PBR_WATTS_TO_LUMENS * 4 * pi
        elif gltf.import_settings['export_import_convert_lighting_mode'] == 'COMPAT':
            return pylight['intensity'] * 4 * pi
        elif gltf.import_settings['export_import_convert_lighting_mode'] == 'RAW':
            return pylight['intensity']
        else:
            raise ValueError(gltf.import_settings['export_import_convert_lighting_mode'])

    @staticmethod
    def create_point(gltf, light_id):
        pylight = gltf.data.extensions['KHR_lights_punctual']['lights'][light_id]

        if 'name' not in pylight.keys():
            pylight['name'] = "Point"

        point = bpy.data.lights.new(name=pylight['name'], type="POINT")

        if 'intensity' in pylight.keys():
            point.energy = BlenderLight._calc_energy_pointlike(gltf, pylight)

        return point

    @staticmethod
    def create_spot(gltf, light_id):
        pylight = gltf.data.extensions['KHR_lights_punctual']['lights'][light_id]

        if 'name' not in pylight.keys():
            pylight['name'] = "Spot"

        spot = bpy.data.lights.new(name=pylight['name'], type="SPOT")

        # Angles
        if 'spot' in pylight.keys() and 'outerConeAngle' in pylight['spot']:
            spot.spot_size = pylight['spot']['outerConeAngle'] * 2
        else:
            spot.spot_size = pi / 2

        if 'spot' in pylight.keys() and 'innerConeAngle' in pylight['spot']:
            spot.spot_blend = 1 - ( pylight['spot']['innerConeAngle'] / pylight['spot']['outerConeAngle'] )
        else:
            spot.spot_blend = 1.0

        if 'intensity' in pylight.keys():
            spot.energy = BlenderLight._calc_energy_pointlike(gltf, pylight)

        return spot
