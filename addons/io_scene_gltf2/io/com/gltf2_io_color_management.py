# Copyright 2019 The glTF-Blender-IO authors.
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

def color_srgb_to_scene_linear(c):
    """
    Convert from sRGB to scene linear color space.

    Source: Cycles addon implementation, node_color.h.
    """
    if c < 0.04045:
        return 0.0 if c < 0.0 else c * (1.0 / 12.92)
    else:
        return pow((c + 0.055) * (1.0 / 1.055), 2.4)

def color_linear_to_srgb(c):
    """
    Convert from linear to sRGB color space.

    Source: Cycles addon implementation, node_color.h.
    c may be a single color value or an array.

    If c's last dimension is 4, it's assumed to be RGBA and the
    alpha channel is not converted.
    """
    if type(c) in (list, np.ndarray):
        colors = np.array(c, np.float32) if type(c) == list else c
        if  colors.ndim > 1 and colors.shape[-1] == 4:
            colors_noa = colors[..., 0:3] # only process RGB for speed
        else:
            colors_noa = colors
        not_small = colors_noa >= 0.0031308
        small_result = np.where(colors_noa < 0.0, 0.0, colors_noa * 12.92)
        large_result = 1.055 * np.power(colors_noa, 1.0 / 2.4, where=not_small) - 0.055
        result = np.where(not_small, large_result, small_result)
        if  colors.ndim > 1 and colors.shape[-1] == 4:
            # copy alpha from original
            result = np.concatenate((result, colors[..., 3, np.newaxis]), axis=-1)
        return result
    else:
        if c < 0.0031308:
            return 0.0 if c < 0.0 else c * 12.92
        else:
            return 1.055 * pow(c, 1.0 / 2.4) - 0.055
