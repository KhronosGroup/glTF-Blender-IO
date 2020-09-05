Here you'll find information on how to add extensions to a glTF file from an external Blender addon.

Add a class named "gltf2ExportUserExtension" to your addon and instanciate an object of the class io_scene_gltf2.io.com.gltf2_io_extensions.Extension

class glTF2ExportUserExtension:

    def __init__(self):
        from io_scene_gltf2.io.com.gltf2_io_extensions import Extension
        self.Extension = Extension


Next, define functions that contain the data of the extension you would like to include. Write those functions for each type you want to include extensions for. Currently implemented are:

gather_node_hook(self, gltf2_object, blender_object, export_settings)
gather_material_hook(self, gltf2_material, blender_material, export_settings)
...





