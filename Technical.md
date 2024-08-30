# Technical overview

## Importer

Here are the main step of the importer:

- Reading and parsing file (See *__init__.py* and *blender_gltf.py* files)
- Creating virtual tree and compute nodes (see *vnode.py* file)
- Then Blender objects are created, based on virtual tree nodes (see all *create* static methods of *blender/imp/gltf2_blender_* files)
- For animations, all gltf animations are created, but only the first one is then set as Blender active action.

### Adding a new material extension

If you want to add a new material extension, here are some steps you need to follow:

- Add the extension in list of managed extensions, in *extensions_managed* list of *glTFImporter* class
- If your extension need a node that is not Principled Shader node, add it, and correspondance links, in *make_output_nodes* function, in *pbrMetallicRoughness.py* file
- Add your newly created nodes for textures in *calc_locations* function, in order to have the nodes correcly displayed without overlapping
- Add you new function at end of *pbr_metallic_roughness* function. Create this function in a new file, on *blender/imp/* directory


## Exporter

Here are the main step of the exporter:

- A virtual node tree is created, then filtered (See *blender/exp/tree.py* file)
- Based on this tree, nodes are exported, with some cache, avoiding calculating multiple time the same things
- At end of process, json tabs are created, replacing references to nodes by index in tabs (See multiple *traverse* functions)

### Adding a new material extension

- In *materials.py/__gather_extensions*, add a function to manage your extension
- Create an *Extension* class to store your extension data.
  - Third parameter is used to set the extension required
  - If you need an extension at root of json, use ChildOfRootExtension instead
- If your texture is a simple mapping of channels:
  - Add your channel mapping in *__get_image_data_mapping* function
  - Example: *Clearcoat*
- If your texture needs a complex calculation:
  - Add a check in *__get_image_data* function to call your specific function
  - In your function, create an *ExportImage* class, setting a function as numpy calculation, calling the *set_calc* method
  - In this function, store needed data for calculation, by using *store_data* method
  - Create a new file in *blender/exp/*, storing your numpy calculation function. This function will use data stored in ExportImage class
  - Example: *Specular*
- If your extension manages some texture, make sure to manage active UVMaps checks in *materials.py/gather_material* function
