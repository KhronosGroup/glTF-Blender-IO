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
    # Register the properties
    bpy.utils.register_class(ExampleExtensionProperties)

    # If you plan to use the Scene Exporter (File => Export => glTF 2.0), you probably want to register the properties to the scene
    bpy.types.Scene.ExampleExtensionProperties = bpy.props.PointerProperty(type=ExampleExtensionProperties)

    # If you plan to use Collection Exporters, you may want to register the properties to the collection, instead of the scene
    # bpy.types.Collection.ExampleExtensionProperties = bpy.props.PointerProperty(type=ExampleExtensionProperties)

    # Use the following 2 lines to register the UI for this hook
    from io_scene_gltf2 import exporter_extension_layout_draw
    exporter_extension_layout_draw['Example glTF Extension'] = draw_export # Make sure to use the same name in unregister()

def unregister():
    # Unregister the properties
    bpy.utils.unregister_class(ExampleExtensionProperties)
    del bpy.types.Scene.ExampleExtensionProperties

    # If you registered the properties to the collection, you should unregister them here
    # del bpy.types.Collection.ExampleExtensionProperties

    # Use the following 2 lines to unregister the UI for this hook
    from io_scene_gltf2 import exporter_extension_layout_draw
    del exporter_extension_layout_draw['Example glTF Extension'] # Make sure to use the same name in register()


def draw_export(context, layout):

    # Note: If you are using Collection Exporter, you may want to restrict UI for some collections
    # You can access the collection like this: context.collection
    # So you can check if you want to show the UI for this collection or not, using
    # if context.collection.name != "Coll":
    #     return


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
        self.is_critical = True

    def gather_node_hook(self, gltf2_object, blender_object, export_settings):

        # Note: If you are using Collection Exporters, you may want to restrict the export for some collections
        # You can access the collection like this: export_settings['gltf_collection']
        # So you can check if you want to use this hook for this collection or not, using
        # if export_settings['gltf_collection'] != "Coll":
        #     return

        if self.properties.enabled:
            if gltf2_object.extensions is None:
                gltf2_object.extensions = {}
            gltf2_object.extensions[glTF_extension_name] = self.Extension(
                name=glTF_extension_name,
                extension={"float": self.properties.float_property},
                required=extension_is_required
            )

def glTF2_pre_export_callback(export_settings):
    print("This will be called before exporting the glTF file.")

def glTF2_post_export_callback(export_settings):
    print("This will be called after exporting the glTF file.")
