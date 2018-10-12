# Copyright 2018 The glTF-Blender-IO authors.
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

import functools


def cached(func):
    """
    Decorator to cache gather functions results. The gather function is only executed if its result isn't in the cache yet
    :param func: the function to be decorated. It will have a static __cache member afterwards
    :return:
    """
    @functools.wraps(func)
    def wrapper_cached(*args, **kwargs):
        assert len(args) == 2 and len(kwargs) == 0, "Wrong signature for cached function"
        blender_obj, export_settings = args
        # invalidate cache if export settings have changed
        if not hasattr(func, "__export_settings") or export_settings != func.__export_settings:
            func.__cache = {}
            func.__export_settings = export_settings
        # use or fill cache
        if blender_obj in func.__cache:
            return func.__cache[blender_obj]
        else:
            result = func(*args)
            func.__cache[blender_obj] = result
            return result
    return wrapper_cached