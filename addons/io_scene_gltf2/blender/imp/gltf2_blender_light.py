# Copyright 2018-2019 The glTF-Blender-IO authors.
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

from ..com.gltf2_blender_extras import set_extras


class BlenderLight():
    """Blender Light."""
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("%s should not be instantiated" % cls)

    @staticmethod
    def create(gltf, light_id):
        """Light creation."""
        pylight = gltf.data.extensions['KHR_lights_punctual']['lights'][light_id]
        if pylight['type'] == "directional":
            obj = BlenderLight.create_directional(gltf, light_id)
        elif pylight['type'] == "point":
            obj = BlenderLight.create_point(gltf, light_id)
        elif pylight['type'] == "spot":
            obj = BlenderLight.create_spot(gltf, light_id)

        if 'color' in pylight.keys():
            obj.data.color = pylight['color']

        if 'intensity' in pylight.keys():
            obj.data.energy = pylight['intensity']

        # TODO range

        if bpy.app.version < (2, 80, 0):
            bpy.data.scenes[gltf.blender_scene].objects.link(obj)
        else:
            if gltf.blender_active_collection is not None:
                bpy.data.collections[gltf.blender_active_collection].objects.link(obj)
            else:
                bpy.data.scenes[gltf.blender_scene].collection.objects.link(obj)

        set_extras(obj.data, pylight.get('extras'))

        return obj

    @staticmethod
    def create_directional(gltf, light_id):
        pylight = gltf.data.extensions['KHR_lights_punctual']['lights'][light_id]

        if 'name' not in pylight.keys():
            pylight['name'] = "Sun"

        if bpy.app.version < (2, 80, 0):
            sun = bpy.data.lamps.new(name=pylight['name'], type="SUN")
        else:
            sun = bpy.data.lights.new(name=pylight['name'], type="SUN")
        obj = bpy.data.objects.new(pylight['name'], sun)
        return obj

    @staticmethod
    def create_point(gltf, light_id):
        pylight = gltf.data.extensions['KHR_lights_punctual']['lights'][light_id]

        if 'name' not in pylight.keys():
            pylight['name'] = "Point"

        if bpy.app.version < (2, 80, 0):
            point = bpy.data.lamps.new(name=pylight['name'], type="POINT")
        else:
            point = bpy.data.lights.new(name=pylight['name'], type="POINT")
        obj = bpy.data.objects.new(pylight['name'], point)
        return obj

    @staticmethod
    def create_spot(gltf, light_id):
        pylight = gltf.data.extensions['KHR_lights_punctual']['lights'][light_id]

        if 'name' not in pylight.keys():
            pylight['name'] = "Spot"

        if bpy.app.version < (2, 80, 0):
            spot = bpy.data.lamps.new(name=pylight['name'], type="SPOT")
        else:
            spot = bpy.data.lights.new(name=pylight['name'], type="SPOT")
        obj = bpy.data.objects.new(pylight['name'], spot)

        # Angles
        if 'spot' in pylight.keys() and 'outerConeAngle' in pylight['spot']:
            spot.spot_size = pylight['spot']['outerConeAngle'] * 2
        else:
            spot.spot_size = pi / 2

        if 'spot' in pylight.keys() and 'innerConeAngle' in pylight['spot']:
            spot.spot_blend = 1 - ( pylight['spot']['innerConeAngle'] / pylight['spot']['outerConeAngle'] )
        else:
            spot.spot_blend = 1.0

        return obj
