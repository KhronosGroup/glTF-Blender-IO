# Copyright (c) 2017 The Khronos Group Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#
# Imports
#

import bpy

from ...io.com.gltf2_io_debug import *
from ...io.com import gltf2_io_image
from .gltf2_blender_get import get_image_material_usage_to_socket
from ..com.gltf2_blender_image import *

#
# Globals
#

#
# Functions
#

def filter_merge_image(export_settings, blender_image):
    metallic_channel = get_image_material_usage_to_socket(blender_image, "Metallic")
    roughness_channel = get_image_material_usage_to_socket(blender_image, "Roughness")

    if metallic_channel < 0 and roughness_channel < 0:
        return False
    
    if export_settings.get("metallic_roughness_image") is None:
        export_settings["metallic_roughness_image"] = gltf2_io_image.create_img(width=blender_image.image.size[0], height=blender_image.image.size[1], r=1.0, g=1.0, b=1.0, a=1.0)

    img = create_img_from_blender_image(blender_image.image)

    if metallic_channel >= 0:
        gltf2_io_image.copy_img_channel(dst_image=export_settings["metallic_roughness_image"], dst_channel=2, src_image=img, src_channel=metallic_channel)
        export_settings["metallic_roughness_image"].name = blender_image.image.name + export_settings["metallic_roughness_image"].name
    if roughness_channel >= 0:
        gltf2_io_image.copy_img_channel(dst_image=export_settings["metallic_roughness_image"], dst_channel=1, src_image=img, src_channel=roughness_channel)
        if metallic_channel < 0:
            export_settings["metallic_roughness_image"].name = export_settings["metallic_roughness_image"].name + blender_image.image.name
    return True


def filter_used_materials():
    """
    Gathers and returns all unfiltered, valid Blender materials.
    """

    materials = []

    for blender_material in bpy.data.materials:
        if blender_material.node_tree and blender_material.use_nodes:
            for currentNode in blender_material.node_tree.nodes:
                if isinstance(currentNode, bpy.types.ShaderNodeGroup):
                    if currentNode.node_tree.name.startswith('glTF Metallic Roughness'):
                        materials.append(blender_material)
                    elif currentNode.node_tree.name.startswith('glTF Specular Glossiness'):
                        materials.append(blender_material)
                elif isinstance(currentNode, bpy.types.ShaderNodeBsdfPrincipled):
                    materials.append(blender_material)
        else:
            materials.append(blender_material)

    return materials


def filter_apply(export_settings):
    """
    Gathers and filters the objects and assets to export.
    Also filters out invalid, deleted and not exportable elements.
    """
    filtered_objects = []
    implicit_filtered_objects = []

    for blender_object in bpy.data.objects:
        
        if blender_object.users == 0:
            continue
        
        if export_settings['gltf_selected'] and not blender_object.select:
            continue

        if not export_settings['gltf_layers'] and not blender_object.layers[0]:
            continue
        
        filtered_objects.append(blender_object)
        
        if export_settings['gltf_selected'] or not export_settings['gltf_layers']:
            current_parent = blender_object.parent
            while current_parent:
                if current_parent not in implicit_filtered_objects:
                    implicit_filtered_objects.append(current_parent)
                
                current_parent = current_parent.parent

    export_settings['filtered_objects'] = filtered_objects
    
    # Meshes
    
    filtered_meshes = {}
    filtered_vertex_groups = {}
    temporary_meshes = []
    
    for blender_mesh in bpy.data.meshes:
        
        if blender_mesh.users == 0:
            continue
        
        current_blender_mesh = blender_mesh
        
        current_blender_object = None
        
        skip = True
        
        for blender_object in filtered_objects:
            
            current_blender_object = blender_object
            
            if current_blender_object.type != 'MESH':
                continue
            
            if current_blender_object.data == current_blender_mesh:
                
                skip = False
                
                use_auto_smooth = current_blender_mesh.use_auto_smooth
                
                if use_auto_smooth:
                    
                    if current_blender_mesh.shape_keys is None: 
                        current_blender_object = current_blender_object.copy()
                    else:
                        use_auto_smooth = False
                        
                        print_console('WARNING', 'Auto smooth and shape keys cannot be exported in parallel. Falling back to non auto smooth.')
                
                if export_settings['gltf_apply'] or use_auto_smooth:
                    
                    if not export_settings['gltf_apply']:
                        current_blender_object.modifiers.clear()
                    
                    if use_auto_smooth:
                        blender_modifier = current_blender_object.modifiers.new('Temporary_Auto_Smooth', 'EDGE_SPLIT')
                    
                        blender_modifier.split_angle = current_blender_mesh.auto_smooth_angle
                        blender_modifier.use_edge_angle = current_blender_mesh.has_custom_normals == False

                    current_blender_mesh = current_blender_object.to_mesh(bpy.context.scene, True, 'PREVIEW')
                    temporary_meshes.append(current_blender_mesh)
                
                break
        
        if skip:
            continue
            
        filtered_meshes[blender_mesh.name] = current_blender_mesh
        filtered_vertex_groups[blender_mesh.name] = current_blender_object.vertex_groups
        
    # Curves
    
    for blender_curve in bpy.data.curves:
        
        if blender_curve.users == 0:
            continue
        
        current_blender_curve = blender_curve

        current_blender_mesh = None
    
        current_blender_object = None
        
        skip = True
        
        for blender_object in filtered_objects:
            
            current_blender_object = blender_object
            
            if current_blender_object.type != 'CURVE':
                continue
            
            if current_blender_object.data == current_blender_curve:

                skip = False
                
                current_blender_object = current_blender_object.copy()
                
                if not export_settings['gltf_apply']:
                    current_blender_object.modifiers.clear()
                
                current_blender_mesh = current_blender_object.to_mesh(bpy.context.scene, True, 'PREVIEW')
                temporary_meshes.append(current_blender_mesh)
                
                break
        
        if skip:
            continue
            
        filtered_meshes[blender_curve.name] = current_blender_mesh
        filtered_vertex_groups[blender_curve.name] = current_blender_object.vertex_groups
    
    # 
            
    export_settings['filtered_meshes'] = filtered_meshes
    export_settings['filtered_vertex_groups'] = filtered_vertex_groups
    export_settings['temporary_meshes'] = temporary_meshes
    
    #

    filtered_materials = []

    for blender_material in filter_used_materials():
        
        if blender_material.users == 0:
            continue
        
        for mesh_name, blender_mesh in filtered_meshes.items():
            for compare_blender_material in blender_mesh.materials:
                if compare_blender_material == blender_material and blender_material not in filtered_materials:
                    filtered_materials.append(blender_material)
        
        #

        for blender_object in filtered_objects:
            if blender_object.material_slots:
                for blender_material_slot in blender_object.material_slots:
                    if blender_material_slot.link == 'DATA':
                        continue
                    
                    if blender_material_slot.material not in filtered_materials:
                        filtered_materials.append(blender_material_slot.material)
                    
    export_settings['filtered_materials'] = filtered_materials                

    #

    filtered_textures = []
    filtered_merged_textures = []
    
    temp_filtered_texture_names = []

    for blender_material in filtered_materials:
        if blender_material.node_tree and blender_material.use_nodes:
            
            per_material_textures = []
            
            for blender_node in blender_material.node_tree.nodes:
                
                if isinstance(blender_node, bpy.types.ShaderNodeTexImage) and blender_node.image is not None and blender_node.image.users != 0 and blender_node.image.size[0] > 0 and blender_node.image.size[1] > 0 and blender_node not in filtered_textures:
                    add_node = False
                    add_merged_node = False
                    for blender_socket in blender_node.outputs:
                        if blender_socket.is_linked:
                            for blender_link in blender_socket.links:
                                if isinstance(blender_link.to_node, bpy.types.ShaderNodeGroup):
                                    if blender_link.to_node.node_tree.name.startswith('glTF Metallic Roughness') or blender_link.to_node.node_tree.name.startswith('glTF Specular Glossiness'):
                                        add_node = True
                                        break
                                elif isinstance(blender_link.to_node, bpy.types.ShaderNodeBsdfPrincipled):
                                    add_node = True
                                    break
                                elif isinstance(blender_link.to_node, bpy.types.ShaderNodeNormalMap):
                                    add_node = True
                                    break
                                elif isinstance(blender_link.to_node, bpy.types.ShaderNodeSeparateRGB):
                                    add_merged_node = True
                                    break
                                    
                        if add_node or add_merged_node:
                            break
                        
                    if add_node:
                        filtered_textures.append(blender_node)
                        # TODO: Add displacement texture, as not stored in node tree.
                        
                    if add_merged_node:
                        if len(per_material_textures) == 0:
                            filtered_merged_textures.append(per_material_textures) 
                        
                        per_material_textures.append(blender_node)
                        
        else:

                for blender_texture_slot in blender_material.texture_slots:

                    if blender_texture_slot is not None and blender_texture_slot.texture and blender_texture_slot.texture.users != 0 and blender_texture_slot.texture.type == 'IMAGE' and blender_texture_slot.texture.image is not None and blender_texture_slot.texture.image.users != 0 and blender_texture_slot.texture.image.size[0] > 0 and  blender_texture_slot.texture.image.size[1] > 0:
                        if blender_texture_slot not in filtered_textures and blender_texture_slot.name not in temp_filtered_texture_names:
                            accept = False
                            
                            if blender_texture_slot.use_map_color_diffuse:
                                accept = True
                                
                            if blender_texture_slot.use_map_ambient:
                                accept = True
                            if blender_texture_slot.use_map_emit:
                                accept = True
                            if blender_texture_slot.use_map_normal:
                                accept = True

                            if export_settings['gltf_displacement']:
                                if blender_texture_slot.use_map_displacement:
                                    accept = True

                            if accept:
                                filtered_textures.append(blender_texture_slot)
                                temp_filtered_texture_names.append(blender_texture_slot.name)
 
    export_settings['filtered_textures'] = filtered_textures                

    #

    filtered_images = []
    filtered_merged_images = []
    filtered_images_use_alpha = {}

    for blender_texture in filtered_textures:
        
        if isinstance(blender_texture, bpy.types.ShaderNodeTexImage):
            if blender_texture.image is not None and blender_texture.image not in filtered_images and blender_texture.image.users != 0 and blender_texture.image.size[0] > 0 and blender_texture.image.size[1] > 0:
                filtered_images.append(blender_texture.image)
                alpha_socket = blender_texture.outputs.get('Alpha')
                if alpha_socket is not None and alpha_socket.is_linked:
                    filtered_images_use_alpha[blender_texture.image.name] = True

        else:
            if blender_texture.texture.image is not None and blender_texture.texture.image not in filtered_images and blender_texture.texture.image.users != 0 and blender_texture.texture.image.size[0] > 0 and blender_texture.texture.image.size[1] > 0:
                filtered_images.append(blender_texture.texture.image)
                if blender_texture.use_map_alpha:
                    filtered_images_use_alpha[blender_texture.texture.image.name] = True

    #

    for per_material_textures in filtered_merged_textures:
        
        export_settings["metallic_roughness_image"] = None
            
        for blender_texture in per_material_textures:
            
            if isinstance(blender_texture, bpy.types.ShaderNodeTexImage):
                if blender_texture.image is not None and blender_texture.image not in filtered_images and blender_texture.image.users != 0 and blender_texture.image.size[0] > 0 and blender_texture.image.size[1] > 0:
                    filter_merge_image(export_settings, blender_texture)

        img = export_settings.get("metallic_roughness_image")          
        if img is not None:
            filtered_merged_images.append(img)
            export_settings['filtered_textures'].append(img)

    export_settings['filtered_merged_images'] = filtered_merged_images
    export_settings['filtered_images'] = filtered_images
    export_settings['filtered_images_use_alpha'] = filtered_images_use_alpha
    
    #
    #
    
    filtered_cameras = []
    
    for blender_camera in bpy.data.cameras:
        
        if blender_camera.users == 0:
            continue
        
        if export_settings['gltf_selected']:
            if blender_camera not in filtered_objects:
                continue 
        
        filtered_cameras.append(blender_camera)

    export_settings['filtered_cameras'] = filtered_cameras

    #
    #
    
    filtered_lights = []
    
    for blender_light in bpy.data.lamps:
        
        if blender_light.users == 0:
            continue

        if export_settings['gltf_selected']:
            if blender_light not in filtered_objects:
                continue 

        if blender_light.type == 'HEMI':
            continue

        filtered_lights.append(blender_light)
                
    export_settings['filtered_lights'] = filtered_lights
    
    #
    #
    
    for implicit_object in implicit_filtered_objects:
        if implicit_object not in filtered_objects:
            filtered_objects.append(implicit_object)

    #
    #
    #
    
    group_index = {}
    
    if export_settings['gltf_skins']:
        for blender_object in filtered_objects:
            if blender_object.type != 'ARMATURE' or len(blender_object.pose.bones) == 0:
                continue
            for blender_bone in blender_object.pose.bones:
                group_index[blender_bone.name] = len(group_index)

    export_settings['group_index'] = group_index
