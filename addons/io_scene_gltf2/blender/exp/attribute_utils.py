# Copyright 2026 The glTF-Blender-IO authors.
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

import numpy as np


def extract_attribute_data(attribute, size, type_, data_type, domain, length, export_settings):

    data = None

    if domain == 'CORNER':
        data = np.empty(size * length, dtype=type_)
    elif domain == 'POINT':
        data = np.empty(size * length, dtype=type_)
    elif domain == "EDGE":
        data = np.empty(size * length, dtype=type_)
    elif domain == 'FACE':
        data = np.empty(size * length, dtype=type_)
    else:
        export_settings['log'].error("domain not known")

    if data_type == "BYTE_COLOR":
        attribute.data.foreach_get('color', data)
        data = data.reshape(-1, length)
    elif data_type == "INT8":
        attribute.data.foreach_get('value', data)
        data = data.reshape(-1, length)
    elif data_type == "FLOAT2":
        attribute.data.foreach_get('vector', data)
        data = data.reshape(-1, length)
    elif data_type == "BOOLEAN":
        attribute.data.foreach_get('value', data)
        data = data.reshape(-1, length)
    elif data_type == "STRING":
        attribute.data.foreach_get('value', data)
        data = data.reshape(-1, length)
    elif data_type == "FLOAT_COLOR":
        attribute.data.foreach_get('color', data)
        data = data.reshape(-1, length)
    elif data_type == "FLOAT_VECTOR":
        attribute.data.foreach_get('vector', data)
        data = data.reshape(-1, length)
    elif data_type == "QUATERNION":
        attribute.data.foreach_get('value', data)
        data = data.reshape(-1, length)
    elif data_type == "FLOAT4X4":
        attribute.data.foreach_get('value', data)
        data = data.reshape(-1, length)
    elif data_type == "INT":
        attribute.data.foreach_get('value', data)
        data = data.reshape(-1, length)
    elif data_type == "FLOAT":
        attribute.data.foreach_get('value', data)
        data = data.reshape(-1, length)
    else:
        export_settings['log'].error("blender type not found " + data_type)

    return data
