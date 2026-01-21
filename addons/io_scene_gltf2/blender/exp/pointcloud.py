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


from ..com import conversion as gltf2_blender_conversion
import numpy as np


def gather_point_cloud(blender_mesh, export_settings):

    primitives = []

    # Do not export if we don't export loose points
    if not export_settings['gltf_loose_points']:
        return []

    # Position
    locs = np.empty(
        len(blender_mesh.attributes['position'].data) * 3, dtype=np.float32)
    position_attribute = gltf2_blender_conversion.get_attribute(
        blender_mesh.attributes, 'position', 'FLOAT_VECTOR', 'POINT')
    source = position_attribute.data if position_attribute else None
    foreach_attribute = 'vector'
    if source:
        source.foreach_get(foreach_attribute, locs)
    locs = locs.reshape(len(blender_mesh.attributes['position'].data), 3)

    # Radius
    radius = np.empty(
        len(blender_mesh.attributes['radius'].data), dtype=np.float32)
    radius_attribute = gltf2_blender_conversion.get_attribute(
        blender_mesh.attributes, 'radius', 'FLOAT', 'POINT')
    source = radius_attribute.data if radius_attribute else None
    foreach_attribute = 'value'
    if source:
        source.foreach_get(foreach_attribute, radius)
    radius = radius.reshape(len(blender_mesh.attributes['radius'].data))

    # Get any other attributes that may be present, starting with an underscore
    custom_attributes = __get_custom_attributes(blender_mesh, export_settings)

    custom_attributes['POSITION'] = {
        'data': locs,
        'data_type': gltf2_blender_conversion.get_data_type('FLOAT_VECTOR'),
        'component_type': gltf2_blender_conversion.get_component_type('FLOAT_VECTOR')
    }
    custom_attributes['_RADIUS'] = {
        'data': radius,
        'data_type': gltf2_blender_conversion.get_data_type('FLOAT'),
        'component_type': gltf2_blender_conversion.get_component_type('FLOAT')
    }

    primitives.append({
        'attributes': custom_attributes,
        'mode': 0,  # POINTS
        'material': 0,  # TODOPC
        'uvmap_attributes_index': {}
    })

    export_settings['log'].info(
        'Point Cloud Primitives created: %d' % len(primitives))

    return primitives


def __get_custom_attributes(blender_mesh, export_settings):
    custom_attributes = {}
    for attribute in blender_mesh.attributes:
        if attribute.domain != 'POINT':
            continue
        if attribute.name in ['position', 'radius']:
            continue
        if not attribute.name.startswith("_"):
            continue

        len_attr = gltf2_blender_conversion.get_data_length(
            attribute.data_type)
        data = np.empty(len(attribute.data) * len_attr, dtype=np.float32)
        if attribute.data_type == "BYTE_COLOR":
            attribute.data.foreach_get('color', data)
            data = data.reshape(-1, len_attr)
        elif attribute.data_type == "INT8":
            attribute.data.foreach_get('value', data)
            data = data.reshape(-1, len_attr)
        elif attribute.data_type == "FLOAT2":
            attribute.data.foreach_get('vector', data)
            data = data.reshape(-1, len_attr)
        elif attribute.data_type == "BOOLEAN":
            attribute.data.foreach_get('value', data)
            data = data.reshape(-1, len_attr)
        elif attribute.data_type == "STRING":
            attribute.data.foreach_get('value', data)
            data = data.reshape(-1, len_attr)
        elif attribute.data_type == "FLOAT_COLOR":
            attribute.data.foreach_get('color', data)
            data = data.reshape(-1, len_attr)
        elif attribute.data_type == "FLOAT_VECTOR":
            attribute.data.foreach_get('vector', data)
            data = data.reshape(-1, len_attr)
        elif attribute.data_type == "QUATERNION":
            attribute.data.foreach_get('value', data)
            data = data.reshape(-1, len_attr)
        elif attribute.data_type == "FLOAT4X4":
            attribute.data.foreach_get('value', data)
            data = data.reshape(-1, len_attr)
        elif attribute.data_type == "FLOAT_VECTOR_4":  # Specific case for tangent
            pass  # TODOPC
        elif attribute.data_type == "INT":
            attribute.data.foreach_get('value', data)
            data = data.reshape(-1, len_attr)
        elif attribute.data_type == "FLOAT":
            attribute.data.foreach_get('value', data)
            data = data.reshape(-1, len_attr)
        else:
            export_settings['log'].error(
                "blender type not found " + attribute.data_type)
        if len_attr > 1:
            data = data.reshape(-1, len_attr)
        custom_attributes[attribute.name] = {
            'data': data,
            'data_type': gltf2_blender_conversion.get_data_type(attribute.data_type),
            'component_type': gltf2_blender_conversion.get_component_type(attribute.data_type)
        }
    return custom_attributes
