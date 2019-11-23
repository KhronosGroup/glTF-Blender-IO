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

import math
import bpy
from mathutils import Matrix, Quaternion

from . import gltf2_blender_export_keys
from io_scene_gltf2.blender.com import gltf2_blender_math
from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached
from io_scene_gltf2.blender.exp import gltf2_blender_gather_skins
from io_scene_gltf2.blender.exp import gltf2_blender_gather_cameras
from io_scene_gltf2.blender.exp import gltf2_blender_gather_mesh
from io_scene_gltf2.blender.exp import gltf2_blender_gather_joints
from io_scene_gltf2.blender.exp import gltf2_blender_extract
from io_scene_gltf2.blender.exp import gltf2_blender_gather_lights
from ..com.gltf2_blender_extras import generate_extras
from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.io.com import gltf2_io_extensions


def gather_node(blender_object, blender_scene, export_settings):
    # custom cache to avoid cache miss when called from animation
    # with blender_scene=None

    # invalidate cache if export settings have changed
    if not hasattr(gather_node, "__export_settings") or export_settings != gather_node.__export_settings:
        gather_node.__cache = {}
        gather_node.__export_settings = export_settings

    if blender_scene is None and blender_object.name in gather_node.__cache:
        return gather_node.__cache[blender_object.name]

    node = __gather_node(blender_object, blender_scene, export_settings)
    gather_node.__cache[blender_object.name] = node
    return node

@cached
def __gather_node(blender_object, blender_scene, export_settings):
    # If blender_scene is None, we are coming from animation export
    # Check to know if object is exported is already done, so we don't check
    # again if object is instanced in scene : this check was already done when exporting object itself
    if not __filter_node(blender_object, blender_scene, export_settings):
        return None

    node = gltf2_io.Node(
        camera=__gather_camera(blender_object, export_settings),
        children=__gather_children(blender_object, blender_scene, export_settings),
        extensions=__gather_extensions(blender_object, export_settings),
        extras=__gather_extras(blender_object, export_settings),
        matrix=__gather_matrix(blender_object, export_settings),
        mesh=__gather_mesh(blender_object, export_settings),
        name=__gather_name(blender_object, export_settings),
        rotation=None,
        scale=None,
        skin=__gather_skin(blender_object, export_settings),
        translation=None,
        weights=__gather_weights(blender_object, export_settings)
    )

    # If node mesh is skined, transforms should be ignored at import, so no need to set them here
    if node.skin is None:
        node.translation, node.rotation, node.scale = __gather_trans_rot_scale(blender_object, export_settings)

    if export_settings[gltf2_blender_export_keys.YUP]:
        if blender_object.type == 'LIGHT' and export_settings[gltf2_blender_export_keys.LIGHTS]:
            correction_node = __get_correction_node(blender_object, export_settings)
            correction_node.extensions = {"KHR_lights_punctual": node.extensions["KHR_lights_punctual"]}
            del node.extensions["KHR_lights_punctual"]
            node.children.append(correction_node)
        if blender_object.type == 'CAMERA' and export_settings[gltf2_blender_export_keys.CAMERAS]:
            correction_node = __get_correction_node(blender_object, export_settings)
            correction_node.camera = node.camera
            node.children.append(correction_node)
        node.camera = None

    return node


def __filter_node(blender_object, blender_scene, export_settings):
    if blender_object.users == 0:
        return False
    if bpy.app.version < (2, 80, 0):
        if export_settings[gltf2_blender_export_keys.SELECTED] and not blender_object.select:
            return False
        if blender_scene is not None:
            if blender_object.name not in blender_scene.objects:
                return False
    else:
        if blender_scene is not None:
            instanced =  any([blender_object.name in layer.objects for layer in blender_scene.view_layers])
            if instanced is False:
                # Check if object is from a linked collection
                if any([blender_object.name in coll.objects for coll in bpy.data.collections if coll.library is not None]):
                    pass
                else:
                    # Not instanced, not linked -> We don't keep this object
                    return False
        if export_settings[gltf2_blender_export_keys.SELECTED] and blender_object.select_get() is False:
            return False

    return True


def __gather_camera(blender_object, export_settings):
    if blender_object.type != 'CAMERA':
        return None

    return gltf2_blender_gather_cameras.gather_camera(blender_object.data, export_settings)


def __gather_children(blender_object, blender_scene, export_settings):
    children = []
    # standard children
    for child_object in blender_object.children:
        if child_object.parent_bone:
            # this is handled further down,
            # as the object should be a child of the specific bone,
            # not the Armature object
            continue
        node = gather_node(child_object, blender_scene, export_settings)
        if node is not None:
            children.append(node)
    # blender dupli objects
    if bpy.app.version < (2, 80, 0):
        if blender_object.dupli_type == 'GROUP' and blender_object.dupli_group:
            for dupli_object in blender_object.dupli_group.objects:
                node = gather_node(dupli_object, blender_scene, export_settings)
                if node is not None:
                    children.append(node)
    else:
        if blender_object.instance_type == 'COLLECTION' and blender_object.instance_collection:
            for dupli_object in blender_object.instance_collection.objects:
                node = gather_node(dupli_object, blender_scene, export_settings)
                if node is not None:
                    children.append(node)

    # blender bones
    if blender_object.type == "ARMATURE":
        root_joints = []
        if export_settings["gltf_def_bones"] is False:
            bones = blender_object.pose.bones
        else:
            bones, _, _ = gltf2_blender_gather_skins.get_bone_tree(None, blender_object)
            bones = [blender_object.pose.bones[b.name] for b in bones]
        for blender_bone in bones:
            if not blender_bone.parent:
                joint = gltf2_blender_gather_joints.gather_joint(blender_bone, export_settings)
                children.append(joint)
                root_joints.append(joint)
        # handle objects directly parented to bones
        direct_bone_children = [child for child in blender_object.children if child.parent_bone]
        def find_parent_joint(joints, name):
            for joint in joints:
                if joint.name == name:
                    return joint
                parent_joint = find_parent_joint(joint.children, name)
                if parent_joint:
                    return parent_joint
            return None
        for child in direct_bone_children:
            # find parent joint
            parent_joint = find_parent_joint(root_joints, child.parent_bone)
            if not parent_joint:
                continue
            child_node = gather_node(child, None, export_settings)
            if child_node is None:
                continue
            blender_bone = blender_object.pose.bones[parent_joint.name]
            # fix rotation
            if export_settings[gltf2_blender_export_keys.YUP]:
                rot = child_node.rotation
                if rot is None:
                    rot = [0, 0, 0, 1]

                rot_quat = Quaternion(rot)
                axis_basis_change = Matrix(
                    ((1.0, 0.0, 0.0, 0.0), (0.0, 0.0, -1.0, 0.0), (0.0, 1.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0)))
                mat = gltf2_blender_math.multiply(axis_basis_change, child.matrix_basis)
                mat = gltf2_blender_math.multiply(child.matrix_parent_inverse, mat)

                _, rot_quat, _ = mat.decompose()
                child_node.rotation = [rot_quat[1], rot_quat[2], rot_quat[3], rot_quat[0]]

            # fix translation (in blender bone's tail is the origin for children)
            trans, _, _ = child.matrix_local.decompose()
            if trans is None:
                trans = [0, 0, 0]
            # bones go down their local y axis
            bone_tail = [0, blender_bone.length, 0]
            child_node.translation = [trans[idx] + bone_tail[idx] for idx in range(3)]

            parent_joint.children.append(child_node)

    return children


def __gather_extensions(blender_object, export_settings):
    extensions = {}

    if export_settings["gltf_lights"] and (blender_object.type == "LAMP" or blender_object.type == "LIGHT"):
        blender_lamp = blender_object.data
        light = gltf2_blender_gather_lights.gather_lights_punctual(
            blender_lamp,
            export_settings
        )
        if light is not None:
            light_extension = gltf2_io_extensions.ChildOfRootExtension(
                name="KHR_lights_punctual",
                path=["lights"],
                extension=light
            )
            extensions["KHR_lights_punctual"] = gltf2_io_extensions.Extension(
                name="KHR_lights_punctual",
                extension={
                    "light": light_extension
                }
            )

    return extensions if extensions else None


def __gather_extras(blender_object, export_settings):
    if export_settings['gltf_extras']:
        return generate_extras(blender_object)
    return None


def __gather_matrix(blender_object, export_settings):
    # return blender_object.matrix_local
    return []


def __gather_mesh(blender_object, export_settings):
    if blender_object.type != "MESH":
        return None

    modifier_normal_types = [
        "NORMAL_EDIT",
        "WEIGHTED_NORMAL"
    ]

    # If not using vertex group, they are irrelevant for caching --> ensure that they do not trigger a cache miss
    vertex_groups = blender_object.vertex_groups
    modifiers = blender_object.modifiers
    if len(vertex_groups) == 0:
        vertex_groups = None
    if len(modifiers) == 0:
        modifiers = None

    if export_settings[gltf2_blender_export_keys.APPLY]:
        auto_smooth = blender_object.data.use_auto_smooth
        edge_split = None
        some_normals_modifier = any([m in modifier_normal_types for m in [mod.type for mod in blender_object.modifiers]])
        if auto_smooth and not some_normals_modifier:
            edge_split = blender_object.modifiers.new('Temporary_Auto_Smooth', 'EDGE_SPLIT')
            edge_split.split_angle = blender_object.data.auto_smooth_angle
            edge_split.use_edge_angle = not blender_object.data.has_custom_normals
            blender_object.data.use_auto_smooth = some_normals_modifier
            if bpy.app.version < (2, 80, 0):
                bpy.context.scene.update()
            else:
                bpy.context.view_layer.update()

        armature_modifiers = {}
        if export_settings[gltf2_blender_export_keys.SKINS]:
            # temporarily disable Armature modifiers if exporting skins
            for idx, modifier in enumerate(blender_object.modifiers):
                if modifier.type == 'ARMATURE':
                    armature_modifiers[idx] = modifier.show_viewport
                    modifier.show_viewport = False

        if bpy.app.version < (2, 80, 0):
            blender_mesh = blender_object.to_mesh(bpy.context.scene, True, 'PREVIEW')
        else:
            depsgraph = bpy.context.evaluated_depsgraph_get()
            blender_mesh_owner = blender_object.evaluated_get(depsgraph)
            blender_mesh = blender_mesh_owner.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
        for prop in blender_object.data.keys():
            blender_mesh[prop] = blender_object.data[prop]
        skip_filter = True

        if export_settings[gltf2_blender_export_keys.SKINS]:
            # restore Armature modifiers
            for idx, show_viewport in armature_modifiers.items():
                blender_object.modifiers[idx].show_viewport = show_viewport

        if auto_smooth and not some_normals_modifier:
            blender_object.data.use_auto_smooth = True
            blender_object.modifiers.remove(edge_split)
    else:
        blender_mesh = blender_object.data
        skip_filter = False
        modifiers = None # avoid cache miss
        # If no skin are exported, no need to have vertex group, this will create a cache miss
        if not export_settings[gltf2_blender_export_keys.SKINS]:
            vertex_groups = None
        else:
            # Check if there is an armature modidier
            if len([mod for mod in blender_object.modifiers if mod.type == "ARMATURE"]) == 0:
                vertex_groups = None # Not needed if no armature, avoid a cache miss

    material_names = tuple([ms.material.name for ms in blender_object.material_slots if ms.material is not None])

    # retrieve armature
    # Because mesh data will be transforms to skeleton space,
    # we can't instantiate multiple object at different location, skined by same armature
    blender_object_for_skined_data = None
    if export_settings[gltf2_blender_export_keys.SKINS]:
        for idx, modifier in enumerate(blender_object.modifiers):
            if modifier.type == 'ARMATURE':
                blender_object_for_skined_data = blender_object

    result = gltf2_blender_gather_mesh.gather_mesh(blender_mesh,
                                                   blender_object_for_skined_data,
                                                   vertex_groups,
                                                   modifiers,
                                                   skip_filter,
                                                   material_names,
                                                   export_settings)

    if export_settings[gltf2_blender_export_keys.APPLY]:
        if bpy.app.version < (2, 80, 0):
            bpy.data.meshes.remove(blender_mesh)
        else:
            blender_mesh_owner.to_mesh_clear()

    return result


def __gather_name(blender_object, export_settings):
    if bpy.app.version < (2, 80, 0):
        if blender_object.dupli_type == 'GROUP' and blender_object.dupli_group:
            return "Duplication_Offset_" + blender_object.name
    else:
        if blender_object.instance_type == 'COLLECTION' and blender_object.instance_collection:
            return "Duplication_Offset_" + blender_object.name
    return blender_object.name


def __gather_trans_rot_scale(blender_object, export_settings):
    if blender_object.matrix_parent_inverse == Matrix.Identity(4):
        trans = blender_object.location

        if blender_object.rotation_mode in ['QUATERNION', 'AXIS_ANGLE']:
            rot = blender_object.rotation_quaternion
        else:
            rot = blender_object.rotation_euler.to_quaternion()

        sca = blender_object.scale
    else:
        # matrix_local = matrix_parent_inverse*location*rotation*scale
        # Decomposing matrix_local gives less accuracy, but is needed if matrix_parent_inverse is not the identity.
        trans, rot, sca = gltf2_blender_extract.decompose_transition(blender_object.matrix_local, export_settings)

    trans = gltf2_blender_extract.convert_swizzle_location(trans, None, None, export_settings)
    rot = gltf2_blender_extract.convert_swizzle_rotation(rot, export_settings)
    sca = gltf2_blender_extract.convert_swizzle_scale(sca, export_settings)

    if bpy.app.version < (2, 80, 0):
        if blender_object.dupli_type == 'GROUP' and blender_object.dupli_group:
            trans = -gltf2_blender_extract.convert_swizzle_location(
                blender_object.dupli_group.dupli_offset, None, None, export_settings)
    else:
        if blender_object.instance_type == 'COLLECTION' and blender_object.instance_collection:
            trans = -gltf2_blender_extract.convert_swizzle_location(
                blender_object.instance_collection.instance_offset, None, None, export_settings)
    translation, rotation, scale = (None, None, None)
    trans[0], trans[1], trans[2] = gltf2_blender_math.round_if_near(trans[0], 0.0), gltf2_blender_math.round_if_near(trans[1], 0.0), \
                                   gltf2_blender_math.round_if_near(trans[2], 0.0)
    rot[0], rot[1], rot[2], rot[3] = gltf2_blender_math.round_if_near(rot[0], 1.0), gltf2_blender_math.round_if_near(rot[1], 0.0), \
                                     gltf2_blender_math.round_if_near(rot[2], 0.0), gltf2_blender_math.round_if_near(rot[3], 0.0)
    sca[0], sca[1], sca[2] = gltf2_blender_math.round_if_near(sca[0], 1.0), gltf2_blender_math.round_if_near(sca[1], 1.0), \
                             gltf2_blender_math.round_if_near(sca[2], 1.0)
    if trans[0] != 0.0 or trans[1] != 0.0 or trans[2] != 0.0:
        translation = [trans[0], trans[1], trans[2]]
    if rot[0] != 1.0 or rot[1] != 0.0 or rot[2] != 0.0 or rot[3] != 0.0:
        rotation = [rot[1], rot[2], rot[3], rot[0]]
    if sca[0] != 1.0 or sca[1] != 1.0 or sca[2] != 1.0:
        scale = [sca[0], sca[1], sca[2]]
    return translation, rotation, scale


def __gather_skin(blender_object, export_settings):
    modifiers = {m.type: m for m in blender_object.modifiers}
    if "ARMATURE" not in modifiers or modifiers["ARMATURE"].object is None:
        return None

    # no skin needed when the modifier is linked without having a vertex group
    vertex_groups = blender_object.vertex_groups
    if len(vertex_groups) == 0:
        return None

    # check if any vertices in the mesh are part of a vertex group
    if bpy.app.version < (2, 80, 0):
        blender_mesh = blender_object.to_mesh(bpy.context.scene, True, 'PREVIEW')
    else:
        depsgraph = bpy.context.evaluated_depsgraph_get()
        blender_mesh_owner = blender_object.evaluated_get(depsgraph)
        blender_mesh = blender_mesh_owner.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
    if not any(vertex.groups is not None and len(vertex.groups) > 0 for vertex in blender_mesh.vertices):
        return None

    # Skins and meshes must be in the same glTF node, which is different from how blender handles armatures
    return gltf2_blender_gather_skins.gather_skin(modifiers["ARMATURE"].object, export_settings)


def __gather_weights(blender_object, export_settings):
    return None


def __get_correction_node(blender_object, export_settings):
    correction_quaternion = gltf2_blender_extract.convert_swizzle_rotation(
        Quaternion((1.0, 0.0, 0.0), math.radians(-90.0)), export_settings)
    correction_quaternion = [correction_quaternion[1], correction_quaternion[2],
                             correction_quaternion[3], correction_quaternion[0]]
    return gltf2_io.Node(
        camera=None,
        children=None,
        extensions=None,
        extras=None,
        matrix=None,
        mesh=None,
        name=blender_object.name + '_Orientation',
        rotation=correction_quaternion,
        scale=None,
        skin=None,
        translation=None,
        weights=None
    )
