# Copyright 2018-2021 The glTF-Blender-IO authors.
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
from ..com.gltf2_blender_ui import gltf2_KHR_materials_variants_variant, gltf2_KHR_materials_variants_primitive, gltf2_KHR_materials_variants_default_material
from .gltf2_blender_material import BlenderMaterial
from io_scene_gltf2.io.imp.gltf2_io_user_extensions import import_user_extensions


class BlenderGlTF():
    """Main glTF import class."""
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("%s should not be instantiated" % cls)

    @staticmethod
    def create(gltf):
        """Create glTF main method, with optional profiling"""

        import_user_extensions('gather_import_gltf_before_hook', gltf)

        profile = bpy.app.debug_value == 102
        if profile:
            import cProfile, pstats, io
            from pstats import SortKey
            pr = cProfile.Profile()
            pr.enable()
            BlenderGlTF._create(gltf)
            pr.disable()
            s = io.StringIO()
            sortby = SortKey.TIME
            ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
            ps.print_stats()
            print(s.getvalue())
        else:
            BlenderGlTF._create(gltf)

    @staticmethod
    def _create(gltf):
        """Create glTF main worker method."""
        BlenderGlTF.set_convert_functions(gltf)
        BlenderGlTF.pre_compute(gltf)
        BlenderScene.create(gltf)

    @staticmethod
    def set_convert_functions(gltf):
        if bpy.app.debug_value != 100:
            # Unit conversion factor in (Blender units) per meter
            u = 1.0 / bpy.context.scene.unit_settings.scale_length

            # glTF Y-Up space --> Blender Z-up space
            # X,Y,Z --> X,-Z,Y
            def convert_loc(x): return u * Vector([x[0], -x[2], x[1]])
            def convert_quat(q): return Quaternion([q[3], q[0], -q[2], q[1]])
            def convert_scale(s): return Vector([s[0], s[2], s[1]])
            def convert_matrix(m):
                return Matrix([
                    [   m[0],   -m[ 8],    m[4],  m[12]*u],
                    [  -m[2],    m[10],   -m[6], -m[14]*u],
                    [   m[1],   -m[ 9],    m[5],  m[13]*u],
                    [ m[3]/u, -m[11]/u,  m[7]/u,    m[15]],
                ])

            # Batch versions operate in place on a numpy array
            def convert_locs_batch(locs):
                # x,y,z -> x,-z,y
                locs[:, [1,2]] = locs[:, [2,1]]
                locs[:, 1] *= -1
                # Unit conversion
                if u != 1: locs *= u
            def convert_normals_batch(ns):
                ns[:, [1,2]] = ns[:, [2,1]]
                ns[:, 1] *= -1

            # Correction for cameras and lights.
            # glTF: right = +X, forward = -Z, up = +Y
            # glTF after Yup2Zup: right = +X, forward = +Y, up = +Z
            # Blender: right = +X, forward = -Z, up = +Y
            # Need to carry Blender --> glTF after Yup2Zup
            gltf.camera_correction = Quaternion((2**0.5/2, 2**0.5/2, 0.0, 0.0))

        else:
            def convert_loc(x): return Vector(x)
            def convert_quat(q): return Quaternion([q[3], q[0], q[1], q[2]])
            def convert_scale(s): return Vector(s)
            def convert_matrix(m):
                return Matrix([m[0::4], m[1::4], m[2::4], m[3::4]])

            def convert_locs_batch(_locs): return
            def convert_normals_batch(_ns): return

            # Same convention, no correction needed.
            gltf.camera_correction = None

        gltf.loc_gltf_to_blender = convert_loc
        gltf.locs_batch_gltf_to_blender = convert_locs_batch
        gltf.quaternion_gltf_to_blender = convert_quat
        gltf.normals_batch_gltf_to_blender = convert_normals_batch
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

        # images
        if gltf.data.images is not None:
            for img in gltf.data.images:
                img.blender_image_name = None

        if gltf.data.nodes is None:
            # Something is wrong in file, there is no nodes
            return

        for node in gltf.data.nodes:
            # Weight animation management
            node.weight_animation = False

        # Dispatch animation
        if gltf.data.animations:
            for node in gltf.data.nodes:
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
                mesh.blender_name = {}  # caches Blender mesh name

        # Calculate names for each mesh's shapekeys
        for mesh in gltf.data.meshes or []:
            mesh.shapekey_names = []
            used_names = set(['Basis']) #Be sure to not use 'Basis' name at import, this is a reserved name

            # Look for primitive with morph targets
            for prim in (mesh.primitives or []):
                if not prim.targets:
                    continue

                for sk, _ in enumerate(prim.targets):
                    # Skip shape key for target that doesn't morph POSITION
                    morphs_position = any(
                        (prim.targets and 'POSITION' in prim.targets[sk])
                        for prim in mesh.primitives
                    )
                    if not morphs_position:
                        mesh.shapekey_names.append(None)
                        continue

                    shapekey_name = None

                    # Try to use name from extras.targetNames
                    try:
                        shapekey_name = str(mesh.extras['targetNames'][sk])
                    except Exception:
                        pass

                    # Try to get name from first primitive's POSITION accessor
                    if shapekey_name is None:
                        try:
                            shapekey_name = gltf.data.accessors[mesh.primitives[0].targets[sk]['POSITION']].name
                        except Exception:
                            pass

                    if shapekey_name is None:
                        shapekey_name = "target_" + str(sk)

                    shapekey_name = BlenderGlTF.find_unused_name(used_names, shapekey_name)
                    used_names.add(shapekey_name)

                    mesh.shapekey_names.append(shapekey_name)

                break

        # Manage KHR_materials_variants
        BlenderGlTF.manage_material_variants(gltf)


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


    @staticmethod
    def manage_material_variants(gltf):
        if not (gltf.data.extensions is not None and 'KHR_materials_variants' in gltf.data.extensions.keys()):
            gltf.KHR_materials_variants = False
            return

        gltf.KHR_materials_variants = True
        # If there is no KHR_materials_variants data in scene, create it
        if bpy.context.preferences.addons['io_scene_gltf2'].preferences.KHR_materials_variants_ui is False:
            bpy.context.preferences.addons['io_scene_gltf2'].preferences.KHR_materials_variants_ui = True
            # Setting preferences as dirty, to be sure that option is saved
            bpy.context.preferences.is_dirty = True

        if len(bpy.data.scenes[0].gltf2_KHR_materials_variants_variants) > 0:
            bpy.data.scenes[0].gltf2_KHR_materials_variants_variants.clear()

        for idx_variant, variant in enumerate(gltf.data.extensions['KHR_materials_variants']['variants']):
            var = bpy.data.scenes[0].gltf2_KHR_materials_variants_variants.add()
            var.name = variant['name']
            var.variant_idx = idx_variant
