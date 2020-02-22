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

def test_color_linear_to_srgb():
    """Ensure the array version gives the right results and is fast"""
    from pytest import approx
    from numpy.random import default_rng
    import time

    n_elements = 10000000              # test this many random values
    expect_elements_per_sec = 10000000 # as of 2020 on an Intel i7; conservative
    expect_max_time = n_elements / expect_elements_per_sec # in sec

    rng = default_rng()
    a = rng.uniform(-10, 100, size=n_elements)
    # Should be fast with numpy
    t0 = time.perf_counter()
    srgb = color_linear_to_srgb(a)
    assert time.perf_counter() - t0 < expect_max_time
    assert a.shape == srgb.shape
    # Just compare some of them, for speed
    for i in range(0, min(100000, len(a))):
        assert srgb[i] == approx(color_linear_to_srgb(a[i]))

def test_color_linear_to_srgb_2d():
    """Ensure it works with a 2d array of colors where each element is RGB/RGBA"""
    from pytest import approx

    a = np.array([[0, 1, 2], [2, 3, 4]], dtype=np.float32)
    srgb = color_linear_to_srgb(a)
    assert a.shape == srgb.shape
    expected = np.reshape([color_linear_to_srgb(x) for x in a.flatten()], a.shape)
    np.testing.assert_allclose(srgb, expected)

    a = np.array([[0, 1, 2, 0.1], [2, 3, 4, 0.5]], dtype=np.float32)
    srgb = color_linear_to_srgb(a)
    assert a.shape == srgb.shape
    expected = np.reshape([color_linear_to_srgb(x) for x in a.flatten()], a.shape)
    expected[:, 3] = a[:, 3] # it shouldn't process alpha
    np.testing.assert_allclose(srgb, expected)
