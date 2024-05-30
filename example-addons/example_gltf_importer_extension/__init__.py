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
# See: https://github.com/KhronosGroup/glTF/tree/main/extensions#about-gltf-extensions
# also: https://github.com/KhronosGroup/glTF/blob/main/extensions/Prefixes.md
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




def draw(context, layout):
    header, body = layout.panel("GLTF_addon_example_importer", default_closed=False)

    props = bpy.context.scene.ExampleImporterExtensionProperties

    header.prop(props, 'enabled')
    body.active = props.enabled
    body.prop(props, 'float_property', text="Some float value")


class glTF2ImportUserExtension:

    def __init__(self):
        self.properties = bpy.context.scene.ExampleImporterExtensionProperties

    def gather_import_node_before_hook(self, vnode, gltf_node, gltf):
        if self.properties.enabled:
            pass

    def gather_import_node_after_hook(self, vnode, gltf_node, blender_object, gltf):
        if self.properties.enabled:
            pass

def register():
    bpy.utils.register_class(ExampleImporterExtensionProperties)
    bpy.types.Scene.ExampleImporterExtensionProperties = bpy.props.PointerProperty(type=ExampleImporterExtensionProperties)

def unregister():
    bpy.utils.unregister_class(ExampleImporterExtensionProperties)
    del bpy.types.Scene.ExampleImporterExtensionProperties
