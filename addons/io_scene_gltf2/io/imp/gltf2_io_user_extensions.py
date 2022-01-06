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

def import_user_extensions(hook_name, gltf_importer, *args):
    for extension in gltf_importer.import_user_extensions:
        hook = getattr(extension, hook_name, None)
        if hook is not None:
            try:
                hook(*args, gltf_importer)
            except Exception as e:
                print(hook_name, "fails on", extension)
                print(str(e))
