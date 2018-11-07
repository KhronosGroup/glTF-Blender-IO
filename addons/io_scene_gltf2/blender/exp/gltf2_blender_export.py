# Copyright 2018 The glTF-Blender-IO authors.
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
import sys
import traceback

from . import export_keys
from . import gltf2_blender_gather
from .gltf2_blender_gltf2_exporter import GlTF2Exporter
from ..com import gltf2_blender_json
from ...io.exp import gltf2_io_export
from ...io.com.gltf2_io_debug import print_console, print_newline


def save(operator,
         context,
         export_settings):
    """
    Starts the glTF 2.0 export and saves to content either to a .gltf or .glb file.
    """

    print_console('INFO', 'Starting glTF 2.0 export')
    bpy.context.window_manager.progress_begin(0, 100)
    bpy.context.window_manager.progress_update(0)

    #

    scenes, animations = gltf2_blender_gather.gather_gltf2(export_settings)
    if not export_settings[export_keys.COPYRIGHT]:
        export_settings[export_keys.COPYRIGHT] = None
    exporter = GlTF2Exporter(copyright=export_settings[export_keys.COPYRIGHT])
    for scene in scenes:
        exporter.add_scene(scene)
    for animation in animations:
        exporter.add_animation(animation)

    if export_settings[export_keys.FORMAT] == 'ASCII':
        exporter.finalize_buffer(export_settings[export_keys.FILE_DIRECTORY],
                                 export_settings[export_keys.BINARY_FILENAME])
    else:
        exporter.finalize_buffer(export_settings[export_keys.FILE_DIRECTORY])
    exporter.finalize_images(export_settings[export_keys.FILE_DIRECTORY])
    glTF = exporter.glTF

    #

    # TODO: move to custom JSON encoder
    def dict_strip(obj):
        o = obj
        if isinstance(obj, dict):
            o = {}
            for k, v in obj.items():
                if v is None:
                    continue
                elif isinstance(v, list) and len(v) == 0:
                    continue
                o[k] = dict_strip(v)
        elif isinstance(obj, list):
            o = []
            for v in obj:
                o.append(dict_strip(v))
        elif isinstance(obj, float):
            # force floats to int, if they are integers (prevent INTEGER_WRITTEN_AS_FLOAT validator warnings)
            if int(obj) == obj:
                return int(obj)
        return o

    try:
        gltf2_io_export.save_gltf(dict_strip(glTF.to_dict()), export_settings, gltf2_blender_json.BlenderJSONEncoder)
    except AssertionError as e:
        _, _, tb = sys.exc_info()
        traceback.print_tb(tb)  # Fixed format
        tb_info = traceback.extract_tb(tb)
        for tbi in tb_info:
            filename, line, func, text = tbi
            print_console('ERROR', 'An error occurred on line {} in statement {}'.format(line, text))
        print_console('ERROR', str(e))
        raise e

    print_console('INFO', 'Finished glTF 2.0 export')
    bpy.context.window_manager.progress_end()
    print_newline()

    return {'FINISHED'}
