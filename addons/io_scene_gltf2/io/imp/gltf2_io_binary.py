# Copyright 2018-2019 The glTF-Blender-IO authors.
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

import struct
import base64

from ..com.gltf2_io import Accessor


class BinaryData():
    """Binary reader."""
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("%s should not be instantiated" % cls)

    @staticmethod
    def get_binary_from_accessor(gltf, accessor_idx):
        """Get binary from accessor."""
        accessor = gltf.data.accessors[accessor_idx]
        if accessor.buffer_view is None:
            return None

        data = BinaryData.get_buffer_view(gltf, accessor.buffer_view)

        accessor_offset = accessor.byte_offset
        if accessor_offset is None:
            accessor_offset = 0

        return data[accessor_offset:]

    @staticmethod
    def get_buffer_view(gltf, buffer_view_idx):
        """Get binary data for buffer view."""
        buffer_view = gltf.data.buffer_views[buffer_view_idx]

        if buffer_view.buffer in gltf.buffers.keys():
            buffer = gltf.buffers[buffer_view.buffer]
        else:
            # load buffer
            gltf.load_buffer(buffer_view.buffer)
            buffer = gltf.buffers[buffer_view.buffer]

        byte_offset = buffer_view.byte_offset
        if byte_offset is None:
            byte_offset = 0

        return buffer[byte_offset:byte_offset + buffer_view.byte_length]

    @staticmethod
    def get_data_from_accessor(gltf, accessor_idx, cache=False):
        """Get data from accessor."""
        if accessor_idx in gltf.accessor_cache:
            return gltf.accessor_cache[accessor_idx]

        accessor = gltf.data.accessors[accessor_idx]
        data = BinaryData.get_data_from_accessor_obj(gltf, accessor)

        if cache:
            gltf.accessor_cache[accessor_idx] = data

        return data

    @staticmethod
    def get_data_from_accessor_obj(gltf, accessor):
        if accessor.buffer_view is not None:
            bufferView = gltf.data.buffer_views[accessor.buffer_view]
            buffer_data = BinaryData.get_buffer_view(gltf, accessor.buffer_view)

            accessor_offset = accessor.byte_offset or 0
            buffer_data = buffer_data[accessor_offset:]

            fmt_char = gltf.fmt_char_dict[accessor.component_type]
            component_nb = gltf.component_nb_dict[accessor.type]
            fmt = '<' + (fmt_char * component_nb)
            default_stride = struct.calcsize(fmt)

            # TODO data alignment stuff

            stride = bufferView.byte_stride or default_stride

            # Decode
            unpack_from = struct.Struct(fmt).unpack_from
            data = [
                unpack_from(buffer_data, offset)
                for offset in range(0, accessor.count*stride, stride)
            ]

        else:
            # No buffer view; initialize to zeros
            component_nb = gltf.component_nb_dict[accessor.type]
            data = [
                (0,) * component_nb
                for i in range(accessor.count)
            ]

        if accessor.sparse:
            sparse_indices_obj = Accessor.from_dict({
                'count': accessor.sparse.count,
                'bufferView': accessor.sparse.indices.buffer_view,
                'byteOffset': accessor.sparse.indices.byte_offset or 0,
                'componentType': accessor.sparse.indices.component_type,
                'type': 'SCALAR',
            })
            sparse_values_obj = Accessor.from_dict({
                'count': accessor.sparse.count,
                'bufferView': accessor.sparse.values.buffer_view,
                'byteOffset': accessor.sparse.values.byte_offset or 0,
                'componentType': accessor.component_type,
                'type': accessor.type,
            })
            sparse_indices = BinaryData.get_data_from_accessor_obj(gltf, sparse_indices_obj)
            sparse_values = BinaryData.get_data_from_accessor_obj(gltf, sparse_values_obj)

            # Apply sparse
            for i in range(accessor.sparse.count):
                data[sparse_indices[i][0]] = sparse_values[i]

        # Normalization
        if accessor.normalized:
            for idx, tuple in enumerate(data):
                new_tuple = ()
                for i in tuple:
                    if accessor.component_type == 5120:
                        new_tuple += (max(float(i / 127.0 ), -1.0),)
                    elif accessor.component_type == 5121:
                        new_tuple += (float(i / 255.0),)
                    elif accessor.component_type == 5122:
                        new_tuple += (max(float(i / 32767.0), -1.0),)
                    elif accessor.component_type == 5123:
                        new_tuple += (i / 65535.0,)
                    else:
                        new_tuple += (float(i),)
                data[idx] = new_tuple

        return data

    @staticmethod
    def get_image_data(gltf, img_idx):
        """Get data from image."""
        pyimage = gltf.data.images[img_idx]
        image_name = "Image_" + str(img_idx)

        assert(not (pyimage.uri is not None and pyimage.buffer_view is not None))

        if pyimage.uri is not None:
            data, file_name = gltf.load_uri(pyimage.uri)
            return data, file_name or image_name

        elif pyimage.buffer_view is not None:
            data = BinaryData.get_buffer_view(gltf, pyimage.buffer_view)
            return data, image_name

        return None, None
