# Copyright (c) 2018 The Khronos Group Inc.
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
import os
import sys

try:
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]  # get all args after "--"
    else:
        argv = []

    if '--glb' in argv:
        path = os.path.splitext(bpy.data.filepath)[0] + ".glb"
        path_parts = os.path.split(path)
        glb_dir = os.path.join(path_parts[0], 'glb')
        if not os.path.exists(glb_dir):
            os.mkdir(glb_dir)
        bpy.ops.export_scene.glb(filepath=os.path.join(glb_dir, path_parts[1]), export_experimental=('--experimental' in argv))
    else:
        bpy.ops.export_scene.gltf(filepath=os.path.splitext(bpy.data.filepath)[0] + ".gltf", export_experimental=('--experimental' in argv))
except Exception as err:
    sys.exit(1)
