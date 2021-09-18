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
```
