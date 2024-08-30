import bpy

bl_info = {
    "name": "Example glTF Extension",
    "category": "Generic",
    "version": (1, 0, 0),
    "blender": (2, 80, 0),
    'location': 'File > Export > glTF 2.0',
    'description': 'Example addon to add a custom extension to an exported glTF file.',
    'tracker_url': "https://github.com/KhronosGroup/glTF-Blender-IO/issues/",  # Replace with your issue tracker
    'isDraft': False,
    'developer': "(Your name here)", # Replace this
    'url': 'https://your_url_here',  # Replace this
}

# glTF extensions are named following a convention with known prefixes.
# See: https://github.com/KhronosGroup/glTF/tree/main/extensions#about-gltf-extensions
# also: https://github.com/KhronosGroup/glTF/blob/main/extensions/Prefixes.md
glTF_extension_name = "EXT_example_extension"

# Support for an extension is "required" if a typical glTF viewer cannot be expected
# to load a given model without understanding the contents of the extension.
# For example, a compression scheme or new image format (with no fallback included)
# would be "required", but physics metadata or app-specific settings could be optional.
extension_is_required = False

class ExampleExtensionProperties(bpy.types.PropertyGroup):
    enabled: bpy.props.BoolProperty(
        name=bl_info["name"],
        description='Include this extension in the exported glTF file.',
        default=True
        )
    float_property: bpy.props.FloatProperty(
        name='Sample FloatProperty',
        description='This is an example of a FloatProperty used by a UserExtension.',
        default=1.0
        )

def register():
    bpy.utils.register_class(ExampleExtensionProperties)
    bpy.types.Scene.ExampleExtensionProperties = bpy.props.PointerProperty(type=ExampleExtensionProperties)

def unregister():
    bpy.utils.unregister_class(ExampleExtensionProperties)
    del bpy.types.Scene.ExampleExtensionProperties


def draw(context, layout):
    header, body = layout.panel("GLTF_addon_example_exporter", default_closed=False)
    header.use_property_split = False

    props = bpy.context.scene.ExampleExtensionProperties

    header.prop(props, 'enabled')
    if body != None:
        body.prop(props, 'float_property', text="Some float value")


# Note: the class must have this exact name
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
            gltf2_object.extensions[glTF_extension_name] = self.Extension(
                name=glTF_extension_name,
                extension={"float": self.properties.float_property},
                required=extension_is_required
            )
