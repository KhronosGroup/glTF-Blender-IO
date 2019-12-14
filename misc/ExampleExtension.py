import bpy

bl_info = {
    "name": "KDAB_example_extension",
    "category": "Generic",
    "blender": (2,80,0),
    'isDraft': False,
    'developer': "KDAB",
    'url': 'https://www.kdab.com',
}

class ExampleExtensionProperties(bpy.types.PropertyGroup):
    enabled: bpy.props.BoolProperty(
        name='ExampleExtension_enabled',
        description='This is an example of a BoolProperty used by a UserExtension.',
        default=True
        )
    float_property: bpy.props.FloatProperty(
        name='ExampleExtension_enabled',
        description='This is an example of a FloatProperty used by a UserExtension.',
        default=1.0
        )

def register():
    bpy.utils.register_class(ExampleExtensionProperties)
    bpy.types.Scene.ExampleExtensionProperties = bpy.props.PointerProperty(type=ExampleExtensionProperties)

def register_panel():
    # Register the panel on demand, we need to be sure to only register it once
    # This is necessary because the panel is a child of the extensions panel, 
    # which may not be registered when we try to register this extension
    try:
        bpy.utils.register_class(GLTF_PT_UserExtensionPanel)
    except Exception:
        pass

    # If the glTF exporter is disabled, we need to unregister the extension panel
    # Just return a function to the exporter so it can unregister the panel
    return unregister_panel


def unregister_panel():
    # Since panel is registered on demand, it is possible it is not registered
    try:
        bpy.utils.unregister_class(GLTF_PT_UserExtensionPanel)
    except Exception:
        pass
        

def unregister():
    unregister_panel()
    bpy.utils.unregister_class(ExampleExtensionProperties)
    del bpy.types.Scene.ExampleExtensionProperties

class GLTF_PT_UserExtensionPanel(bpy.types.Panel):

    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Example Extension"
    bl_parent_id = "GLTF_PT_export_user_extensions"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator
        return operator.bl_idname == "EXPORT_SCENE_OT_gltf"

    def draw_header(self, context):
        props = bpy.context.scene.ExampleExtensionProperties
        self.layout.prop(props, 'enabled')

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.


        box = layout.box()
        box.label(text="Is draft: " + str(bl_info['isDraft']))
        box.label(text="Developer: " + str(bl_info['developer']))
        box.label(text="url: " + str(bl_info['url']))

        props = bpy.context.scene.ExampleExtensionProperties
        layout.prop(props, 'float_property', text="Some float value")


class glTF2ExportUserExtension:

    def __init__(self):
        # We need to wait until we create the gltf2UserExtension to import the gltf2 modules
        # Otherwise, it may fail because the gltf2 may not be loaded yet
        from io_scene_gltf2.io.com.gltf2_io_extensions import Extension
        self.Extension = Extension 
        self.properties = bpy.context.scene.ExampleExtensionProperties

    def gather_node_hook(self, gltf2_object, blender_object, export_settings):
        if self.properties.enabled:
            if gltf2_object.extensions is None:
                gltf2_object.extensions = {}
            gltf2_object.extensions[bl_info['name']] = self.Extension(
                name= bl_info['name'], 
                extension={"float": self.properties.float_property},
                required=False
            )

