# Copyright 2018-2023 The glTF-Blender-IO authors.
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

from urllib.parse import unquote, quote
from os.path import normpath
from os import sep

def uri_to_path(uri):
    uri = uri.replace('\\', '/') # Some files come with \\ as dir separator
    uri = unquote(uri)
    return normpath(uri)

def path_to_uri(path):
    path = normpath(path)
    path = path.replace(sep, '/')
    return quote(path)
