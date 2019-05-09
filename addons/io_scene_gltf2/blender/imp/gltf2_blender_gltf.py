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

import bpy
from .gltf2_blender_scene import BlenderScene
from ...io.com.gltf2_io_trs import TRS


class BlenderGlTF():
    """Main glTF import class."""
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("%s should not be instantiated" % cls)

    @staticmethod
    def create(gltf):
        """Create glTF main method."""
        if bpy.app.version < (2, 80, 0):
            bpy.context.scene.render.engine = 'CYCLES'
        else:
            if bpy.context.scene.render.engine not in ['CYCLES', 'BLENDER_EEVEE']:
                bpy.context.scene.render.engine = 'BLENDER_EEVEE'
        BlenderGlTF.pre_compute(gltf)

        gltf.display_current_node = 0
        if gltf.data.nodes is not None:
            gltf.display_total_nodes = len(gltf.data.nodes)
        else:
            gltf.display_total_nodes = "?"

        active_object_name_at_end = None
        if gltf.data.scenes is not None:
            for scene_idx, scene in enumerate(gltf.data.scenes):
                BlenderScene.create(gltf, scene_idx)
            # keep active object name if needed (to be able to set as active object at end)
            if gltf.data.scene is not None:
                if scene_idx == gltf.data.scene:
                    if bpy.app.version < (2, 80, 0):
                        active_object_name_at_end = bpy.context.scene.objects.active.name
                    else:
                        active_object_name_at_end = bpy.context.view_layer.objects.active.name
            else:
                if scene_idx == 0:
                    if bpy.app.version < (2, 80, 0):
                        active_object_name_at_end = bpy.context.scene.objects.active.name
                    else:
                        active_object_name_at_end = bpy.context.view_layer.objects.active.name
        else:
            # special case where there is no scene in glTF file
            # generate all objects in current scene
            BlenderScene.create(gltf, None)
            if bpy.app.version < (2, 80, 0):
                active_object_name_at_end = bpy.context.scene.objects.active.name
            else:
                active_object_name_at_end = bpy.context.view_layer.objects.active.name

        # Armature correction
        # Tries to set the bone tails so that they look logical.
        # If a bone has children, then set the tail to the average of all children heads,
        # Otherwise calculate the difference between the head and the tail
        # of the parent bone and calculate the tail from that.

        for armobj in [obj for obj in bpy.data.objects if obj.type == "ARMATURE"]:
            if bpy.app.version < (2, 80, 0):
                # Take into account only armature from this scene
                if armobj.name not in bpy.context.scene.objects:
                    continue
                bpy.context.scene.objects.active = armobj
            else:
                # Take into account only armature from this scene
                if armobj.name not in bpy.context.view_layer.objects:
                    continue
                bpy.context.view_layer.objects.active = armobj
            armature = armobj.data
            bpy.ops.object.mode_set(mode="EDIT")
            no_children_bones = []
            for bone in armature.edit_bones:
                child_bone_sum = [0, 0, 0]
                child_count = 0
                for child in bone.children:
                    child_bone_sum[0] += child.head[0]
                    child_bone_sum[1] += child.head[1]
                    child_bone_sum[2] += child.head[2]
                    child_count += 1
                if child_count == 0:
                    if bone.parent is not None:
                        no_children_bones.append(bone)
                else:
                    bone.tail[0] = child_bone_sum[0]/child_count
                    bone.tail[1] = child_bone_sum[1]/child_count
                    bone.tail[2] = child_bone_sum[2]/child_count
            for bone in no_children_bones:
                disp_x = bone.parent.tail[0] - bone.parent.head[0]
                disp_y = bone.parent.tail[1] - bone.parent.head[1]
                disp_z = bone.parent.tail[2] - bone.parent.head[2]
                bone.tail = [bone.head[0] + disp_x, bone.head[1] + disp_y, bone.head[2] + disp_z]

            bpy.ops.object.mode_set(mode="OBJECT")

        # Set active object
        if active_object_name_at_end is not None:
            if bpy.app.version < (2, 80, 0):
                bpy.context.scene.objects.active = bpy.data.objects[active_object_name_at_end]
            else:
                bpy.context.view_layer.objects.active = bpy.data.objects[active_object_name_at_end]

    @staticmethod
    def pre_compute(gltf):
        """Pre compute, just before creation."""
        # default scene used
        gltf.blender_scene = None

        # Check if there is animation on object
        # Init is to False, and will be set to True during creation
        gltf.animation_object = False

        # Store shapekeys equivalent between target & shapekey index
        # For example when no POSITION on target
        gltf.shapekeys = {}

        # Blender material
        if gltf.data.materials:
            for material in gltf.data.materials:
                material.blender_material = {}

                if material.pbr_metallic_roughness:
                    # Init
                    material.pbr_metallic_roughness.color_type = gltf.SIMPLE
                    material.pbr_metallic_roughness.vertex_color = False
                    material.pbr_metallic_roughness.metallic_type = gltf.SIMPLE

                    if material.pbr_metallic_roughness.base_color_texture:
                        material.pbr_metallic_roughness.color_type = gltf.TEXTURE

                    if material.pbr_metallic_roughness.metallic_roughness_texture:
                        material.pbr_metallic_roughness.metallic_type = gltf.TEXTURE

                    if material.pbr_metallic_roughness.base_color_factor:
                        if material.pbr_metallic_roughness.color_type == gltf.TEXTURE and \
                                material.pbr_metallic_roughness.base_color_factor != [1.0, 1.0, 1.0, 1.0]:
                            material.pbr_metallic_roughness.color_type = gltf.TEXTURE_FACTOR
                    else:
                        material.pbr_metallic_roughness.base_color_factor = [1.0, 1.0, 1.0, 1.0]

                    if material.pbr_metallic_roughness.metallic_factor is not None:
                        if material.pbr_metallic_roughness.metallic_type == gltf.TEXTURE \
                                and material.pbr_metallic_roughness.metallic_factor != 1.0:
                            material.pbr_metallic_roughness.metallic_type = gltf.TEXTURE_FACTOR
                    else:
                        material.pbr_metallic_roughness.metallic_factor = 1.0

                    if material.pbr_metallic_roughness.roughness_factor is not None:
                        if material.pbr_metallic_roughness.metallic_type == gltf.TEXTURE \
                                and material.pbr_metallic_roughness.roughness_factor != 1.0:
                            material.pbr_metallic_roughness.metallic_type = gltf.TEXTURE_FACTOR
                    else:
                        material.pbr_metallic_roughness.roughness_factor = 1.0

                # pre compute material for KHR_materials_pbrSpecularGlossiness
                if material.extensions is not None \
                        and 'KHR_materials_pbrSpecularGlossiness' in material.extensions.keys():
                    # Init
                    material.extensions['KHR_materials_pbrSpecularGlossiness']['diffuse_type'] = gltf.SIMPLE
                    material.extensions['KHR_materials_pbrSpecularGlossiness']['vertex_color'] = False
                    material.extensions['KHR_materials_pbrSpecularGlossiness']['specgloss_type'] = gltf.SIMPLE

                    if 'diffuseTexture' in material.extensions['KHR_materials_pbrSpecularGlossiness'].keys():
                        material.extensions['KHR_materials_pbrSpecularGlossiness']['diffuse_type'] = gltf.TEXTURE

                    if 'diffuseFactor' in material.extensions['KHR_materials_pbrSpecularGlossiness'].keys():
                        if material.extensions['KHR_materials_pbrSpecularGlossiness']['diffuse_type'] == gltf.TEXTURE \
                                and material.extensions['KHR_materials_pbrSpecularGlossiness']['diffuseFactor'] != \
                                [1.0, 1.0, 1.0, 1.0]:
                            material.extensions['KHR_materials_pbrSpecularGlossiness']['diffuse_type'] = \
                                gltf.TEXTURE_FACTOR
                    else:
                        material.extensions['KHR_materials_pbrSpecularGlossiness']['diffuseFactor'] = \
                            [1.0, 1.0, 1.0, 1.0]

                    if 'specularGlossinessTexture' in material.extensions['KHR_materials_pbrSpecularGlossiness'].keys():
                        material.extensions['KHR_materials_pbrSpecularGlossiness']['specgloss_type'] = gltf.TEXTURE

                    if 'specularFactor' in material.extensions['KHR_materials_pbrSpecularGlossiness'].keys():
                        if material.extensions['KHR_materials_pbrSpecularGlossiness']['specgloss_type'] == \
                                gltf.TEXTURE \
                                and material.extensions['KHR_materials_pbrSpecularGlossiness']['specularFactor'] != \
                                [1.0, 1.0, 1.0]:
                            material.extensions['KHR_materials_pbrSpecularGlossiness']['specgloss_type'] = \
                                gltf.TEXTURE_FACTOR
                    else:
                        material.extensions['KHR_materials_pbrSpecularGlossiness']['specularFactor'] = [1.0, 1.0, 1.0]

                    if 'glossinessFactor' not in material.extensions['KHR_materials_pbrSpecularGlossiness'].keys():
                        material.extensions['KHR_materials_pbrSpecularGlossiness']['glossinessFactor'] = 1.0

        # images
        if gltf.data.images is not None:
            for img in gltf.data.images:
                img.blender_image_name = None

        if gltf.data.nodes is None:
            # Something is wrong in file, there is no nodes
            return

        for node_idx, node in enumerate(gltf.data.nodes):

            # Weight animation management
            node.weight_animation = False

            # skin management
            if node.skin is not None and node.mesh is not None:
                if not hasattr(gltf.data.skins[node.skin], "node_ids"):
                    gltf.data.skins[node.skin].node_ids = []

                gltf.data.skins[node.skin].node_ids.append(node_idx)

            # Lights management
            node.correction_needed = False

            # transform management
            if node.matrix:
                node.transform = node.matrix
                continue

            # No matrix, but TRS
            mat = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]  # init

            if node.scale:
                mat = TRS.scale_to_matrix(node.scale)

            if node.rotation:
                q_mat = TRS.quaternion_to_matrix(node.rotation)
                mat = TRS.matrix_multiply(q_mat, mat)

            if node.translation:
                loc_mat = TRS.translation_to_matrix(node.translation)
                mat = TRS.matrix_multiply(loc_mat, mat)

            node.transform = mat


        # joint management
        for node_idx, node in enumerate(gltf.data.nodes):
            is_joint, skin_idx = gltf.is_node_joint(node_idx)
            if is_joint:
                node.is_joint = True
                node.skin_id = skin_idx
            else:
                node.is_joint = False

        if gltf.data.skins:
            for skin_id, skin in enumerate(gltf.data.skins):
                # init blender values
                skin.blender_armature_name = None
                # if skin.skeleton and skin.skeleton not in skin.joints:
                #     gltf.data.nodes[skin.skeleton].is_joint = True
                #     gltf.data.nodes[skin.skeleton].skin_id  = skin_id

        # Dispatch animation
        if gltf.data.animations:
            for node_idx, node in enumerate(gltf.data.nodes):
                node.animations = {}

            for anim_idx, anim in enumerate(gltf.data.animations):
                for channel_idx, channel in enumerate(anim.channels):
                    if anim_idx not in gltf.data.nodes[channel.target.node].animations.keys():
                        gltf.data.nodes[channel.target.node].animations[anim_idx] = []
                    gltf.data.nodes[channel.target.node].animations[anim_idx].append(channel_idx)
                    # Manage node with animation on weights, that are animated in meshes in Blender (ShapeKeys)
                    if channel.target.path == "weights":
                        gltf.data.nodes[channel.target.node].weight_animation = True

        # Meshes
        if gltf.data.meshes:
            for mesh in gltf.data.meshes:
                mesh.blender_name = None
                mesh.is_weight_animated = False
