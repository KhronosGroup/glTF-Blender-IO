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

from ...io.imp.user_extensions import import_user_extensions
from ..com.conversion import PBR_WATTS_TO_LUMENS
from ..com.extras import set_extras


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
            light = BlenderLight.create_directional(gltf, light_id)  # ...Why not pass the pylight?
        elif pylight['type'] == "point":
            light = BlenderLight.create_point(gltf, light_id)
        elif pylight['type'] == "spot":
            light = BlenderLight.create_spot(gltf, light_id)

        if 'color' in pylight.keys():
            light.color = pylight['color']

        # TODO range

        set_extras(light, pylight.get('extras'))

        pylight['blender_object_data'] = light  # Needed in case of KHR_animation_pointer

        return light

    @staticmethod
    def create_directional(gltf, light_id):
        pylight = gltf.data.extensions['KHR_lights_punctual']['lights'][light_id]

        if 'name' not in pylight.keys():
            pylight['name'] = "Sun"  # Uh... Is it okay to mutate the import data?

        sun = bpy.data.lights.new(name=pylight['name'], type="SUN")

        if 'intensity' in pylight.keys():
            sun.energy = BlenderLight.calc_energy_directional(gltf, pylight['intensity'])

        return sun

    @staticmethod
    def calc_energy_directional(gltf, pylight_data):
        if gltf.import_settings['export_import_convert_lighting_mode'] == 'SPEC':
            return pylight_data / PBR_WATTS_TO_LUMENS
        elif gltf.import_settings['export_import_convert_lighting_mode'] == 'COMPAT':
            return pylight_data
        elif gltf.import_settings['export_import_convert_lighting_mode'] == 'RAW':
            return pylight_data
        else:
            raise ValueError(gltf.import_settings['export_import_convert_lighting_mode'])

    @staticmethod
    def calc_energy_pointlike(gltf, pylight_data):
        if gltf.import_settings['export_import_convert_lighting_mode'] == 'SPEC':
            return pylight_data / PBR_WATTS_TO_LUMENS * 4 * pi
        elif gltf.import_settings['export_import_convert_lighting_mode'] == 'COMPAT':
            return pylight_data * 4 * pi
        elif gltf.import_settings['export_import_convert_lighting_mode'] == 'RAW':
            return pylight_data
        else:
            raise ValueError(gltf.import_settings['export_import_convert_lighting_mode'])

    @staticmethod
    def create_point(gltf, light_id):
        pylight = gltf.data.extensions['KHR_lights_punctual']['lights'][light_id]

        if 'name' not in pylight.keys():
            pylight['name'] = "Point"

        point = bpy.data.lights.new(name=pylight['name'], type="POINT")

        if 'intensity' in pylight.keys():
            point.energy = BlenderLight.calc_energy_pointlike(gltf, pylight['intensity'])

        return point

    @staticmethod
    def create_spot(gltf, light_id):
        pylight = gltf.data.extensions['KHR_lights_punctual']['lights'][light_id]

        if 'name' not in pylight.keys():
            pylight['name'] = "Spot"

        spot = bpy.data.lights.new(name=pylight['name'], type="SPOT")

        # Angles
        if 'spot' in pylight.keys():
            gltf_default_outer_cone_angle = pi / 4
            gltf_default_inner_cone_angle = 0.0

            spot.spot_size = BlenderLight.calc_spot_cone_outer(
                gltf, pylight['spot'].get('outerConeAngle', gltf_default_outer_cone_angle))
            spot.spot_blend = BlenderLight.calc_spot_cone_inner(
                gltf, pylight['spot'].get(
                    'outerConeAngle', gltf_default_outer_cone_angle), pylight['spot'].get(
                    'innerConeAngle', gltf_default_inner_cone_angle))

        if 'intensity' in pylight.keys():
            spot.energy = BlenderLight.calc_energy_pointlike(gltf, pylight['intensity'])

        # Store multiple channel data, as we will need all channels to convert to
        # blender data when animated by KHR_animation_pointer
        if gltf.data.extensions_used is not None and "KHR_animation_pointer" in gltf.data.extensions_used:
            if len(pylight['animations']) > 0:
                for anim_idx in pylight['animations'].keys():
                    for channel_idx in pylight['animations'][anim_idx]:
                        channel = gltf.data.animations[anim_idx].channels[channel_idx]
                        pointer_tab = channel.target.extensions["KHR_animation_pointer"]["pointer"].split("/")
                        if len(pointer_tab) == 6 and pointer_tab[1] == "extensions" and \
                                pointer_tab[2] == "KHR_lights_punctual" and \
                                pointer_tab[3] == "lights" and \
                                pointer_tab[5] in ["spot.innerConeAngle", "spot.outerConeAngle"]:
                            # Store multiple channel data, as we will need all channels to convert to
                            # blender data when animated
                            if "multiple_channels" not in pylight.keys():
                                pylight['multiple_channels'] = {}
                            pylight['multiple_channels'][pointer_tab[5]] = (anim_idx, channel_idx)

        return spot

    @staticmethod
    def calc_spot_cone_outer(gltf, outercone):
        return outercone * 2

    @staticmethod
    def calc_spot_cone_inner(gltf, outercone, innercone):
        return 1 - (innercone / outercone)
