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

import json
import bpy


class BlenderJSONEncoder(json.JSONEncoder):
    """Blender JSON Encoder."""

    def default(self, obj):
        if isinstance(obj, bpy.types.ID):
            return dict(
                name=obj.name,
                type=obj.__class__.__name__
            )
        return super(BlenderJSONEncoder, self).default(obj)


def is_json_convertible(data):
    """Test, if a data set can be expressed as JSON."""
    try:
        json.dumps(data, cls=BlenderJSONEncoder)
        return True
    except:
        return False
