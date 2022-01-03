import bpy
from io_scene_gltf2.io.com.gltf2_io_extensions import Extension

bl_info = {
    "name": "Example glTF Importer Extension",
    "category": "Generic",
    "version": (1, 0, 0),
    "blender": (2, 80, 0),
    'location': 'File > Import > glTF 2.0',
    'description': 'Example addon to add a custom feature to an imported glTF file.',
    'tracker_url': "https://github.com/KhronosGroup/glTF-Blender-IO/issues/",  # Replace with your issue tracker
    'isDraft': False,
    'developer': "(Your name here)", # Replace this
    'url': 'https://your_url_here',  # Replace this
}

# glTF extensions are named following a convention with known prefixes.
# See: https://github.com/KhronosGroup/glTF/tree/master/extensions#about-gltf-extensions
# also: https://github.com/KhronosGroup/glTF/blob/master/extensions/Prefixes.md
glTF_extension_name = "EXT_example_extension"

class ExampleImporterExtensionProperties(bpy.types.PropertyGroup):
    enabled: bpy.props.BoolProperty(
        name=bl_info["name"],
        description='Run this extension while importing glTF file.',
        default=True
        )
    float_property: bpy.props.FloatProperty(
        name='Sample FloatProperty',
        description='This is an example of a FloatProperty used by a UserExtension.',
        default=1.0
        )


class GLTF_PT_UserExtensionPanel(bpy.types.Panel):

    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Enabled"
    bl_parent_id = "GLTF_PT_import_user_extensions"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator
        return operator.bl_idname == "IMPORT_SCENE_OT_gltf"

    def draw_header(self, context):
        props = bpy.context.scene.ExampleExtensionProperties
        self.layout.prop(props, 'enabled')

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        props = bpy.context.scene.ExampleExtensionProperties
        layout.active = props.enabled

        box = layout.box()
        box.label(text=glTF_extension_name)

        layout.prop(props, 'float_property', text="Some float value")


class glTF2ImportUserExtension:

    def __init__(self):
        self.properties = bpy.context.scene.ExampleImporterExtensionProperties
        self.extensions = [Extension(name="TEST_extension1", extension={}, required=True), Extension(name="TEST_extension2", extension={}, required=False)]

    def gather_import_node_before_hook(self, vnode, gltf_node):
        if self.properties.enabled:
            pass

    def gather_import_node_after_hook(self, vnode, gltf_node, blender_object):
        if self.properties.enabled:
            pass

def register():
    bpy.utils.register_class(ExampleImporterExtensionProperties)
    bpy.types.Scene.ExampleImporterExtensionProperties = bpy.props.PointerProperty(type=ExampleImporterExtensionProperties)

def unregister():
    unregister_panel()
    bpy.utils.unregister_class(ExampleImporterExtensionProperties)
    del bpy.types.Scene.ExampleImporterExtensionProperties


def register_panel():
    # Register the panel on demand, we need to be sure to only register it once
    # This is necessary because the panel is a child of the extensions panel,
    # which may not be registered when we try to register this extension
    try:
        bpy.utils.register_class(GLTF_PT_UserExtensionPanel)
    except Exception:
        pass

    # If the glTF importer is disabled, we need to unregister the extension panel
    # Just return a function to the importer so it can unregister the panel
    return unregister_panel


def unregister_panel():
    # Since panel is registered on demand, it is possible it is not registered
    try:
        bpy.utils.unregister_class(GLTF_PT_UserExtensionPanel)
    except Exception:
        pass