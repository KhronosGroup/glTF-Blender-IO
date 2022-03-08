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
from ..com.gltf2_blender_material_helpers import get_gltf_node_name, create_settings_group

def create_gltf_ao_group(operator, group_name):

    # create a new group
    gltf_ao_group = bpy.data.node_groups.new(group_name, "ShaderNodeTree")
    
    return gltf_ao_group

class NODE_OT_GLTF_SETTINGS(bpy.types.Operator):
    bl_idname = "node.gltf_settings_node_operator"
    bl_label  = "glTF Settings"


    @classmethod
    def poll(cls, context):
        space = context.space_data
        return space.type == "NODE_EDITOR" \
            and context.object and context.object.active_material \
            and context.object.active_material.use_nodes is True \
            and bpy.context.preferences.addons['io_scene_gltf2'].preferences.settings_node_ui is True

    def execute(self, context):
        gltf_settings_node_name = get_gltf_node_name()
        if gltf_settings_node_name in bpy.data.node_groups:
            my_group = bpy.data.node_groups[get_gltf_node_name()]
        else:
            my_group = create_settings_group(gltf_settings_node_name)
        node_tree = context.object.active_material.node_tree
        new_node = node_tree.nodes.new("ShaderNodeGroup")
        new_node.node_tree = bpy.data.node_groups[my_group.name]
        return {"FINISHED"}


def add_gltf_settings_to_menu(self, context) :
    if bpy.context.preferences.addons['io_scene_gltf2'].preferences.settings_node_ui is True:
        self.layout.operator("node.gltf_settings_node_operator")


def register():
    bpy.utils.register_class(NODE_OT_GLTF_SETTINGS)
    bpy.types.NODE_MT_category_SH_NEW_OUTPUT.append(add_gltf_settings_to_menu)

def unregister():
    bpy.utils.unregister_class(NODE_OT_GLTF_SETTINGS)
