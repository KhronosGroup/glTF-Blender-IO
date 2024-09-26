Here you'll find information on how to add importer extensions from a glTF file from an external Blender addon.

First, your importer must define a class with this exact name:

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

If you want to use this file as a base of your addon, make sure to make it properly installable as Blender addon by either:

- Rename from `__init__.py` to another name
- Create a zip file of the directory that includes `__init__.py`

Next, define functions that contain the data of the extension you would like to include. Write those functions for each type you want to include extensions for. Currently implemented are:

```
gather_import_node_before_hook(self, vnode, gltf_node, gltf)
gather_import_node_after_hook(self, vnode, gltf_node, blender_object, gltf)
gather_import_scene_before_hook(self, gltf_scene, blender_scene, gltf)
gather_import_scene_after_nodes_hook(self, gltf_scene, blender_scene, gltf)
gather_import_scene_after_animation_hook(self, gltf_scene, blender_scene, gltf)
gather_import_material_before_hook(self, gltf_material, vertex_color, gltf)
gather_import_material_after_hook(self, gltf_material, vertex_color, blender_mat, gltf)
gather_import_light_before_hook(self, gltf_node, gltf_light, gltf)
gather_import_light_after_hook(self, gltf_node, blender_node, blender_light, gltf)
gather_import_mesh_before_hook(self, gltf_mesh, gltf)
gather_import_mesh_after_hook(self, gltf_mesh, blender_mesh, gltf)
gather_import_mesh_options(self, mesh_options, gltf_mesh, skin_idx, gltf)
gather_import_camera_before_hook(self, gltf_node, gltf_camera, gltf)
gather_import_camera_after_hook(self, gltf_node, blender_node, blender_camera, gltf)
gather_import_image_before_hook(self, gltf_img, gltf)
gather_import_image_after_hook(self, gltf_img, blender_image, gltf)
gather_import_texture_before_hook(self, gltf_texture, mh, tex_info, location, label, color_socket, alpha_socket, is_data, gltf)
gather_import_texture_after_hook(self, gltf_texture, node_tree, mh, tex_info, location, label, color_socket, alpha_socket, is_data, gltf)
gather_import_animations(self, gltf_animations, animation_options, gltf)
gather_import_animation_before_hook(self, anim_idx, gltf)
gather_import_animation_after_hook(self, anim_idx, track_name, gltf)
gather_import_animation_channel_before_hook(self, gltf_animation, gltf_node, path, channel, gltf)
gather_import_animation_channel_after_hook(self, gltf_animation, gltf_node, path, channel, blender_action, gltf)
gather_import_animation_weight_before_hook(self, gltf_node, blender_animation, gltf)
gather_import_animation_weight_after_hook(self, gltf_node, blender_animation, gltf)
gather_import_decode_primitive(self, gltf_mesh, gltf_primitive, skin_idx, gltf)
gather_import_gltf_before_hook(self, gltf)
```
