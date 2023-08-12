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

import bpy

from ...io.com import gltf2_io
from ...io.exp.gltf2_io_user_extensions import export_user_extensions
from ..com.gltf2_blender_extras import generate_extras
from .gltf2_blender_gather_cache import cached
from . import gltf2_blender_gather_nodes
from . import gltf2_blender_gather_tree
from .animation.sampled.object.gltf2_blender_gather_object_keyframes import get_cache_data
from .animation.gltf2_blender_gather_animations import gather_animations


def gather_gltf2(export_settings):
    """
    Gather glTF properties from the current state of blender.

    :return: list of scene graphs to be added to the glTF export
    """
    scenes = []
    animations = []  # unfortunately animations in gltf2 are just as 'root' as scenes.
    active_scene = None
    store_user_scene = bpy.context.scene
    scenes_to_export = bpy.data.scenes if export_settings['gltf_active_scene'] is False else [scene for scene in bpy.data.scenes if scene.name == store_user_scene.name]
    for blender_scene in scenes_to_export:
        scenes.append(__gather_scene(blender_scene, export_settings))
        if export_settings['gltf_animations']:
            # resetting object cache
            get_cache_data.reset_cache()
            animations += gather_animations(export_settings)
        if bpy.context.scene.name == store_user_scene.name:
            active_scene = len(scenes) -1

    # restore user scene
    bpy.context.window.scene = store_user_scene
    return active_scene, scenes, animations


@cached
def __gather_scene(blender_scene, export_settings):
    scene = gltf2_io.Scene(
        extensions=None,
        extras=__gather_extras(blender_scene, export_settings),
        name=blender_scene.name,
        nodes=[]
    )


    vtree = gltf2_blender_gather_tree.VExportTree(export_settings)
    vtree.construct(blender_scene)
    vtree.search_missing_armature() # In case armature are no parented correctly

    export_user_extensions('vtree_before_filter_hook', export_settings, vtree)

    # Now, we can filter tree if needed
    vtree.filter()
    if export_settings['gltf_flatten_bones_hierarchy'] is True:
        vtree.break_bone_hierarchy()
    if export_settings['gltf_flatten_obj_hierarchy'] is True:
        vtree.break_obj_hierarchy()

    vtree.variants_reset_to_original()

    export_user_extensions('vtree_after_filter_hook', export_settings, vtree)

    export_settings['vtree'] = vtree

    for r in [vtree.nodes[r] for r in vtree.roots]:
        node = gltf2_blender_gather_nodes.gather_node(
            r, export_settings)
        if node is not None:
            scene.nodes.append(node)

    vtree.add_neutral_bones()

    export_user_extensions('gather_scene_hook', export_settings, scene, blender_scene)

    return scene


def __gather_extras(blender_object, export_settings):
    if export_settings['gltf_extras']:
        return generate_extras(blender_object)
    return None
