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


class BinaryData():
    """Binary reader."""
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("%s should not be instantiated" % cls)

    @staticmethod
    def get_binary_from_accessor(gltf, accessor_idx):
        """Get binary from accessor."""
        accessor = gltf.data.accessors[accessor_idx]
        data = BinaryData.get_buffer_view(gltf, accessor.buffer_view) # TODO initialize with 0 when not present!

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

        bufferView = gltf.data.buffer_views[accessor.buffer_view]  # TODO initialize with 0 when not present!
        buffer_data = BinaryData.get_binary_from_accessor(gltf, accessor_idx)

        fmt_char = gltf.fmt_char_dict[accessor.component_type]
        component_nb = gltf.component_nb_dict[accessor.type]
        fmt = '<' + (fmt_char * component_nb)
        stride_ = struct.calcsize(fmt)
        # TODO data alignment stuff

        if bufferView.byte_stride:
            stride = bufferView.byte_stride
        else:
            stride = stride_

        unpack_from = struct.Struct(fmt).unpack_from
        data = [
            unpack_from(buffer_data, offset)
            for offset in range(0, accessor.count*stride, stride)
        ]

        if accessor.sparse:
            sparse_indices_data = BinaryData.get_data_from_sparse(gltf, accessor.sparse, "indices")
            sparse_values_values = BinaryData.get_data_from_sparse(
                gltf,
                accessor.sparse,
                "values",
                accessor.type,
                accessor.component_type
            )

            # apply sparse
            for cpt_idx, idx in enumerate(sparse_indices_data):
                data[idx[0]] = sparse_values_values[cpt_idx]

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

        if cache:
            gltf.accessor_cache[accessor_idx] = data

        return data

    @staticmethod
    def get_data_from_sparse(gltf, sparse, type_, type_val=None, comp_type=None):
        """Get data from sparse."""
        if type_ == "indices":
            bufferView = gltf.data.buffer_views[sparse.indices.buffer_view]
            offset = sparse.indices.byte_offset
            component_nb = gltf.component_nb_dict['SCALAR']
            fmt_char = gltf.fmt_char_dict[sparse.indices.component_type]
        elif type_ == "values":
            bufferView = gltf.data.buffer_views[sparse.values.buffer_view]
            offset = sparse.values.byte_offset
            component_nb = gltf.component_nb_dict[type_val]
            fmt_char = gltf.fmt_char_dict[comp_type]

        if bufferView.buffer in gltf.buffers.keys():
            buffer = gltf.buffers[bufferView.buffer]
        else:
            # load buffer
            gltf.load_buffer(bufferView.buffer)
            buffer = gltf.buffers[bufferView.buffer]

        bin_data = buffer[bufferView.byte_offset + offset:bufferView.byte_offset + offset + bufferView.byte_length]

        fmt = '<' + (fmt_char * component_nb)
        stride_ = struct.calcsize(fmt)
        # TODO data alignment stuff ?

        if bufferView.byte_stride:
            stride = bufferView.byte_stride
        else:
            stride = stride_

        unpack_from = struct.Struct(fmt).unpack_from
        data = [
            unpack_from(bin_data, offset)
            for offset in range(0, sparse.count*stride, stride)
        ]

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
