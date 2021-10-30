Here you'll find information on how to add extensions to a glTF file from an external Blender addon.

Add a class named `gltf2ExportUserExtension` to your addon and instantiate an object of the class `io_scene_gltf2.io.com.gltf2_io_extensions.Extension`

```python
class glTF2ExportUserExtension:

    def __init__(self):
        from io_scene_gltf2.io.com.gltf2_io_extensions import Extension
        self.Extension = Extension
```

Next, define functions that contain the data of the extension you would like to include. Write those functions for each type you want to include extensions for. Currently implemented are:

```
gather_animation_hook(self, gltf2_animation, blender_action, blender_object, export_settings)
gather_animation_channel_hook(self, gltf2_animation_channel, channels, blender_object, bake_bone, bake_channel, bake_range_start, bake_range_end, action_name, export_settings)
gather_animation_channel_target_hook(self, gltf2_animation_channel_target, channels, blender_object, bake_bone, bake_channel, export_settings)
gather_animation_sampler_hook(self, gltf2_sampler, channels, blender_object, bake_bone, bake_channel, bake_range_start, bake_range_end, action_name, export_settings)
gather_asset_hook(self, gltf2_asset, export_settings)
gather_camera_hook(self, gltf2_camera, blender_camera, export_settings)
gather_gltf_hook(self, gltf2_plan, export_settings)
gather_image_hook(self, gltf2_image, blender_shader_sockets, export_settings)
gather_joint_hook(self, gltf2_node, blender_bone, export_settings)
gather_material_hook(self, gltf2_material, blender_material, export_settings)
gather_material_pbr_metallic_roughness_hook(self, gltf2_material, blender_material, orm_texture, export_settings)
gather_material_unlit_hook(self, gltf2_material, blender_material, export_settings)
gather_mesh_hook(self, gltf2_mesh, blender_mesh, blender_object, vertex_groups, modifiers, skip_filter, material_names, export_settings)
gather_node_hook(self, gltf2_node, blender_object, export_settings)
gather_sampler_hook(self, gltf2_sampler, blender_shader_node, export_settings)
gather_scene_hook(self, gltf2_scene, blender_scene, export_settings)
gather_skin_hook(self, gltf2_skin, blender_object, export_settings)
gather_texture_hook(self, gltf2_texture, blender_shader_sockets, export_settings)
gather_texture_info_hook(self, gltf2_texture_info, blender_shader_sockets, export_settings)
merge_animation_extensions_hook(self, gltf2_animation_source, gltf2_animation_destination, export_settings)
```
