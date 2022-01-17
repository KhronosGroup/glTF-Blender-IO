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

import functools
import bpy
from io_scene_gltf2.blender.exp import gltf2_blender_get


def cached_by_key(key):
    """
    Decorates functions whose result should be cached. Use it like:
        @cached_by_key(key=...)
        def func(..., export_settings):
            ...
    The decorated function, func, must always take an "export_settings" arg
    (the cache is stored here).
    The key argument to the decorator is a function that computes the key to
    cache on. It is passed all the arguments to func.
    """
    def inner(func):
        @functools.wraps(func)
        def wrapper_cached(*args, **kwargs):
            if kwargs.get("export_settings"):
                export_settings = kwargs["export_settings"]
            else:
                export_settings = args[-1]

            cache_key = key(*args, **kwargs)

            # invalidate cache if export settings have changed
            if not hasattr(func, "__export_settings") or export_settings != func.__export_settings:
                func.__cache = {}
                func.__export_settings = export_settings
            # use or fill cache
            if cache_key in func.__cache:
                return func.__cache[cache_key]
            else:
                result = func(*args, **kwargs)
                func.__cache[cache_key] = result
                return result

        return wrapper_cached

    return inner


def default_key(*args, **kwargs):
    """
    Default cache key for @cached functions.
    Cache on all arguments (except export_settings).
    """
    assert len(args) >= 2 and 0 <= len(kwargs) <= 1, "Wrong signature for cached function"
    cache_key_args = args
    # make a shallow copy of the keyword arguments so that 'export_settings' can be removed
    cache_key_kwargs = dict(kwargs)
    if kwargs.get("export_settings"):
        del cache_key_kwargs["export_settings"]
    else:
        cache_key_args = args[:-1]

    cache_key = ()
    for i in cache_key_args:
        cache_key += (i,)
    for i in cache_key_kwargs.values():
        cache_key += (i,)

    return cache_key


def cached(func):
    return cached_by_key(key=default_key)(func)

def objectcache(func):

    def reset_cache_objectcache():
        func.__objectcache = {}

    func.reset_cache = reset_cache_objectcache

    @functools.wraps(func)
    def wrapper_objectcache(*args, **kwargs):
        cache_key_args = args
        cache_key_args = args[:-1]

        if not hasattr(func, "__objectcache"):
            func.reset_cache()

        # object is not cached yet
        if cache_key_args[0] not in func.__objectcache.keys():
            result = func(*args)
            func.__objectcache = result
            return result[cache_key_args[0]][cache_key_args[1]][cache_key_args[4]]
        # object is in cache, but not this action
        # We need to keep other actions
        elif cache_key_args[1] not in func.__objectcache[cache_key_args[0]].keys():
            result = func(*args)
            func.__objectcache[cache_key_args[0]][cache_key_args[1]] = result[cache_key_args[0]][cache_key_args[1]]
            return result[cache_key_args[0]][cache_key_args[1]][cache_key_args[4]]
        # all is already cached
        else:
            return func.__objectcache[cache_key_args[0]][cache_key_args[1]][cache_key_args[4]]
    return wrapper_objectcache

def bonecache(func):

    def reset_cache_bonecache():
        func.__current_action_name = None
        func.__current_armature_uuid = None
        func.__bonecache = {}

    func.reset_cache = reset_cache_bonecache

    @functools.wraps(func)
    def wrapper_bonecache(*args, **kwargs):

        armature = args[-1]['vtree'].nodes[args[0]].blender_object

        cache_key_args = args
        cache_key_args = args[:-1]

        if cache_key_args[2] is None:
            pose_bone_if_armature = gltf2_blender_get.get_object_from_datapath(armature,
                                                                cache_key_args[1][0].data_path)
        else:
            pose_bone_if_armature = armature.pose.bones[cache_key_args[2]]

        if not hasattr(func, "__current_action_name"):
            func.reset_cache()
        if cache_key_args[6] != func.__current_action_name or cache_key_args[0] != func.__current_armature_uuid:
            result = func(*args)
            func.__bonecache = result
            func.__current_action_name = cache_key_args[6]
            func.__current_armature_uuid = cache_key_args[0]
            return result[cache_key_args[7]][pose_bone_if_armature.name]
        else:
            return func.__bonecache[cache_key_args[7]][pose_bone_if_armature.name]
    return wrapper_bonecache

# TODO: replace "cached" with "unique" in all cases where the caching is functional and not only for performance reasons
call_or_fetch = cached
unique = cached

def skdriverdiscovercache(func):

    def reset_cache_skdriverdiscovercache():
        func.__current_armature_uuid = None
        func.__skdriverdiscover = {}

    func.reset_cache = reset_cache_skdriverdiscovercache

    @functools.wraps(func)
    def wrapper_skdriverdiscover(*args, **kwargs):

        cache_key_args = args
        cache_key_args = args[:-1]

        if not hasattr(func, "__current_armature_uuid") or func.__current_armature_uuid is None:
            func.reset_cache()

        if cache_key_args[0] != func.__current_armature_uuid:
            result = func(*args)
            func.__skdriverdiscover[cache_key_args[0]] = result
            func.__current_armature_uuid = cache_key_args[0]
            return result
        else:
            return func.__skdriverdiscover[cache_key_args[0]]
    return wrapper_skdriverdiscover

def skdrivervalues(func):

    def reset_cache_skdrivervalues():
        func.__skdrivervalues = {}

    func.reset_cache = reset_cache_skdrivervalues

    @functools.wraps(func)
    def wrapper_skdrivervalues(*args, **kwargs):
        if not hasattr(func, "__skdrivervalues") or func.__skdrivervalues is None:
            func.reset_cache()

        armature = args[-1]['vtree'].nodes[args[0]].blender_object

        cache_key_args = args
        cache_key_args = args[:-1]

        if armature.name not in func.__skdrivervalues.keys():
            func.__skdrivervalues[armature.name] = {}
        if cache_key_args[1] not in func.__skdrivervalues[armature.name]:
            vals = func(*args)
            func.__skdrivervalues[armature.name][cache_key_args[1]] = vals
            return vals
        else:
            return func.__skdrivervalues[armature.name][cache_key_args[1]]
    return wrapper_skdrivervalues
