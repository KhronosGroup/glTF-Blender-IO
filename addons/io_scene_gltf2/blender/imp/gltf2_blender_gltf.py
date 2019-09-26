# Copyright 2018-2019 The glTF-Blender-IO authors.
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
        # Try to detect bone chains, and set bone lengths
        # To detect if a bone is in a chain, we try to detect if a bone head is aligned
        # with parent_bone :
        #          Parent bone defined a line (between head & tail)
        #          Bone head defined a point
        #          Calcul of distance between point and line
        #          If < threshold --> In a chain
        # Based on an idea of @Menithal, but added alignement detection to avoid some bad cases

        threshold = 0.001
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
            for bone in armature.edit_bones:
                if bone.parent is None:
                    continue

                parent = bone.parent

                # case where 2 bones are aligned (not in chain, same head)
                if (bone.head - parent.head).length < threshold:
                    continue

                u = (parent.tail - parent.head).normalized()
                point = bone.head
                distance = ((point - parent.head).cross(u)).length / u.length
                if distance < threshold:
                    save_parent_direction = (parent.tail - parent.head).normalized().copy()
                    save_parent_tail = parent.tail.copy()
                    parent.tail = bone.head

                    # case where 2 bones are aligned (not in chain, same head)
                    # bone is no more is same direction
                    if (parent.tail - parent.head).normalized().dot(save_parent_direction) < 0.9:
                        parent.tail = save_parent_tail

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

            track_names = set()
            for anim_idx, anim in enumerate(gltf.data.animations):
                # Pick pair-wise unique name for each animation to use as a name
                # for its NLA tracks.
                desired_name = anim.name or "Anim_%d" % anim_idx
                anim.track_name = BlenderGlTF.find_unused_name(track_names, desired_name)
                track_names.add(anim.track_name)

                for channel_idx, channel in enumerate(anim.channels):
                    if channel.target.node is None:
                        continue

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

        # Calculate names for each mesh's shapekeys
        for mesh in gltf.data.meshes:
            mesh.shapekey_names = []
            used_names = set()

            for sk, target in enumerate(mesh.primitives[0].targets or []):
                if 'POSITION' not in target:
                    mesh.shapekey_names.append(None)
                    continue

                # Check if glTF file has some extras with targetNames. Otherwise
                # use the name of the POSITION accessor on the first primitive.
                shapekey_name = None
                if mesh.extras is not None:
                    if 'targetNames' in mesh.extras and sk < len(mesh.extras['targetNames']):
                        shapekey_name = mesh.extras['targetNames'][sk]
                if shapekey_name is None:
                    if gltf.data.accessors[target['POSITION']].name is not None:
                        shapekey_name = gltf.data.accessors[target['POSITION']].name
                if shapekey_name is None:
                    shapekey_name = "target_" + str(sk)

                shapekey_name = BlenderGlTF.find_unused_name(used_names, shapekey_name)
                used_names.add(shapekey_name)

                mesh.shapekey_names.append(shapekey_name)

    @staticmethod
    def find_unused_name(haystack, desired_name):
        """Finds a name not in haystack and <= 63 UTF-8 bytes.
        (the limit on the size of a Blender name.)
        If a is taken, tries a.001, then a.002, etc.
        """
        stem = desired_name[:63]
        suffix = ''
        cntr = 1
        while True:
            name = stem + suffix

            if len(name.encode('utf-8')) > 63:
                stem = stem[:-1]
                continue

            if name not in haystack:
                return name

            suffix = '.%03d' % cntr
            cntr += 1
