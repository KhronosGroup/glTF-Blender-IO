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

#TODOVariants : Add a first level with file, to manage importing multiple files with each independant variants?

# Operator to assign a variant to objects
class SCENE_OT_gltf2_assign_variant(bpy.types.Operator):
    bl_idname = "scene.gltf2_assign_variant"
    bl_label = "Display Text"
    bl_options = {'REGISTER'}


    @classmethod
    def poll(self, context):
        return True #TODOVariants check there are variants

    def execute(self, context):

        gltf2_active_variant = bpy.data.scenes[0].gltf2_active_variant

        # loop on all mesh
        for obj in [o for o in bpy.data.objects if o.type == "MESH"]:
            mesh = obj.data
            for i in mesh.gltf2_variant_mesh_data:
                if i.variants and gltf2_active_variant in [v.variant.variant_idx for v in i.variants]:
                    mat = i.material
                    slot = i.material_slot_index
                    obj.material_slots[slot].material = mat

        return {'FINISHED'}

def op_register():
    bpy.utils.register_class(SCENE_OT_gltf2_assign_variant)

def op_unregister():
    bpy.utils.unregister_class(SCENE_OT_gltf2_assign_variant)
