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
from os.path import dirname, join, isfile, basename


class BinaryData():
    """Binary reader."""
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("%s should not be instantiated" % cls)

    @staticmethod
    def get_binary_from_accessor(gltf, accessor_idx):
        """Get binary from accessor."""
        accessor = gltf.data.accessors[accessor_idx]
        bufferView = gltf.data.buffer_views[accessor.buffer_view]  # TODO initialize with 0 when not present!
        if bufferView.buffer in gltf.buffers.keys():
            buffer = gltf.buffers[bufferView.buffer]
        else:
            # load buffer
            gltf.load_buffer(bufferView.buffer)
            buffer = gltf.buffers[bufferView.buffer]

        accessor_offset = accessor.byte_offset
        bufferview_offset = bufferView.byte_offset

        if accessor_offset is None:
            accessor_offset = 0
        if bufferview_offset is None:
            bufferview_offset = 0

        return buffer[accessor_offset + bufferview_offset:accessor_offset + bufferview_offset + bufferView.byte_length]

    @staticmethod
    def get_data_from_accessor(gltf, accessor_idx):
        """Get data from accessor."""
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

        data = []
        offset = 0
        while len(data) < accessor.count:
            element = struct.unpack_from(fmt, buffer_data, offset)
            data.append(element)
            offset += stride

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

        data = []
        offset = 0
        while len(data) < sparse.count:
            element = struct.unpack_from(fmt, bin_data, offset)
            data.append(element)
            offset += stride

        return data

    @staticmethod
    def get_image_data(gltf, img_idx):
        """Get data from image."""
        pyimage = gltf.data.images[img_idx]

        image_name = "Image_" + str(img_idx)

        if pyimage.uri:
            sep = ';base64,'
            if pyimage.uri[:5] == 'data:':
                idx = pyimage.uri.find(sep)
                if idx != -1:
                    data = pyimage.uri[idx + len(sep):]
                    return base64.b64decode(data), image_name

            if isfile(join(dirname(gltf.filename), pyimage.uri)):
                with open(join(dirname(gltf.filename), pyimage.uri), 'rb') as f_:
                    return f_.read(), basename(join(dirname(gltf.filename), pyimage.uri))
            else:
                gltf.log.error("Missing file (index " + str(img_idx) + "): " + pyimage.uri)
                return None, None

        if pyimage.buffer_view is None:
            return None, None

        bufferView = gltf.data.buffer_views[pyimage.buffer_view]

        if bufferView.buffer in gltf.buffers.keys():
            buffer = gltf.buffers[bufferView.buffer]
        else:
            # load buffer
            gltf.load_buffer(bufferView.buffer)
            buffer = gltf.buffers[bufferView.buffer]

        bufferview_offset = bufferView.byte_offset

        if bufferview_offset is None:
            bufferview_offset = 0

        return buffer[bufferview_offset:bufferview_offset + bufferView.byte_length], image_name
