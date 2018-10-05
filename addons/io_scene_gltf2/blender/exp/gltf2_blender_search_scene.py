# Copyright (c) 2017 The Khronos Group Inc.
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
import typing
from abc import ABC


class Filter:
    """
    Base class for all node tree filter operations
    """
    def __call__(self, obj: bpy.types.Object):
        return True


class ByName(Filter):
    """
    Filter the objects by name

    example usage:
    find_objects(FilterByName("Cube"))
    """
    def __init__(self, name):
        self.name = name

    def __call__(self, obj: bpy.types.Object):
        return obj.name == self.name


class ByDataType(Filter):
    """
    Filter the scene objects by their data type
    """
    def __init__(self, data_type: str):
        self.type = data_type

    def __call__(self, obj: bpy.types.Object):
        return obj.type == self.type


class ByDataInstance(Filter):
    """
    Filter the scene objects by a specific ID instance
    """
    def __init__(self, data_instance: bpy.types.ID):
        self.data = data_instance

    def __call__(self, obj: bpy.types.Object):
        return self.data == obj.data


def find_objects(object_filter: typing.Union[Filter, typing.Callable]):
    """
    Find objects in the scene where the filter expression is true.
    :param object_filter: should be a function(x: object) -> bool
    :return: a list of shader nodes for which filter is true
    """
    results = []
    for obj in bpy.context.scene.objects:
        if object_filter(obj):
            results.append(obj)
    return results


def find_objects_from(obj: bpy.types.Object, object_filter: typing.Union[Filter, typing.Callable]):
    """
    Search for objects matching a filter function below a specified object
    :param obj: the starting point of the search
    :param object_filter: a function(x: object) -> bool
    :return: a list of objects which passed the filter
    """
    results = []
    if object_filter(obj):
        results.append(obj)
    for child in obj.children:
        results += find_objects_from(child, object_filter)
    return results
