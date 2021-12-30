Here you'll find information on how to add importer extensions from a glTF file from an external Blender addon.


```python
class glTF2ImportUserExtension:

    def __init__(self):
        pass
```

Next, define functions that contain the data of the extension you would like to include. Write those functions for each type you want to include extensions for. Currently implemented are:

```
gather_import_node_before_hook(self, vnode, gltf_node)
gather_import_node_after_hook(self, vnode, gltf_node, blender_object)
gather_import_scene_before_hook(self, gltf_scene, blender_scene)
gather_import_scene_after_nodes_hook(self, gltf_scene, blender_scene)
gather_import_scene_after_animation_hook(self, gltf_scene, blender_scene)
gather_import_material_before_hook(self, gltf, pymaterial, material_idx, vertex_color)
gather_import_material_after_hook(self, gltf, pymaterial, material_idx, vertex_color, blender_mat)
gather_import_light_before_hook(self, gltf, pylight, light_id)
gather_import_light_after_hook(self, gltf, pylight, light_id, blender_light)
gather_import_mesh_before_hook(self, gltf, pymesh, mesh_idx, skin_idx)
gather_import_mesh_after_hook(self, gltf, pymesh, mesh_idx, skin_idx, blender_mesh)
```
