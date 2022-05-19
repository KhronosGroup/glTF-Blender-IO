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


################ glTF Settings node ###########################################

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


################################### KHR_materials_variants ####################

# Global UI panel

# TODOVariant : remove a variant
# TODOVariant : remove a variant slot in material

class gltf2_KHR_materials_variants_variant(bpy.types.PropertyGroup):
    variant_idx : bpy.props.IntProperty()
    name : bpy.props.StringProperty(name="Variant Name")

class SCENE_UL_gltf2_variants(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):

        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.prop(item, "name", text="", emboss=False)

        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'

class SCENE_PT_gltf2_variants(bpy.types.Panel):
    bl_label = "glTF Material Variants"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "glTF Variants"

    @classmethod
    def poll(self, context):
        return bpy.context.preferences.addons['io_scene_gltf2'].preferences.KHR_materials_variants_ui is True

    def draw(self, context):
        layout = self.layout
        row = layout.row()

        if bpy.data.scenes[0].get('gltf2_KHR_materials_variants_variants') and len(bpy.data.scenes[0].gltf2_KHR_materials_variants_variants) > 0:

            row.template_list("SCENE_UL_gltf2_variants", "", bpy.data.scenes[0], "gltf2_KHR_materials_variants_variants", bpy.data.scenes[0], "gltf2_active_variant")
            col = row.column()
            row = col.column(align=True)
            row.operator("scene.gltf2_variant_add", icon="ADD", text="")

            row = layout.row()
            row.operator("scene.gltf2_display_variant", text="Display Variant")
            row = layout.row()
            row.operator("scene.gltf2_assign_to_variant", text="Assign To Variant")
            row = layout.row()
            row.operator("scene.gltf2_reset_to_original", text="Reset To Original")
            row.operator("scene.gltf2_assign_as_original", text="Assign as Original")
        else:
            row.operator("scene.gltf2_variant_add", text="Add Material Variant")

class SCENE_OT_gltf2_variant_add(bpy.types.Operator):
    """Add a new Material Variant"""
    bl_idname = "scene.gltf2_variant_add"
    bl_label = "Add Material Variant"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(self, context):
        return True

    def execute(self, context):
        if 'gltf2_KHR_materials_variants_variants' not in bpy.data.scenes[0].keys():
            bpy.types.Scene.gltf2_KHR_materials_variants_variants = bpy.props.CollectionProperty(type=gltf2_KHR_materials_variants_variant)
            bpy.types.Scene.gltf2_active_variant = bpy.props.IntProperty()

        var = bpy.data.scenes[0].gltf2_KHR_materials_variants_variants.add()
        var.variant_idx = len(bpy.data.scenes[0].gltf2_KHR_materials_variants_variants) - 1
        var.name = "VariantName"
        bpy.data.scenes[0].gltf2_active_variant = len(bpy.data.scenes[0].gltf2_KHR_materials_variants_variants) - 1
        return {'FINISHED'}


# Operator to display a variant
class SCENE_OT_gltf2_display_variant(bpy.types.Operator):
    bl_idname = "scene.gltf2_display_variant"
    bl_label = "Display Variant"
    bl_options = {'REGISTER'}


    @classmethod
    def poll(self, context):
        return len(bpy.data.scenes[0].gltf2_KHR_materials_variants_variants) > 0

    def execute(self, context):

        gltf2_active_variant = bpy.data.scenes[0].gltf2_active_variant

        # loop on all mesh
        for obj in [o for o in bpy.data.objects if o.type == "MESH"]:
            mesh = obj.data
            for i in mesh.gltf2_variant_mesh_data:
                if i.variants and gltf2_active_variant in [v.variant.variant_idx for v in i.variants]:
                    mat = i.material
                    slot = i.material_slot_index
                    if slot < len(obj.material_slots): # Seems user remove some slots...
                        obj.material_slots[slot].material = mat

        return {'FINISHED'}

# Operator to assign current mesh materials to a variant
class SCENE_OT_gltf2_assign_to_variant(bpy.types.Operator):
    bl_idname = "scene.gltf2_assign_to_variant"
    bl_label = "Assign To Variant"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(self, context):
        return len(bpy.data.scenes[0].gltf2_KHR_materials_variants_variants) > 0 \
            and bpy.context.object.type == "MESH"

    def execute(self, context):
        gltf2_active_variant = bpy.data.scenes[0].gltf2_active_variant
        obj = bpy.context.object

        # loop on material slots ( primitives )
        for mat_slot_idx, s in enumerate(obj.material_slots):
            # Check if there is already data for this slot
            found = False
            for i in obj.data.gltf2_variant_mesh_data:
                if i.material_slot_index == mat_slot_idx and i.material == s.material:
                    found = True
                    variant_primitive = i

            if found is False:
                variant_primitive = obj.data.gltf2_variant_mesh_data.add()
                variant_primitive.material_slot_index = mat_slot_idx
                variant_primitive.material = s.material

            vari = variant_primitive.variants.add()
            vari.variant.variant_idx = bpy.data.scenes[0].gltf2_active_variant

        return {'FINISHED'}

# Operator to reset mesh to orignal (using default material when exists)
class SCENE_OT_gltf2_reset_to_original(bpy.types.Operator):
    bl_idname = "scene.gltf2_reset_to_original"
    bl_label = "Reset to Orignal"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(self, context):
        return bpy.context.object.type == "MESH" and len(context.object.data.gltf2_variant_default_materials) > 0

    def execute(self, context):
        obj = bpy.context.object

        # loop on material slots ( primitives )
        for mat_slot_idx, s in enumerate(obj.material_slots):
            # Check if there is a default material for this slot
            found = False
            for i in obj.data.gltf2_variant_default_materials:
                if i.material_slot_index == mat_slot_idx:
                    s.material = i.default_material
                    break

        return {'FINISHED'}

# Operator to assign current materials as default materials
class SCENE_OT_gltf2_assign_as_original(bpy.types.Operator):
    bl_idname = "scene.gltf2_assign_as_original"
    bl_label = "Assign as Original"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(self, context):
        return bpy.context.object.type == "MESH"

    def execute(self, context):
        obj = bpy.context.object

        # loop on material slots ( primitives )
        for mat_slot_idx, s in enumerate(obj.material_slots):
            # Check if there is a default material for this slot
            found = False
            for i in obj.data.gltf2_variant_default_materials:
                if i.material_slot_index == mat_slot_idx:
                    found = True
                    # Update if needed
                    i.default_material = s.material
                    break

            if found is False:
                default_mat = obj.data.gltf2_variant_default_materials.add()
                default_mat.material_slot_index = mat_slot_idx
                default_mat.default_material = s.material

        return {'FINISHED'}

# Mesh Panel

class gltf2_KHR_materials_variant_pointer(bpy.types.PropertyGroup):
    variant: bpy.props.PointerProperty(type=gltf2_KHR_materials_variants_variant)

class gltf2_KHR_materials_variants_default_material(bpy.types.PropertyGroup):
    material_slot_index: bpy.props.IntProperty(name="Material Slot Index")
    default_material: bpy.props.PointerProperty(type=bpy.types.Material)

class gltf2_KHR_materials_variants_primitive(bpy.types.PropertyGroup):
    material_slot_index : bpy.props.IntProperty(name="Material Slot Index")
    material: bpy.props.PointerProperty(type=bpy.types.Material)
    variants: bpy.props.CollectionProperty(type=gltf2_KHR_materials_variant_pointer)
    active_variant_idx: bpy.props.IntProperty()

class MESH_UL_gltf2_mesh_variants(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):

        vari = item.variant
        layout.context_pointer_set("id", vari)

        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.prop(bpy.data.scenes[0].gltf2_KHR_materials_variants_variants[vari.variant_idx], "name", text="", emboss=False)
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'

class MESH_PT_gltf2_mesh_variants(bpy.types.Panel):
    bl_label = "glTF Material Variants"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "material"

    @classmethod
    def poll(self, context):
        return bpy.context.preferences.addons['io_scene_gltf2'].preferences.KHR_materials_variants_ui is True \
            and len(bpy.context.object.material_slots) > 0

    def draw(self, context):
        layout = self.layout

        active_material_slots = bpy.context.object.active_material_index

        found = False
        if 'gltf2_variant_mesh_data' in bpy.context.object.data.keys():
            for idx, prim in enumerate(bpy.context.object.data.gltf2_variant_mesh_data):
                if prim.material_slot_index == active_material_slots and id(prim.material) == id(bpy.context.object.material_slots[active_material_slots].material):
                    found = True
                    break

        row = layout.row()
        if found is True:
            row.template_list("MESH_UL_gltf2_mesh_variants", "", prim, "variants", prim, "active_variant_idx")
            col = row.column()
            row = col.column(align=True)
            row.operator("scene.gltf2_variants_slot_add", icon="ADD", text="")

            row = layout.row()
            if 'gltf2_KHR_materials_variants_variants' in bpy.data.scenes[0].keys() and len(bpy.data.scenes[0].gltf2_KHR_materials_variants_variants) > 0:
                row.prop_search(context.object.data, "gltf2_variant_pointer", bpy.data.scenes[0], "gltf2_KHR_materials_variants_variants", text="Variant")
                row = layout.row()
                row.operator("scene.gltf2_material_to_variant", text="Assign To Variant")
            else:
                row.label(text="Please Create a Variant First")
        else:
            if 'gltf2_KHR_materials_variants_variants' in bpy.data.scenes[0].keys() and len(bpy.data.scenes[0].gltf2_KHR_materials_variants_variants) > 0:
                row.operator("scene.gltf2_variants_slot_add", text="Add a new Variant Slot")
            else:
                row.label(text="Please Create a Variant First")


class SCENE_OT_gltf2_variant_slot_add(bpy.types.Operator):
    """Add a new Slot"""
    bl_idname = "scene.gltf2_variants_slot_add"
    bl_label = "Add new Slot"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(self, context):
        return len(bpy.context.object.material_slots) > 0

    def execute(self, context):
        mesh = context.object.data
        if 'gltf2_variant_mesh_data' not in mesh.keys():
            bpy.types.Mesh.gltf2_variant_mesh_data = bpy.props.CollectionProperty(type=gltf2_KHR_materials_variants_primitive)
            bpy.types.Mesh.gltf2_variant_default_materials = bpy.props.CollectionProperty(type=gltf2_KHR_materials_variants_default_material)
            bpy.types.Mesh.gltf2_variant_pointer = bpy.props.StringProperty()

        if 'gltf2_KHR_materials_variants_variants' not in bpy.data.scenes[0].keys():
            bpy.types.Scene.gltf2_KHR_materials_variants_variants = bpy.props.CollectionProperty(type=gltf2_KHR_materials_variants_variant)
            bpy.types.Scene.gltf2_active_variant = bpy.props.IntProperty()

        # Check if there is already a data for this slot_idx + material

        found = False
        for i in mesh.gltf2_variant_mesh_data:
            if i.material_slot_index == context.object.active_material_index and i.material == context.object.material_slots[context.object.active_material_index].material:
                found = True
                variant_primitive = i

        if found is False:
            variant_primitive = mesh.gltf2_variant_mesh_data.add()
            variant_primitive.material_slot_index = context.object.active_material_index
            variant_primitive.material = context.object.material_slots[context.object.active_material_index].material

        vari = variant_primitive.variants.add()
        vari.variant.variant_idx = bpy.data.scenes[0].gltf2_active_variant

        return {'FINISHED'}

class SCENE_OT_gltf2_material_to_variant(bpy.types.Operator):
    """Assign Variant to Slot"""
    bl_idname = "scene.gltf2_material_to_variant"
    bl_label = "Assign Material To Variant"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(self, context):
        return len(bpy.context.object.material_slots) > 0 and context.object.data.gltf2_variant_pointer != ""

    def execute(self, context):
        mesh = context.object.data

        found = False
        for i in mesh.gltf2_variant_mesh_data:
            if i.material_slot_index == context.object.active_material_index and i.material == context.object.material_slots[context.object.active_material_index].material:
                found = True
                variant_primitive = i

        if found is False:
            return {'CANCELLED'}

        vari = variant_primitive.variants[variant_primitive.active_variant_idx]

        # Retrieve variant idx
        found = False
        for v in bpy.data.scenes[0].gltf2_KHR_materials_variants_variants:
            if v.name == context.object.data.gltf2_variant_pointer:
                found = True
                break

        if found is False:
            return {'CANCELLED'}

        vari.variant.variant_idx = v.variant_idx

        return {'FINISHED'}

###############################################################################



def register():
    bpy.utils.register_class(NODE_OT_GLTF_SETTINGS)
    bpy.utils.register_class(SCENE_OT_gltf2_display_variant)
    bpy.utils.register_class(SCENE_OT_gltf2_assign_to_variant)
    bpy.utils.register_class(SCENE_OT_gltf2_reset_to_original)
    bpy.utils.register_class(SCENE_OT_gltf2_assign_as_original)
    bpy.utils.register_class(gltf2_KHR_materials_variants_variant)
    bpy.utils.register_class(gltf2_KHR_materials_variant_pointer)
    bpy.utils.register_class(gltf2_KHR_materials_variants_primitive)
    bpy.utils.register_class(gltf2_KHR_materials_variants_default_material)
    bpy.utils.register_class(SCENE_UL_gltf2_variants)
    bpy.utils.register_class(SCENE_PT_gltf2_variants)
    bpy.utils.register_class(MESH_UL_gltf2_mesh_variants)
    bpy.utils.register_class(MESH_PT_gltf2_mesh_variants)
    bpy.utils.register_class(SCENE_OT_gltf2_variant_add)
    bpy.utils.register_class(SCENE_OT_gltf2_material_to_variant)
    bpy.utils.register_class(SCENE_OT_gltf2_variant_slot_add)
    bpy.types.NODE_MT_category_SH_NEW_OUTPUT.append(add_gltf_settings_to_menu)
    if bpy.context.preferences.addons['io_scene_gltf2'].preferences.KHR_materials_variants_ui is True:
        bpy.types.Mesh.gltf2_variant_mesh_data = bpy.props.CollectionProperty(type=gltf2_KHR_materials_variants_primitive)
        bpy.types.Mesh.gltf2_variant_default_materials = bpy.props.CollectionProperty(type=gltf2_KHR_materials_variants_default_material)
        bpy.types.Mesh.gltf2_variant_pointer = bpy.props.StringProperty()
        bpy.types.Scene.gltf2_KHR_materials_variants_variants = bpy.props.CollectionProperty(type=gltf2_KHR_materials_variants_variant)
        bpy.types.Scene.gltf2_active_variant = bpy.props.IntProperty()

def unregister():
    bpy.utils.unregister_class(SCENE_OT_gltf2_variant_add)
    bpy.utils.unregister_class(SCENE_OT_gltf2_material_to_variant)
    bpy.utils.unregister_class(SCENE_OT_gltf2_variant_slot_add)
    bpy.utils.unregister_class(SCENE_OT_gltf2_display_variant)
    bpy.utils.unregister_class(SCENE_OT_gltf2_assign_to_variant)
    bpy.utils.unregister_class(SCENE_OT_gltf2_reset_to_original)
    bpy.utils.unregister_class(SCENE_OT_gltf2_assign_as_original)
    bpy.utils.unregister_class(NODE_OT_GLTF_SETTINGS)
    bpy.utils.unregister_class(SCENE_PT_gltf2_variants)
    bpy.utils.unregister_class(SCENE_UL_gltf2_variants)
    bpy.utils.unregister_class(MESH_PT_gltf2_mesh_variants)
    bpy.utils.unregister_class(MESH_UL_gltf2_mesh_variants)
    bpy.utils.unregister_class(gltf2_KHR_materials_variants_default_material)
    bpy.utils.unregister_class(gltf2_KHR_materials_variants_primitive)
    bpy.utils.unregister_class(gltf2_KHR_materials_variants_variant)
    bpy.utils.unregister_class(gltf2_KHR_materials_variant_pointer)
