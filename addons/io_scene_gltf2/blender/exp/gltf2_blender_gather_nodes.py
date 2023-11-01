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

from ...io.com.gltf2_io_debug import print_console
from ...io.com import gltf2_io
from ...io.com import gltf2_io_extensions
from ...io.exp.gltf2_io_user_extensions import export_user_extensions
from ..com.gltf2_blender_extras import generate_extras
from ..com import gltf2_blender_math
from . import gltf2_blender_gather_tree
from . import gltf2_blender_gather_skins
from . import gltf2_blender_gather_cameras
from . import gltf2_blender_gather_mesh
from . import gltf2_blender_gather_joints
from . import gltf2_blender_gather_lights
from .gltf2_blender_gather_tree import VExportNode

def gather_node(vnode, export_settings):

    blender_object = vnode.blender_object

    skin = gather_skin(vnode.uuid, export_settings)
    if skin is not None:
        vnode.skin = skin

    node = gltf2_io.Node(
        camera=__gather_camera(blender_object, export_settings),
        children=__gather_children(vnode, export_settings),
        extensions=__gather_extensions(blender_object, export_settings),
        extras=__gather_extras(blender_object, export_settings),
        matrix=__gather_matrix(blender_object, export_settings),
        mesh=__gather_mesh(vnode, blender_object, export_settings),
        name=__gather_name(blender_object, export_settings),
        rotation=None,
        scale=None,
        skin=skin,
        translation=None,
        weights=__gather_weights(blender_object, export_settings)
    )

    # If node mesh is skined, transforms should be ignored at import, so no need to set them here
    if node.skin is None:
        node.translation, node.rotation, node.scale = __gather_trans_rot_scale(vnode, export_settings)


    export_user_extensions('gather_node_hook', export_settings, node, blender_object)

    vnode.node = node

    return node


def __gather_camera(blender_object, export_settings):
    if blender_object.type != 'CAMERA':
        return None

    return gltf2_blender_gather_cameras.gather_camera(blender_object.data, export_settings)


def __gather_children(vnode, export_settings):
    children = []

    vtree = export_settings['vtree']


    armature_object_uuid = None

    # Standard Children / Collection
    if export_settings['gltf_armature_object_remove'] is False:
        for c in [vtree.nodes[c] for c in vnode.children if vtree.nodes[c].blender_type != gltf2_blender_gather_tree.VExportNode.BONE]:
            node = gather_node(c, export_settings)
            if node is not None:
                children.append(node)
    else:
        root_joints = []
        for c in [vtree.nodes[c] for c in vnode.children]:
            if c.blender_type != gltf2_blender_gather_tree.VExportNode.BONE:
                node = gather_node(c, export_settings)
                if node is not None:
                    children.append(node)
            else:
                # We come here because armature was remove, and bone can be a child of any object
                joint = gltf2_blender_gather_joints.gather_joint_vnode(c.uuid, export_settings)
                children.append(joint)
                armature_object_uuid = c.armature
                root_joints.append(joint)

    # Now got all bone children (that are root joints), we can get object parented to bones

    # Armature --> Retrieve Blender bones
    # This can't happen if we remove the Armature Object
    if vnode.blender_type == gltf2_blender_gather_tree.VExportNode.ARMATURE:
        armature_object_uuid = vnode.uuid
        root_joints = []
        root_bones_uuid = export_settings['vtree'].get_root_bones_uuid(vnode.uuid)
        for bone_uuid in root_bones_uuid:
            joint = gltf2_blender_gather_joints.gather_joint_vnode(bone_uuid, export_settings)
            children.append(joint)
            root_joints.append(joint)


    if vnode.blender_type == gltf2_blender_gather_tree.VExportNode.ARMATURE \
            or armature_object_uuid is not None:

        # Object parented to bones
        get_objects_parented_to_bones(armature_object_uuid, root_joints, export_settings)

    return children

def get_objects_parented_to_bones(armature_object_uuid, root_joints, export_settings):
    vtree = export_settings['vtree']
    direct_bone_children = []
    for n in [vtree.nodes[i] for i in vtree.get_all_bones(armature_object_uuid)]:
        direct_bone_children.extend([c for c in n.children if vtree.nodes[c].blender_type != gltf2_blender_gather_tree.VExportNode.BONE])

    for child in direct_bone_children: # List of object that are parented to bones
        # find parent joint
        parent_joint = __find_parent_joint(root_joints, vtree.nodes[child].blender_object.parent_bone)
        if not parent_joint:
            continue
        child_node = gather_node(vtree.nodes[child], export_settings)
        if child_node is None:
            continue

        mat = vtree.nodes[vtree.nodes[child].parent_bone_uuid].matrix_world.inverted_safe() @ vtree.nodes[child].matrix_world
        loc, rot_quat, scale = mat.decompose()

        trans = __convert_swizzle_location(loc, export_settings)
        rot = __convert_swizzle_rotation(rot_quat, export_settings)
        sca = __convert_swizzle_scale(scale, export_settings)


        translation, rotation, scale = (None, None, None)
        if trans[0] != 0.0 or trans[1] != 0.0 or trans[2] != 0.0:
            translation = [trans[0], trans[1], trans[2]]
        if rot[0] != 1.0 or rot[1] != 0.0 or rot[2] != 0.0 or rot[3] != 0.0:
            rotation = [rot[1], rot[2], rot[3], rot[0]]
        if sca[0] != 1.0 or sca[1] != 1.0 or sca[2] != 1.0:
            scale = [sca[0], sca[1], sca[2]]

        child_node.translation = translation
        child_node.rotation = rotation
        child_node.scale = scale

        parent_joint.children.append(child_node)


def __find_parent_joint(joints, name):
    for joint in joints:
        if joint.name == name:
            return joint
        parent_joint = __find_parent_joint(joint.children, name)
        if parent_joint:
            return parent_joint
    return None


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
        return generate_extras(blender_object, export_settings)
    return None


def __gather_matrix(blender_object, export_settings):
    # return blender_object.matrix_local
    return []


def __gather_mesh(vnode, blender_object, export_settings):
    if blender_object.type in ['CURVE', 'SURFACE', 'FONT']:
        return __gather_mesh_from_nonmesh(blender_object, export_settings)

    if blender_object.type != "MESH":
        return None

    # For duplis instancer, when show is off -> export as empty
    if vnode.force_as_empty is True:
        return None

    # Be sure that object is valid (no NaN for example)
    res = blender_object.data.validate()
    if res is True:
        print_console("WARNING", "Mesh " + blender_object.data.name + " is not valid, and may be exported wrongly")

    modifiers = blender_object.modifiers
    if len(modifiers) == 0:
        modifiers = None


    if export_settings['gltf_apply']:
        if modifiers is None: # If no modifier, use original mesh, it will instance all shared mesh in a single glTF mesh
            blender_mesh = blender_object.data
            # Keep materials from object, as no modifiers are applied, so no risk that
            # modifiers changed them
            materials = tuple(ms.material for ms in blender_object.material_slots)
        else:
            armature_modifiers = {}
            if export_settings['gltf_skins']:
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

            if export_settings['gltf_skins']:
                # restore Armature modifiers
                for idx, show_viewport in armature_modifiers.items():
                    blender_object.modifiers[idx].show_viewport = show_viewport

            # Keep materials from the newly created tmp mesh
            materials = tuple(mat for mat in blender_mesh.materials)
            if len(materials) == 1 and materials[0] is None:
                    materials = tuple(ms.material for ms in blender_object.material_slots)
    else:
        blender_mesh = blender_object.data
        # If no skin are exported, no need to have vertex group, this will create a cache miss
        if not export_settings['gltf_skins']:
            modifiers = None
        else:
            # Check if there is an armature modidier
            if len([mod for mod in blender_object.modifiers if mod.type == "ARMATURE"]) == 0:
                modifiers = None
        # Keep materials from object, as no modifiers are applied, so no risk that
        # modifiers changed them
        materials = tuple(ms.material for ms in blender_object.material_slots)

    # retrieve armature
    # Because mesh data will be transforms to skeleton space,
    # we can't instantiate multiple object at different location, skined by same armature
    uuid_for_skined_data = None
    if export_settings['gltf_skins']:
        for idx, modifier in enumerate(blender_object.modifiers):
            if modifier.type == 'ARMATURE':
                uuid_for_skined_data = vnode.uuid

    result = gltf2_blender_gather_mesh.gather_mesh(blender_mesh,
                                                   uuid_for_skined_data,
                                                   blender_object.vertex_groups,
                                                   modifiers,
                                                   materials,
                                                   None,
                                                   export_settings)

    if export_settings['gltf_apply'] and modifiers is not None:
        blender_mesh_owner.to_mesh_clear()

    return result


def __gather_mesh_from_nonmesh(blender_object, export_settings):
    """Handles curves, surfaces, text, etc."""
    needs_to_mesh_clear = False
    try:
        # Convert to a mesh
        try:
            if export_settings['gltf_apply']:
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

        materials = tuple([ms.material for ms in blender_object.material_slots if ms.material is not None])
        modifiers = None
        blender_object_for_skined_data = None

        result = gltf2_blender_gather_mesh.gather_mesh(blender_mesh,
                                                       blender_object_for_skined_data,
                                                       blender_object.vertex_groups,
                                                       modifiers,
                                                       materials,
                                                       blender_object.data,
                                                       export_settings)

    finally:
        if needs_to_mesh_clear:
            blender_mesh_owner.to_mesh_clear()

    return result


def __gather_name(blender_object, export_settings):

    class GltfHookName:
        def __init__(self, name):
            self.name = name
    gltf_hook_name = GltfHookName(blender_object.name)

    export_user_extensions('gather_node_name_hook', export_settings, gltf_hook_name, blender_object)
    return gltf_hook_name.name

def __gather_trans_rot_scale(vnode, export_settings):
    if vnode.parent_uuid is None:
        # No parent, so matrix is world matrix
        trans, rot, sca = vnode.matrix_world.decompose()
    else:
        # calculate local matrix
        if export_settings['vtree'].nodes[vnode.parent_uuid].skin is None:
            trans, rot, sca = (export_settings['vtree'].nodes[vnode.parent_uuid].matrix_world.inverted_safe() @ vnode.matrix_world).decompose()
        else:
            # But ... if parent has skin, the parent TRS are not taken into account, so don't get local from parent, but from armature
            # It also depens if skined mesh is parented to armature or not
            if export_settings['vtree'].nodes[vnode.parent_uuid].parent_uuid is not None and export_settings['vtree'].nodes[export_settings['vtree'].nodes[vnode.parent_uuid].parent_uuid].blender_type == VExportNode.ARMATURE:
                trans, rot, sca = (export_settings['vtree'].nodes[export_settings['vtree'].nodes[vnode.parent_uuid].armature].matrix_world.inverted_safe() @ vnode.matrix_world).decompose()
            else:
                trans, rot, sca = vnode.matrix_world.decompose()

    # make sure the rotation is normalized
    rot.normalize()

    trans = __convert_swizzle_location(trans, export_settings)
    rot = __convert_swizzle_rotation(rot, export_settings)
    sca = __convert_swizzle_scale(sca, export_settings)

    if vnode.blender_object.instance_type == 'COLLECTION' and vnode.blender_object.instance_collection:
        offset = -__convert_swizzle_location(
            vnode.blender_object.instance_collection.instance_offset, export_settings)

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

def gather_skin(vnode, export_settings):
    blender_object = export_settings['vtree'].nodes[vnode].blender_object
    modifiers = {m.type: m for m in blender_object.modifiers}
    if "ARMATURE" not in modifiers or modifiers["ARMATURE"].object is None:
        return None

    # no skin needed when the modifier is linked without having a vertex group
    if len(blender_object.vertex_groups) == 0:
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
    return gltf2_blender_gather_skins.gather_skin(export_settings['vtree'].nodes[vnode].armature, export_settings)


def __gather_weights(blender_object, export_settings):
    return None

def __convert_swizzle_location(loc, export_settings):
    """Convert a location from Blender coordinate system to glTF coordinate system."""
    if export_settings['gltf_yup']:
        return Vector((loc[0], loc[2], -loc[1]))
    else:
        return Vector((loc[0], loc[1], loc[2]))


def __convert_swizzle_rotation(rot, export_settings):
    """
    Convert a quaternion rotation from Blender coordinate system to glTF coordinate system.

    'w' is still at first position.
    """
    if export_settings['gltf_yup']:
        return Quaternion((rot[0], rot[1], rot[3], -rot[2]))
    else:
        return Quaternion((rot[0], rot[1], rot[2], rot[3]))


def __convert_swizzle_scale(scale, export_settings):
    """Convert a scale from Blender coordinate system to glTF coordinate system."""
    if export_settings['gltf_yup']:
        return Vector((scale[0], scale[2], scale[1]))
    else:
        return Vector((scale[0], scale[1], scale[2]))
