# Copyright 2018-2022 The glTF-Blender-IO authors.
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
import numpy as np
from .gltf2_blender_gather_image import StoreImage, StoreData
from .gltf2_blender_image import TmpImageGuard, make_temp_image_copy

def sheen_calculation(stored):
    lerp = lambda a, b, v: (1-v)*a + v*b
    luminance = lambda c: 0.3 * c[:,:,0] + 0.6 * c[:,:,1] + 0.1 * c[:,:,2]
    stack3 = lambda v: np.dstack([v]*3)

    # Find all Blender images used
    images = []
    for fill in stored.values():
        if isinstance(fill, StoreImage):
            if fill.image not in images:
                images.append(fill.image)

    if not images:
        # No ImageFills; use a 1x1 white pixel
        pixels = np.array([1.0, 1.0, 1.0, 1.0], np.float32)
        return pixels, 1, 1

    width = max(image.size[0] for image in images)
    height = max(image.size[1] for image in images)

    buffers = {}

    for identifier, image in [(ident, store.image) for (ident, store) in stored.items() if isinstance(store, StoreImage)]:
        tmp_buf = np.empty(width * height * 4, np.float32)
        
        if image.size[0] == width and image.size[1] == height:
            image.pixels.foreach_get(tmp_buf)
        else:
            # Image is the wrong size; make a temp copy and scale it.
            with TmpImageGuard() as guard:
                make_temp_image_copy(guard, src_image=image)
                tmp_image = guard.image
                tmp_image.scale(width, height)
                tmp_image.pixels.foreach_get(tmp_buf)

        buffers[identifier] = np.reshape(tmp_buf, [width, height, 4])

    # keep only needed channels
    ## scalar
    for i in ['sheen', 'sheen_tint']:
        if i in buffers.keys():
            buffers[i] = buffers[i][:,:,stored[i + "_channel"].data]
        else:
            buffers[i] = np.full((height, width, 1), stored[i].data)

    # Vector 3
    for i in ['base_color']:
        if i in buffers.keys():
            if i + "_channel" not in stored.keys():
                buffers[i] = buffers[i][:,:,:3]
            else:
                # keep only needed channel
                for c in range(3):
                    if c != stored[i+"_channel"].data:
                        buffers[i][:, :, c] = 0.0
                buffers[i] = buffers[i][:,:,:3]
        else:
            buffers[i] = np.full((height, width, 3), stored[i].data[0:3])

    
    # calculation
    # TODOExt Approximation discussion in progress
    
    tint_from_color = buffers['base_color'] / stack3(luminance(buffers['base_color']))
    np.nan_to_num(tint_from_color, copy=False, nan=0.0)     # if luminance in a pixel was zero

    out_buf = lerp(tint_from_color, stack3(buffers['sheen_tint']), stack3(buffers['sheen']))
    out_buf = np.clip(out_buf, 0.0, 1.0)
    out_buf = np.dstack((out_buf, np.ones((height, width)))) # Set alpha to 1
    out_buf = np.reshape(out_buf, (width * height * 4))

    return np.float32(out_buf), width, height, [1.0, 1.0, 1.0]
