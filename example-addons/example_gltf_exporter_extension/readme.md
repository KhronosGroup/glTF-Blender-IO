Here you'll find information on how to add extensions to a glTF file from an external Blender addon.

Add a class named `gltf2ExportUserExtension` (must be this name) to your addon and instantiate an object of the class `io_scene_gltf2.io.com.gltf2_io_extensions.Extension`

```python
class glTF2ExportUserExtension:

    def __init__(self):
        from io_scene_gltf2.io.com.gltf2_io_extensions import Extension
        self.Extension = Extension
```

If you want to use this file as a base of your addon, make sure to make it properly installable as Blender addon by either:

- Rename from `__init__.py` to another name
- Create a zip file of the directory that includes `__init__.py`

Next, define functions that contain the data of the extension you would like to include. Write those functions for each type you want to include extensions for. Currently implemented are:

```
pre_export_hook(self, export_settings)
post_export_hook(self, export_settings)
gather_animation_channel_hook(self, gltf2_animation_channel, channel, blender_object, bone, action_name, node_channel_is_animated, export_settings)
gather_animation_channel_target_hook(self, gltf2_animation_channel_target, channels, blender_object, bake_bone, bake_channel, export_settings)
gather_animation_sampler_hook(self, gltf2_sampler, blender_object, bone, action_name, node_channel_is_animated, export_settings)
gather_asset_hook(self, gltf2_asset, export_settings)
gather_camera_hook(self, gltf2_camera, blender_camera, export_settings)
gather_gltf_extensions_hook(self, gltf2_plan, export_settings)
gather_image_hook(self, gltf2_image, blender_shader_sockets, export_settings)
gather_joint_hook(self, gltf2_node, blender_bone, export_settings)
gather_material_hook(self, gltf2_material, blender_material, export_settings)
gather_material_pbr_metallic_roughness_hook(self, gltf2_material, blender_material, orm_texture, export_settings)
gather_material_unlit_hook(self, gltf2_material, blender_material, export_settings)
gather_mesh_hook(self, gltf2_mesh, blender_mesh, blender_object, vertex_groups, modifiers, materials, export_settings)
gather_node_hook(self, gltf2_node, blender_object, export_settings)
gather_node_name_hook(self, gltf_name, blender_object, export_settings)
gather_sampler_hook(self, gltf2_sampler, blender_shader_node, export_settings)
gather_scene_hook(self, gltf2_scene, blender_scene, export_settings)
gather_skin_hook(self, gltf2_skin, blender_object, export_settings)
gather_texture_hook(self, gltf2_texture, blender_shader_sockets, export_settings)
gather_texture_info_hook(self, gltf2_texture_info, blender_shader_sockets, export_settings)
merge_animation_extensions_hook(self, gltf2_animation_source, gltf2_animation_destination, export_settings)
vtree_before_filter_hook(self, vtree, export_settings)
vtree_after_filter_hook(self, vtree, export_settings)
pre_gather_animation_hook(self, gltf2_channels, blender_action, slot_identifier, blender_object, export_settings)
gather_actions_hook(self, blender_object, actions, export_settings) # params = ActionsData
gather_tracks_hook(self, blender_object, tracks, export_settings) # params = TracksData, blender_tracks_names, track_on_type
pre_gather_actions_hook(self, blender_object, export_settings) # For action mode
pre_gather_tracks_hook(self, blender_object, export_settings) # For track mode
pre_animation_switch_hook(self, blender_object, blender_action, slot, track_name, on_type, export_settings) # For action mode
post_animation_switch_hook(self, blender_object, blender_action, slot, track_name, on_type, export_settings)  # For action mode
pre_animation_track_switch_hook(self, blender_object, tracks, track_name, on_type, export_settings) # For track mode
post_animation_track_switch_hook(self, blender_object, tracks, track_name, on_type, export_settings)  # For track mode
animation_switch_loop_hook(self, blender_object, post, export_settings) # post = False before loop, True after loop # for action mode
animation_track_switch_loop_hook(self, blender_object, post, export_settings) # post = False before loop, True after loop # for track mode
animation_gather_fcurve(self, blender_object, blender_action, export_settings)
animation_channels_object_sampled(self, gltf2_channels, blender_object, blender_action, slot_identifier, cache_key, export_settings)
animation_gather_object_channel(self, blender_object, blender_action_name, export_settings)
animation_gather_object_sampler(self, blender_object, action_name, export_settings)
animation_channels_sk_sampled(self, gltf2_channels, blender_object, blender_action, slot_identifier, cache_key, export_settings)
animation_action_sk_sampled_target(self, blender_object, export_settings)
animation_gather_sk_channels(self, blender_object, blender_action_name, export_settings)
animation_gather_sk_channel(self, blender_object, blender_action_name, export_settings)
animation_gather_fcurve_channel_target(self, blender_object, bone_name, export_settings)
animation_gather_fcurve_channel_sampler(self, blender_object, bone_name, export_settings)
animation_gather_fcurve_channel(self, blender_object, bone_name, channel_group, export_settings)
gather_gltf_hook(self, active_scene_idx, scenes, animations, export_settings)
gather_gltf_encoded_hook(self, gltf_format, sort_order, export_settings)
gather_tree_filter_tag_hook(self, tree, export_settings)
animation_channels_armature_sampled(self, gltf2_channels, blender_object, blender_action, slot_identifier, cache_key, export_settings)
gather_animation_bone_sampled_channel_target_hook(self, blender_object, bone, channel, export_settings)
gather_animation_object_sampled_channel_target_hook(self, blender_object, channel)
gather_attribute_keep(self, keep_attribute, export_settings)
gather_attribute_change(self, attribute, data, is_normalized_byte_color, export_settings)
gather_attributes_change(self, attributes, export_settings)
gather_gltf_additional_textures_hook(self, json, additioan_json_textures, export_settings)
gather_node_mesh_hook(self, option, blender_object, export_settings)
extra_animation_manage(self, extra_samplers, obj_uuid, blender_object, blender_action, gltf_channels, export_settings)
```
