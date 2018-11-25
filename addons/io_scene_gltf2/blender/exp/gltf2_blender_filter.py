# Copyright 2018 The glTF-Blender-IO authors.
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
from . import gltf2_blender_export_keys
from . import gltf2_blender_get
from ...io.com.gltf2_io_debug import print_console
from ..com.gltf2_blender_image import create_img_from_blender_image
from ...io.com import gltf2_io_image

#
# Globals
#

PREVIEW = 'PREVIEW'
GLOSSINESS = 'glTF Specular Glossiness'
ROUGHNESS = 'glTF Metallic Roughness'


#
# Functions
#

def filter_merge_image(export_settings, blender_image):
    metallic_channel = gltf2_blender_get.get_image_material_usage_to_socket(blender_image, "Metallic")
    roughness_channel = gltf2_blender_get.get_image_material_usage_to_socket(blender_image, "Roughness")

    if metallic_channel < 0 and roughness_channel < 0:
        return False

    output = export_settings[gltf2_blender_export_keys.METALLIC_ROUGHNESS_IMAGE]
    if export_settings.get(export_keys.METALLIC_ROUGHNESS_IMAGE) is None:
        width = blender_image.image.size[0]
        height = blender_image.image.size[1]
        output = gltf2_io_image.create_img(width, height, r=1.0, g=1.0, b=1.0, a=1.0)

    source = create_img_from_blender_image(blender_image.image)

    if metallic_channel >= 0:
        gltf2_io_image.copy_img_channel(output, dst_channel=2, src_image=source, src_channel=metallic_channel)
        output.name = blender_image.image.name + output.name
    if roughness_channel >= 0:
        gltf2_io_image.copy_img_channel(output, dst_channel=1, src_image=source, src_channel=roughness_channel)
        if metallic_channel < 0:
            output.name = output.name + blender_image.image.name
    return True


def filter_used_materials():
    """Gather and return all unfiltered, valid Blender materials."""
    materials = []

    for blender_material in bpy.data.materials:
        if blender_material.node_tree and blender_material.use_nodes:
            for currentNode in blender_material.node_tree.nodes:
                if isinstance(currentNode, bpy.types.ShaderNodeGroup):
                    if currentNode.node_tree.name.startswith(ROUGHNESS):
                        materials.append(blender_material)
                    elif currentNode.node_tree.name.startswith(GLOSSINESS):
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

        if bpy.app.version < (2, 80, 0):
            if export_settings[gltf2_blender_export_keys.SELECTED] and not blender_object.select:
                continue
        else:
            if export_settings[gltf2_blender_export_keys.SELECTED] and blender_object.select_get() is False:
                continue

        if not export_settings[gltf2_blender_export_keys.LAYERS] and not blender_object.layers[0]:
            continue

        filtered_objects.append(blender_object)

        if export_settings[gltf2_blender_export_keys.SELECTED] or not export_settings[gltf2_blender_export_keys.LAYERS]:
            current_parent = blender_object.parent
            while current_parent:
                if current_parent not in implicit_filtered_objects:
                    implicit_filtered_objects.append(current_parent)

                current_parent = current_parent.parent

    export_settings[gltf2_blender_export_keys.FILTERED_OBJECTS] = filtered_objects

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

                        print_console('WARNING',
                                      'Auto smooth and shape keys cannot be exported in parallel. '
                                      'Falling back to non auto smooth.')

                if export_settings[gltf2_blender_export_keys.APPLY] or use_auto_smooth:
                    # TODO: maybe add to new exporter
                    if not export_settings[gltf2_blender_export_keys.APPLY]:
                        current_blender_object.modifiers.clear()

                    if use_auto_smooth:
                        blender_modifier = current_blender_object.modifiers.new('Temporary_Auto_Smooth', 'EDGE_SPLIT')

                        blender_modifier.split_angle = current_blender_mesh.auto_smooth_angle
                        blender_modifier.use_edge_angle = not current_blender_mesh.has_custom_normals

                    current_blender_mesh = current_blender_object.to_mesh(bpy.context.scene, True, PREVIEW)
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

            if current_blender_object.type not in ('CURVE', 'FONT'):
                continue

            if current_blender_object.data == current_blender_curve:

                skip = False

                current_blender_object = current_blender_object.copy()

                if not export_settings[gltf2_blender_export_keys.APPLY]:
                    current_blender_object.modifiers.clear()

                current_blender_mesh = current_blender_object.to_mesh(bpy.context.scene, True, PREVIEW)
                temporary_meshes.append(current_blender_mesh)

                break

        if skip:
            continue

        filtered_meshes[blender_curve.name] = current_blender_mesh
        filtered_vertex_groups[blender_curve.name] = current_blender_object.vertex_groups

    #

    export_settings[gltf2_blender_export_keys.FILTERED_MESHES] = filtered_meshes
    export_settings[gltf2_blender_export_keys.FILTERED_VERTEX_GROUPS] = filtered_vertex_groups
    export_settings[gltf2_blender_export_keys.TEMPORARY_MESHES] = temporary_meshes

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

    export_settings[gltf2_blender_export_keys.FILTERED_MATERIALS] = filtered_materials

    #

    filtered_textures = []
    filtered_merged_textures = []

    temp_filtered_texture_names = []

    for blender_material in filtered_materials:
        if blender_material.node_tree and blender_material.use_nodes:

            per_material_textures = []

            for blender_node in blender_material.node_tree.nodes:

                if is_valid_node(blender_node) and blender_node not in filtered_textures:
                    add_node = False
                    add_merged_node = False
                    for blender_socket in blender_node.outputs:
                        if blender_socket.is_linked:
                            for blender_link in blender_socket.links:
                                if isinstance(blender_link.to_node, bpy.types.ShaderNodeGroup):
                                    is_roughness = blender_link.to_node.node_tree.name.startswith(ROUGHNESS)
                                    is_glossiness = blender_link.to_node.node_tree.name.startswith(GLOSSINESS)
                                    if is_roughness or is_glossiness:
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

                if is_valid_texture_slot(blender_texture_slot) and \
                        blender_texture_slot not in filtered_textures and \
                        blender_texture_slot.name not in temp_filtered_texture_names:
                    accept = False

                    if blender_texture_slot.use_map_color_diffuse:
                        accept = True

                    if blender_texture_slot.use_map_ambient:
                        accept = True
                    if blender_texture_slot.use_map_emit:
                        accept = True
                    if blender_texture_slot.use_map_normal:
                        accept = True

                    if export_settings[gltf2_blender_export_keys.DISPLACEMENT]:
                        if blender_texture_slot.use_map_displacement:
                            accept = True

                    if accept:
                        filtered_textures.append(blender_texture_slot)
                        temp_filtered_texture_names.append(blender_texture_slot.name)

    export_settings[gltf2_blender_export_keys.FILTERED_TEXTURES] = filtered_textures

    #

    filtered_images = []
    filtered_merged_images = []
    filtered_images_use_alpha = {}

    for blender_texture in filtered_textures:

        if isinstance(blender_texture, bpy.types.ShaderNodeTexImage):
            if is_valid_image(blender_texture.image) and blender_texture.image not in filtered_images:
                filtered_images.append(blender_texture.image)
                alpha_socket = blender_texture.outputs.get('Alpha')
                if alpha_socket is not None and alpha_socket.is_linked:
                    filtered_images_use_alpha[blender_texture.image.name] = True

        else:
            if is_valid_image(blender_texture.texture.image) and blender_texture.texture.image not in filtered_images:
                filtered_images.append(blender_texture.texture.image)
                if blender_texture.use_map_alpha:
                    filtered_images_use_alpha[blender_texture.texture.image.name] = True

    #

    for per_material_textures in filtered_merged_textures:

        export_settings[gltf2_blender_export_keys.METALLIC_ROUGHNESS_IMAGE] = None

        for blender_texture in per_material_textures:

            if isinstance(blender_texture, bpy.types.ShaderNodeTexImage):
                if is_valid_image(blender_texture.image) and blender_texture.image not in filtered_images:
                    filter_merge_image(export_settings, blender_texture)

        img = export_settings.get(export_keys.METALLIC_ROUGHNESS_IMAGE)
        if img is not None:
            filtered_merged_images.append(img)
            export_settings[gltf2_blender_export_keys.FILTERED_TEXTURES].append(img)

    export_settings[gltf2_blender_export_keys.FILTERED_MERGED_IMAGES] = filtered_merged_images
    export_settings[gltf2_blender_export_keys.FILTERED_IMAGES] = filtered_images
    export_settings[gltf2_blender_export_keys.FILTERED_IMAGES_USE_ALPHA] = filtered_images_use_alpha

    #

    filtered_cameras = []

    for blender_camera in bpy.data.cameras:

        if blender_camera.users == 0:
            continue

        if export_settings[gltf2_blender_export_keys.SELECTED]:
            if blender_camera not in filtered_objects:
                continue

        filtered_cameras.append(blender_camera)

    export_settings[gltf2_blender_export_keys.FILTERED_CAMERAS] = filtered_cameras

    #
    #

    filtered_lights = []

    for blender_light in bpy.data.lamps:

        if blender_light.users == 0:
            continue

        if export_settings[gltf2_blender_export_keys.SELECTED]:
            if blender_light not in filtered_objects:
                continue

        if blender_light.type == 'HEMI':
            continue

        filtered_lights.append(blender_light)

    export_settings[gltf2_blender_export_keys.FILTERED_LIGHTS] = filtered_lights

    #
    #

    for implicit_object in implicit_filtered_objects:
        if implicit_object not in filtered_objects:
            filtered_objects.append(implicit_object)

    #
    #
    #

    group_index = {}

    if export_settings[gltf2_blender_export_keys.SKINS]:
        for blender_object in filtered_objects:
            if blender_object.type != 'ARMATURE' or len(blender_object.pose.bones) == 0:
                continue
            for blender_bone in blender_object.pose.bones:
                group_index[blender_bone.name] = len(group_index)

    export_settings[gltf2_blender_export_keys.GROUP_INDEX] = group_index


def is_valid_node(blender_node):
    return isinstance(blender_node, bpy.types.ShaderNodeTexImage) and is_valid_image(blender_node.image)


def is_valid_image(image):
    return image is not None and \
        image.users != 0 and \
        image.size[0] > 0 and \
        image.size[1] > 0


def is_valid_texture_slot(blender_texture_slot):
    return blender_texture_slot is not None and \
        blender_texture_slot.texture and \
        blender_texture_slot.texture.users != 0 and \
        blender_texture_slot.texture.type == 'IMAGE' and \
        blender_texture_slot.texture.image is not None and \
        blender_texture_slot.texture.image.users != 0 and \
        blender_texture_slot.texture.image.size[0] > 0 and \
        blender_texture_slot.texture.image.size[1] > 0
