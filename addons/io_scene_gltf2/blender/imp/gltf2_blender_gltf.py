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
from mathutils import Vector, Quaternion, Matrix
from .gltf2_blender_scene import BlenderScene


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
        BlenderGlTF.set_convert_functions(gltf)
        BlenderGlTF.pre_compute(gltf)

        gltf.display_current_node = 0
        if gltf.data.nodes is not None:
            gltf.display_total_nodes = len(gltf.data.nodes)
        else:
            gltf.display_total_nodes = "?"

        BlenderScene.create(gltf)

    @staticmethod
    def set_convert_functions(gltf):
        yup2zup = bpy.app.debug_value != 100

        if yup2zup:
            # glTF Y-Up space --> Blender Z-up space
            # X,Y,Z --> X,-Z,Y
            def convert_loc(x): return Vector([x[0], -x[2], x[1]])
            def convert_quat(q): return Quaternion([q[3], q[0], -q[2], q[1]])
            def convert_normal(n): return Vector([n[0], -n[2], n[1]])
            def convert_scale(s): return Vector([s[0], s[2], s[1]])
            def convert_matrix(m):
                return Matrix([
                    [ m[0], -m[ 8],  m[4],  m[12]],
                    [-m[2],  m[10], -m[6], -m[14]],
                    [ m[1], -m[ 9],  m[5],  m[13]],
                    [ m[3], -m[11],  m[7],  m[15]],
                ])

            # Correction for cameras and lights.
            # glTF: right = +X, forward = -Z, up = +Y
            # glTF after Yup2Zup: right = +X, forward = +Y, up = +Z
            # Blender: right = +X, forward = -Z, up = +Y
            # Need to carry Blender --> glTF after Yup2Zup
            gltf.camera_correction = Quaternion((2**0.5/2, 2**0.5/2, 0.0, 0.0))

        else:
            def convert_loc(x): return Vector(x)
            def convert_quat(q): return Quaternion([q[3], q[0], q[1], q[2]])
            def convert_normal(n): return Vector(n)
            def convert_scale(s): return Vector(s)
            def convert_matrix(m):
                return Matrix([m[0::4], m[1::4], m[2::4], m[3::4]])

            # Same convention, no correction needed.
            gltf.camera_correction = None

        gltf.loc_gltf_to_blender = convert_loc
        gltf.quaternion_gltf_to_blender = convert_quat
        gltf.normal_gltf_to_blender = convert_normal
        gltf.scale_gltf_to_blender = convert_scale
        gltf.matrix_gltf_to_blender = convert_matrix

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
                mesh.blender_name = {}  # cache Blender mesh (keyed by skin_idx)
                mesh.is_weight_animated = False

        # Calculate names for each mesh's shapekeys
        for mesh in gltf.data.meshes or []:
            mesh.shapekey_names = []
            used_names = set()

            # Some invalid glTF files has empty primitive tab
            if len(mesh.primitives) > 0:
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
