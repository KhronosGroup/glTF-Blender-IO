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

import sys
import traceback

from io_scene_gltf2.blender.com import gltf2_blender_json
from io_scene_gltf2.blender.exp import gltf2_blender_export_keys
from io_scene_gltf2.blender.exp import gltf2_blender_gather
from io_scene_gltf2.blender.exp.gltf2_blender_gltf2_exporter import GlTF2Exporter
from io_scene_gltf2.io.com.gltf2_io_debug import print_console, print_newline
from io_scene_gltf2.io.exp import gltf2_io_export


def save(context, export_settings):
    """Start the glTF 2.0 export and saves to content either to a .gltf or .glb file."""
    __notify_start(context)
    json, buffer = __export(export_settings)
    __write_file(json, buffer, export_settings)
    __notify_end(context)
    return {'FINISHED'}


def __export(export_settings):
    exporter = GlTF2Exporter(__get_copyright(export_settings))
    __add_root_objects(exporter, export_settings)
    buffer = __create_buffer(exporter, export_settings)
    exporter.finalize_images(export_settings[gltf2_blender_export_keys.FILE_DIRECTORY])
    json = __fix_json(exporter.glTF.to_dict())

    return json, buffer


def __get_copyright(export_settings):
    if export_settings[gltf2_blender_export_keys.COPYRIGHT]:
        return export_settings[gltf2_blender_export_keys.COPYRIGHT]
    return None


def __add_root_objects(exporter, export_settings):
    scenes, animations = gltf2_blender_gather.gather_gltf2(export_settings)
    for scene in scenes:
        exporter.add_scene(scene)
    for animation in animations:
        exporter.add_animation(animation)


def __create_buffer(exporter, export_settings):
    buffer = bytes()
    if export_settings[gltf2_blender_export_keys.FORMAT] == 'GLB':
        buffer = exporter.finalize_buffer(export_settings[gltf2_blender_export_keys.FILE_DIRECTORY], is_glb=True)
    else:
        if export_settings[gltf2_blender_export_keys.FORMAT] == 'GLTF_EMBEDDED':
            exporter.finalize_buffer(export_settings[gltf2_blender_export_keys.FILE_DIRECTORY])
        else:
            exporter.finalize_buffer(export_settings[gltf2_blender_export_keys.FILE_DIRECTORY],
                                     export_settings[gltf2_blender_export_keys.BINARY_FILENAME])

    return buffer


def __fix_json(obj):
    # TODO: move to custom JSON encoder
    fixed = obj
    if isinstance(obj, dict):
        fixed = {}
        for key, value in obj.items():
            if value is None:
                continue
            elif isinstance(value, list) and len(value) == 0:
                continue
            fixed[key] = __fix_json(value)
    elif isinstance(obj, list):
        fixed = []
        for value in obj:
            fixed.append(__fix_json(value))
    elif isinstance(obj, float):
        # force floats to int, if they are integers (prevent INTEGER_WRITTEN_AS_FLOAT validator warnings)
        if int(obj) == obj:
            return int(obj)
    return fixed


def __write_file(json, buffer, export_settings):
    try:
        gltf2_io_export.save_gltf(
            json,
            export_settings,
            gltf2_blender_json.BlenderJSONEncoder,
            buffer)
    except AssertionError as e:
        _, _, tb = sys.exc_info()
        traceback.print_tb(tb)  # Fixed format
        tb_info = traceback.extract_tb(tb)
        for tbi in tb_info:
            filename, line, func, text = tbi
            print_console('ERROR', 'An error occurred on line {} in statement {}'.format(line, text))
        print_console('ERROR', str(e))
        raise e


def __notify_start(context):
    print_console('INFO', 'Starting glTF 2.0 export')
    context.window_manager.progress_begin(0, 100)
    context.window_manager.progress_update(0)


def __notify_end(context):
    print_console('INFO', 'Finished glTF 2.0 export')
    context.window_manager.progress_end()
    print_newline()
