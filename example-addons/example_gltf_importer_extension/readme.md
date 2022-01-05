Here you'll find information on how to add importer extensions from a glTF file from an external Blender addon.


```python
class glTF2ImportUserExtension:

    def __init__(self):
        pass
```

If your importer extension supports custom glTF extensions, add them in the `__init__` by doing the following:

```python
    def __init__(self):
        self.extensions = [Extension(name="TEST_extension1", extension={}, required=True), Extension(name="TEST_extension2", extension={}, required=False)]
```

Next, define functions that contain the data of the extension you would like to include. Write those functions for each type you want to include extensions for. Currently implemented are:

```
gather_import_node_before_hook(self, vnode, gltf_node, import_extensions)
gather_import_node_after_hook(self, vnode, gltf_node, blender_object, import_extensions)
gather_import_scene_before_hook(self, gltf_scene, blender_scene, import_extensions)
gather_import_scene_after_nodes_hook(self, gltf_scene, blender_scene, import_extensions)
gather_import_scene_after_animation_hook(self, gltf_scene, blender_scene, import_extensions)
gather_import_material_before_hook(self, gltf_material, vertex_color, import_extensions)
gather_import_material_after_hook(self, gltf_material, vertex_color, blender_mat, import_extensions)
gather_import_light_before_hook(self, gltf_light, import_extensions)
gather_import_light_after_hook(self, gltf_light, blender_light, import_extensions)
gather_import_mesh_before_hook(self, gltf_mesh, import_extensions)
gather_import_mesh_after_hook(self, gltf_mesh, blender_mesh, import_extensions)
gather_import_camera_before_hook(self, gltf_camera, import_extensions)
gather_import_camera_after_hook(self, gltf_camera, blender_camera, import_extensions)
gather_import_image_before_hook(self, gltf_img, import_extensions)
gather_import_image_after_hook(self, gltf_img, blender_image, import_extensions)
gather_import_texture_before_hook(self, gltf_texture, mh, tex_info, location, label, color_socket, alpha_socket, is_data, import_extensions)
gather_import_texture_after_hook(self, gltf_texture, node_tree, mh, tex_info, location, label, color_socket, alpha_socket, is_data, import_extensions)
gather_import_animation_channel_before_hook(self, gltf_animation, gltf_node, path, channel, import_extensions)
gather_import_animation_channel_after_hook(self, gltf_animation, gltf_node, path, channel, blender_action, import_extensions)
gather_import_animation_weight_before_hook(self, gltf_node, blender_animation, import_extensions)
gather_import_animation_weight_after_hook(self, gltf_node, blender_animation, import_extensions)
```
