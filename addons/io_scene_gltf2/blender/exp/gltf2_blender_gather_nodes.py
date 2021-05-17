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

import math
import bpy
from mathutils import Matrix, Quaternion, Vector

from . import gltf2_blender_export_keys
from io_scene_gltf2.blender.com import gltf2_blender_math
from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached
from io_scene_gltf2.blender.exp import gltf2_blender_gather_skins
from io_scene_gltf2.blender.exp import gltf2_blender_gather_cameras
from io_scene_gltf2.blender.exp import gltf2_blender_gather_mesh
from io_scene_gltf2.blender.exp import gltf2_blender_gather_joints
from io_scene_gltf2.blender.exp import gltf2_blender_gather_lights
from ..com.gltf2_blender_extras import generate_extras
from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.io.com import gltf2_io_extensions
from io_scene_gltf2.io.exp.gltf2_io_user_extensions import export_user_extensions
from io_scene_gltf2.io.com.gltf2_io_debug import print_console


def gather_node(blender_object, library, blender_scene, dupli_object_parent, export_settings):
    # custom cache to avoid cache miss when called from animation
    # with blender_scene=None

    # invalidate cache if export settings have changed
    if not hasattr(gather_node, "__export_settings") or export_settings != gather_node.__export_settings:
        gather_node.__cache = {}
        gather_node.__export_settings = export_settings

    if blender_scene is None and (blender_object.name, library) in gather_node.__cache:
        return gather_node.__cache[(blender_object.name, library)]

    node = __gather_node(blender_object, library, blender_scene, dupli_object_parent, export_settings)
    gather_node.__cache[(blender_object.name, library)] = node
    return node

@cached
def __gather_node(blender_object, library, blender_scene, dupli_object_parent, export_settings):
    children = __gather_children(blender_object, blender_scene, export_settings)

    camera = None
    mesh = None
    skin = None
    weights = None

    # If blender_scene is None, we are coming from animation export
    # Check to know if object is exported is already done, so we don't check
    # again if object is instanced in scene : this check was already done when exporting object itself
    if not __filter_node(blender_object, blender_scene, export_settings):
        if children:
            # This node should be filtered out, but has un-filtered children present.
            # So, export this node, excluding its camera, mesh, skin, and weights.
            # The transformations and animations on this node will have visible effects on children.
            pass
        else:
            # This node is filtered out, and has no un-filtered children or descendants.
            return None
    else:
        # This node is being fully exported.
        camera = __gather_camera(blender_object, export_settings)
        mesh = __gather_mesh(blender_object, library, export_settings)
        skin = __gather_skin(blender_object, export_settings)
        weights = __gather_weights(blender_object, export_settings)

    node = gltf2_io.Node(
        camera=camera,
        children=children,
        extensions=__gather_extensions(blender_object, export_settings),
        extras=__gather_extras(blender_object, export_settings),
        matrix=__gather_matrix(blender_object, export_settings),
        mesh=mesh,
        name=__gather_name(blender_object, export_settings),
        rotation=None,
        scale=None,
        skin=skin,
        translation=None,
        weights=weights
    )

    # If node mesh is skined, transforms should be ignored at import, so no need to set them here
    if node.skin is None:
        node.translation, node.rotation, node.scale = __gather_trans_rot_scale(blender_object, export_settings)

    if export_settings[gltf2_blender_export_keys.YUP]:
        # Checking node.extensions is making sure that the type of lamp is managed, and will be exported
        if blender_object.type == 'LIGHT' and export_settings[gltf2_blender_export_keys.LIGHTS] and node.extensions:
            correction_node = __get_correction_node(blender_object, export_settings)
            correction_node.extensions = {"KHR_lights_punctual": node.extensions["KHR_lights_punctual"]}
            del node.extensions["KHR_lights_punctual"]
            node.children.append(correction_node)
        if blender_object.type == 'CAMERA' and export_settings[gltf2_blender_export_keys.CAMERAS]:
            correction_node = __get_correction_node(blender_object, export_settings)
            correction_node.camera = node.camera
            node.children.append(correction_node)
        node.camera = None

    export_user_extensions('gather_node_hook', export_settings, node, blender_object)

    return node


def __filter_node(blender_object, blender_scene, export_settings):
    if blender_object.users == 0:
        return False
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

    if export_settings[gltf2_blender_export_keys.VISIBLE] and blender_object.visible_get() is False:
        return False

    # render_get() doesn't exist, so unfortunately this won't take into account the Collection settings
    if export_settings[gltf2_blender_export_keys.RENDERABLE] and blender_object.hide_render is True:
        return False

    if export_settings[gltf2_blender_export_keys.ACTIVE_COLLECTION]:
        found = any(x == blender_object for x in bpy.context.collection.all_objects)

        if not found:
            return False

    return True


def __gather_camera(blender_object, export_settings):
    if blender_object.type != 'CAMERA':
        return None

    return gltf2_blender_gather_cameras.gather_camera(blender_object.data, export_settings)


def __gather_children(blender_object, blender_scene, export_settings):
    children = []
    # standard children
    for _child_object in blender_object.children:
        if _child_object.parent_bone:
            # this is handled further down,
            # as the object should be a child of the specific bone,
            # not the Armature object
            continue

        child_object = _child_object.proxy if _child_object.proxy else _child_object

        node = gather_node(child_object,
            child_object.library.name if child_object.library else None,
            blender_scene, None, export_settings)
        if node is not None:
            children.append(node)
    # blender dupli objects
    if blender_object.instance_type == 'COLLECTION' and blender_object.instance_collection:
        for dupli_object in blender_object.instance_collection.objects:
            if dupli_object.parent is not None:
                continue
            if dupli_object.type == "ARMATURE":
                continue # There is probably a proxy
            node = gather_node(dupli_object,
                dupli_object.library.name if dupli_object.library else None,
                blender_scene, blender_object.name, export_settings)
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
                joint = gltf2_blender_gather_joints.gather_joint(blender_object, blender_bone, export_settings)
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
            child_node = gather_node(child, None, None, None, export_settings)
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
                mat = child.matrix_parent_inverse @ child.matrix_basis
                mat = mat @ axis_basis_change

                _, rot_quat, _ = mat.decompose()
                child_node.rotation = [rot_quat[1], rot_quat[2], rot_quat[3], rot_quat[0]]

            # fix translation (in blender bone's tail is the origin for children)
            trans, _, _ = child.matrix_local.decompose()
            if trans is None:
                trans = [0, 0, 0]
            # bones go down their local y axis
            if blender_bone.matrix.to_scale()[1] >= 1e-6:
                bone_tail = [0, blender_bone.length / blender_bone.matrix.to_scale()[1], 0]
            else:
                bone_tail = [0,0,0] # If scale is 0, tail == head
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


def __gather_mesh(blender_object, library, export_settings):
    if blender_object.type in ['CURVE', 'SURFACE', 'FONT']:
        return __gather_mesh_from_nonmesh(blender_object, library, export_settings)

    if blender_object.type != "MESH":
        return None

    # If not using vertex group, they are irrelevant for caching --> ensure that they do not trigger a cache miss
    vertex_groups = blender_object.vertex_groups
    modifiers = blender_object.modifiers
    if len(vertex_groups) == 0:
        vertex_groups = None
    if len(modifiers) == 0:
        modifiers = None

    if export_settings[gltf2_blender_export_keys.APPLY]:
        armature_modifiers = {}
        if export_settings[gltf2_blender_export_keys.SKINS]:
            # temporarily disable Armature modifiers if exporting skins
            for idx, modifier in enumerate(blender_object.modifiers):
                if modifier.type == 'ARMATURE':
                    armature_modifiers[idx] = modifier.show_viewport
                    modifier.show_viewport = False

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
    else:
        blender_mesh = blender_object.data
        skip_filter = False
        # If no skin are exported, no need to have vertex group, this will create a cache miss
        if not export_settings[gltf2_blender_export_keys.SKINS]:
            vertex_groups = None
            modifiers = None
        else:
            # Check if there is an armature modidier
            if len([mod for mod in blender_object.modifiers if mod.type == "ARMATURE"]) == 0:
                vertex_groups = None # Not needed if no armature, avoid a cache miss
                modifiers = None

    materials = tuple(ms.material for ms in blender_object.material_slots)
    material_names = tuple(None if mat is None else mat.name for mat in materials)

    # retrieve armature
    # Because mesh data will be transforms to skeleton space,
    # we can't instantiate multiple object at different location, skined by same armature
    blender_object_for_skined_data = None
    if export_settings[gltf2_blender_export_keys.SKINS]:
        for idx, modifier in enumerate(blender_object.modifiers):
            if modifier.type == 'ARMATURE':
                blender_object_for_skined_data = blender_object

    result = gltf2_blender_gather_mesh.gather_mesh(blender_mesh,
                                                   library,
                                                   blender_object_for_skined_data,
                                                   vertex_groups,
                                                   modifiers,
                                                   skip_filter,
                                                   material_names,
                                                   export_settings)

    if export_settings[gltf2_blender_export_keys.APPLY]:
        blender_mesh_owner.to_mesh_clear()

    return result


def __gather_mesh_from_nonmesh(blender_object, library, export_settings):
    """Handles curves, surfaces, text, etc."""
    needs_to_mesh_clear = False
    try:
        # Convert to a mesh
        try:
            if export_settings[gltf2_blender_export_keys.APPLY]:
                depsgraph = bpy.context.evaluated_depsgraph_get()
                blender_mesh_owner = blender_object.evaluated_get(depsgraph)
                blender_mesh = blender_mesh_owner.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
                # TODO: do we need preserve_all_data_layers?

            else:
                blender_mesh_owner = blender_object
                blender_mesh = blender_mesh_owner.to_mesh()

            # In some cases (for example curve with single vertice), no blender_mesh is created (without crash)
            if blender_mesh is None:
                return None

        except Exception:
            return None

        needs_to_mesh_clear = True

        skip_filter = True
        material_names = tuple([ms.material.name for ms in blender_object.material_slots if ms.material is not None])
        vertex_groups = None
        modifiers = None
        blender_object_for_skined_data = None

        result = gltf2_blender_gather_mesh.gather_mesh(blender_mesh,
                                                       library,
                                                       blender_object_for_skined_data,
                                                       vertex_groups,
                                                       modifiers,
                                                       skip_filter,
                                                       material_names,
                                                       export_settings)

    finally:
        if needs_to_mesh_clear:
            blender_mesh_owner.to_mesh_clear()

    return result


def __gather_name(blender_object, export_settings):
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


        if blender_object.matrix_local[3][3] != 0.0:
            trans, rot, sca = blender_object.matrix_local.decompose()
        else:
            # Some really weird cases, scale is null (if parent is null when evaluation is done)
            print_console('WARNING', 'Some nodes are 0 scaled during evaluation. Result can be wrong')
            trans = blender_object.location
            if blender_object.rotation_mode in ['QUATERNION', 'AXIS_ANGLE']:
                rot = blender_object.rotation_quaternion
            else:
                rot = blender_object.rotation_euler.to_quaternion()
            sca = blender_object.scale

    # make sure the rotation is normalized
    rot.normalize()

    trans = __convert_swizzle_location(trans, export_settings)
    rot = __convert_swizzle_rotation(rot, export_settings)
    sca = __convert_swizzle_scale(sca, export_settings)

    if blender_object.instance_type == 'COLLECTION' and blender_object.instance_collection:
        offset = -__convert_swizzle_location(
            blender_object.instance_collection.instance_offset, export_settings)

        s = Matrix.Diagonal(sca).to_4x4()
        r = rot.to_matrix().to_4x4()
        t = Matrix.Translation(trans).to_4x4()
        o = Matrix.Translation(offset).to_4x4()
        m = t @ r @ s @ o

        trans = m.translation

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
    depsgraph = bpy.context.evaluated_depsgraph_get()
    blender_mesh_owner = blender_object.evaluated_get(depsgraph)
    blender_mesh = blender_mesh_owner.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
    if not any(vertex.groups is not None and len(vertex.groups) > 0 for vertex in blender_mesh.vertices):
        return None

    # Prevent infinite recursive error. A mesh can't have an Armature modifier
    # and be bone parented to a bone of this armature
    # In that case, ignore the armature modifier, keep only the bone parenting
    if blender_object.parent is not None \
    and blender_object.parent_type == 'BONE' \
    and blender_object.parent.name == modifiers["ARMATURE"].object.name:

        return None

    # Skins and meshes must be in the same glTF node, which is different from how blender handles armatures
    return gltf2_blender_gather_skins.gather_skin(modifiers["ARMATURE"].object, export_settings)


def __gather_weights(blender_object, export_settings):
    return None


def __get_correction_node(blender_object, export_settings):
    correction_quaternion = __convert_swizzle_rotation(
        Quaternion((1.0, 0.0, 0.0), math.radians(-90.0)), export_settings)
    correction_quaternion = [correction_quaternion[1], correction_quaternion[2],
                             correction_quaternion[3], correction_quaternion[0]]
    return gltf2_io.Node(
        camera=None,
        children=[],
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


def __convert_swizzle_location(loc, export_settings):
    """Convert a location from Blender coordinate system to glTF coordinate system."""
    if export_settings[gltf2_blender_export_keys.YUP]:
        return Vector((loc[0], loc[2], -loc[1]))
    else:
        return Vector((loc[0], loc[1], loc[2]))


def __convert_swizzle_rotation(rot, export_settings):
    """
    Convert a quaternion rotation from Blender coordinate system to glTF coordinate system.

    'w' is still at first position.
    """
    if export_settings[gltf2_blender_export_keys.YUP]:
        return Quaternion((rot[0], rot[1], rot[3], -rot[2]))
    else:
        return Quaternion((rot[0], rot[1], rot[2], rot[3]))


def __convert_swizzle_scale(scale, export_settings):
    """Convert a scale from Blender coordinate system to glTF coordinate system."""
    if export_settings[gltf2_blender_export_keys.YUP]:
        return Vector((scale[0], scale[2], scale[1]))
    else:
        return Vector((scale[0], scale[1], scale[2]))
