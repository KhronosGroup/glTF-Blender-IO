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

def export_user_extensions(hook_name, export_settings, *args):
    if args and hasattr(args[0], "extensions"):
        if args[0].extensions is None:
            args[0].extensions = {}

    for extension in export_settings['gltf_user_extensions']:
        hook = getattr(extension, hook_name, None)
        if hook is not None:
            try:
                hook(*args, export_settings)
            except Exception as e:
                print(hook_name, "fails on", extension)
                print(str(e))
