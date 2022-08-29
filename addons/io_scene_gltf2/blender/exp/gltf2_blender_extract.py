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

import numpy as np
from mathutils import Vector

from . import gltf2_blender_export_keys
from ...io.com.gltf2_io_debug import print_console
from io_scene_gltf2.blender.exp import gltf2_blender_gather_skins
from io_scene_gltf2.io.com import gltf2_io_constants
from io_scene_gltf2.blender.com import gltf2_blender_conversion


def extract_primitives(blender_mesh, uuid_for_skined_data, blender_vertex_groups, modifiers, export_settings):
    """Extract primitives from a mesh."""
    print_console('INFO', 'Extracting primitive: ' + blender_mesh.name)



    ############################### Prepare ########################################

    blender_object = None
    if uuid_for_skined_data:
        blender_object = export_settings['vtree'].nodes[uuid_for_skined_data].blender_object

    use_normals = export_settings[gltf2_blender_export_keys.NORMALS]
    if use_normals:
        blender_mesh.calc_normals_split()

    use_tangents = False
    if use_normals and export_settings[gltf2_blender_export_keys.TANGENTS]:
        if blender_mesh.uv_layers.active and len(blender_mesh.uv_layers) > 0:
            try:
                blender_mesh.calc_tangents()
                use_tangents = True
            except Exception:
                print_console('WARNING', 'Could not calculate tangents. Please try to triangulate the mesh first.')

    tex_coord_max = 0
    if export_settings[gltf2_blender_export_keys.TEX_COORDS]:
        if blender_mesh.uv_layers.active:
            tex_coord_max = len(blender_mesh.uv_layers)

    use_morph_normals = use_normals and export_settings[gltf2_blender_export_keys.MORPH_NORMAL]
    use_morph_tangents = use_morph_normals and use_tangents and export_settings[gltf2_blender_export_keys.MORPH_TANGENT]

    use_materials = export_settings[gltf2_blender_export_keys.MATERIALS]

    blender_attributes = []

    # Check if we have to export skin
    armature = None
    skin = None
    if blender_vertex_groups and export_settings[gltf2_blender_export_keys.SKINS]:
        if modifiers is not None:
            modifiers_dict = {m.type: m for m in modifiers}
            if "ARMATURE" in modifiers_dict:
                modifier = modifiers_dict["ARMATURE"]
                armature = modifier.object

        # Skin must be ignored if the object is parented to a bone of the armature
        # (This creates an infinite recursive error)
        # So ignoring skin in that case
        is_child_of_arma = (
            armature and
            blender_object and
            blender_object.parent_type == "BONE" and
            blender_object.parent.name == armature.name
        )
        if is_child_of_arma:
            armature = None

        if armature:
            skin = gltf2_blender_gather_skins.gather_skin(export_settings['vtree'].nodes[uuid_for_skined_data].armature, export_settings)
            if not skin:
                armature = None

    key_blocks = []
    if blender_mesh.shape_keys and export_settings[gltf2_blender_export_keys.MORPH]:
        key_blocks = [
            key_block
            for key_block in blender_mesh.shape_keys.key_blocks
            if not (key_block == key_block.relative_key or key_block.mute)
        ]

    # Fetch vert positions and bone data (joint,weights)

    locs, morph_locs = __get_positions(blender_mesh, key_blocks, armature, blender_object, export_settings)

    if skin:
        vert_bones, num_joint_sets, need_neutral_bone = __get_bone_data(blender_mesh, skin, blender_vertex_groups)
        if need_neutral_bone is True:
            # Need to create a fake joint at root of armature
            # In order to assign not assigned vertices to it
            # But for now, this is not yet possible, we need to wait the armature node is created
            # Just store this, to be used later
            armature_uuid = export_settings['vtree'].nodes[uuid_for_skined_data].armature
            export_settings['vtree'].nodes[armature_uuid].need_neutral_bone = True


    # Manage attributes + COLOR_0
    for blender_attribute_index, blender_attribute in enumerate(blender_mesh.attributes):
        attr = {}
        attr['blender_attribute_index'] = blender_attribute_index
        attr['blender_name'] = blender_attribute.name
        attr['blender_domain'] = blender_attribute.domain
        attr['blender_data_type'] = blender_attribute.data_type

        # TODOATTR: For now, we don't export edge data, because I need to find how to 
        # get from edge data to dots data
        if attr['blender_domain'] == "EDGE":
            continue

        # Some type are not exportable (example : String)
        if gltf2_blender_conversion.get_component_type(blender_attribute.data_type) is None or \
            gltf2_blender_conversion.get_data_type(blender_attribute.data_type) is None:

            continue

        if blender_mesh.color_attributes.find(blender_attribute.name) == blender_mesh.color_attributes.render_color_index \
            and blender_mesh.color_attributes.render_color_index != -1:

            if export_settings[gltf2_blender_export_keys.COLORS] is False:
                continue
            attr['gltf_attribute_name'] = 'COLOR_0'
            attr['func_get'] = __get_color_attribute
            attr['func_get_args'] = [blender_mesh, blender_mesh.color_attributes.render_color_index]

        else:
            attr['gltf_attribute_name'] = '_' + blender_attribute.name.upper()
            attr['func_get'] = __get_layer_attribute
            attr['func_get_args'] = [blender_mesh]
            if export_settings['gltf_attributes'] is False:
                continue

        blender_attributes.append(attr)

    # Manage POSITION
    attr = {}
    attr['blender_data_type'] = 'FLOAT_VECTOR'
    attr['blender_domain'] = 'POINT'
    attr['gltf_attribute_name'] = 'POSITION'
    attr['func_set'] = __set_positions_attribute
    attr['func_set_args'] = [locs]
    attr['skip_getting_to_dots'] = True
    blender_attributes.append(attr)

    # Manage uvs TEX_COORD_x
    for tex_coord_i in range(tex_coord_max):
        attr = {}
        attr['blender_data_type'] = 'FLOAT2'
        attr['blender_domain'] = 'CORNER'
        attr['gltf_attribute_name'] = 'TEXCOORD_' + str(tex_coord_i)
        attr['func_get'] = __get_uvs_attribute
        attr['func_get_args'] = [blender_mesh, tex_coord_i]
        blender_attributes.append(attr)

    # Manage NORMALS
    if use_normals:
        attr = {}
        attr['blender_data_type'] = 'FLOAT_VECTOR'
        attr['blender_domain'] = 'CORNER'
        attr['gltf_attribute_name'] = 'NORMAL'
        attr['gltf_attribute_name_morph'] = 'MORPH_NORMAL_'
        attr['func_get'] = __get_normal_attribute
        attr['func_get_args'] = [blender_object, armature, blender_mesh, key_blocks, use_morph_normals, export_settings]
        blender_attributes.append(attr)

    # Manage TANGENT
    if use_tangents:
        attr = {}
        attr['blender_data_type'] = 'FLOAT_VECTOR_4'
        attr['blender_domain'] = 'CORNER'
        attr['gltf_attribute_name'] = 'TANGENT'
        attr['func_get'] = __get_tangent_attribute
        attr['func_get_args'] = [blender_mesh, armature, blender_object, export_settings]
        blender_attributes.append(attr)

    # Manage MORPH_POSITION_x
    for morph_i, vs in enumerate(morph_locs):
        attr = {}
        attr['blender_attribute_index'] = morph_i
        attr['blender_data_type'] = 'FLOAT_VECTOR'
        attr['blender_domain'] = 'POINT'
        attr['gltf_attribute_name'] = 'MORPH_POSITION_' + str(morph_i)
        attr['skip_getting_to_dots'] = True
        attr['func_set'] = __set_morph_locs_attribute
        attr['func_set_args'] = [morph_locs]
        blender_attributes.append(attr)

        # Manage MORPH_NORMAL_x
        if use_morph_normals:
            attr = {}
            attr['blender_attribute_index'] = morph_i
            attr['blender_data_type'] = 'FLOAT_VECTOR'
            attr['blender_domain'] = 'CORNER'
            attr['gltf_attribute_name'] = 'MORPH_NORMAL_' + str(morph_i)
            # No func_get is set here, because data are set from NORMALS
            blender_attributes.append(attr)

            # Manage MORPH_TANGENT_x
            # This is a particular case, where we need to have the following data already calculated
            # - NORMAL
            # - MORPH_NORMAL
            # - TANGENT
            # So, the following needs to be AFTER the 3 others.
            if use_morph_tangents:
                attr = {}
                attr['blender_attribute_index'] = morph_i
                attr['blender_data_type'] = 'FLOAT_VECTOR'
                attr['blender_domain'] = 'CORNER'
                attr['gltf_attribute_name'] = 'MORPH_TANGENT_' + str(morph_i)
                attr['gltf_attribute_name_normal'] = "NORMAL"
                attr['gltf_attribute_name_morph_normal'] = "MORPH_NORMAL_" + str(morph_i)
                attr['gltf_attribute_name_tangent'] = "TANGENT"
                attr['skip_getting_to_dots'] = True
                attr['func_set'] = __set_morph_tangent_attribute
                attr['func_set_args'] = []
                blender_attributes.append(attr)

    for attr in blender_attributes:
        attr['len'] = gltf2_blender_conversion.get_data_length(attr['blender_data_type'])
        attr['type'] = gltf2_blender_conversion.get_numpy_type(attr['blender_data_type'])


    ########################## Create dot data structure #################################################

    # Now that we get all attributes that are going to be exported, create numpy array that will store them
    dot_fields = [('vertex_index', np.uint32)]
    for attr in blender_attributes:
        if 'skip_getting_to_dots' in attr:
            continue
        for i in range(attr['len']):
            dot_fields.append((attr['gltf_attribute_name'] + str(i), attr['type']))

    # In Blender there is both per-vert data, like position, and also per-loop
    # (loop=corner-of-poly) data, like normals or UVs. glTF only has per-vert
    # data, so we need to split Blender verts up into potentially-multiple glTF
    # verts.
    #
    # First, we'll collect a "dot" for every loop: a struct that stores all the
    # attributes at that loop, namely the vertex index (which determines all
    # per-vert data), and all the per-loop data like UVs, etc.
    #
    # Each unique dot will become one unique glTF vert.

    dots = np.empty(len(blender_mesh.loops), dtype=np.dtype(dot_fields))



    ################### Populate dots data #############################################################

    vidxs = np.empty(len(blender_mesh.loops))
    blender_mesh.loops.foreach_get('vertex_index', vidxs)
    dots['vertex_index'] = vidxs
    del vidxs

    for attr in blender_attributes:
        if 'skip_getting_to_dots' in attr:
            continue
        if 'func_get' not in attr:
            continue
        attr['func_get'](*(attr['func_get_args'] + [attr, dots]))




    ############################## Primitive split ##########################################

    # Calculate triangles and sort them into primitives.

    blender_mesh.calc_loop_triangles()
    loop_indices = np.empty(len(blender_mesh.loop_triangles) * 3, dtype=np.uint32)
    blender_mesh.loop_triangles.foreach_get('loops', loop_indices)

    prim_indices = {}  # maps material index to TRIANGLES-style indices into dots

    if use_materials == "NONE": # Only for None. For placeholder and export, keep primitives
        # Put all vertices into one primitive
        prim_indices[-1] = loop_indices

    else:
        # Bucket by material index.

        tri_material_idxs = np.empty(len(blender_mesh.loop_triangles), dtype=np.uint32)
        blender_mesh.loop_triangles.foreach_get('material_index', tri_material_idxs)
        loop_material_idxs = np.repeat(tri_material_idxs, 3)  # material index for every loop
        unique_material_idxs = np.unique(tri_material_idxs)
        del tri_material_idxs

        for material_idx in unique_material_idxs:
            prim_indices[material_idx] = loop_indices[loop_material_idxs == material_idx]

    # Create all the primitives.

    ######################## Create primitives ######################################

    primitives = []

    for material_idx, dot_indices in prim_indices.items():
        # Extract just dots used by this primitive, deduplicate them, and
        # calculate indices into this deduplicated list.
        prim_dots = dots[dot_indices]
        prim_dots, indices = np.unique(prim_dots, return_inverse=True)

        if len(prim_dots) == 0:
            continue

        # Now just move all the data for prim_dots into attribute arrays

        attributes = {}

        blender_idxs = prim_dots['vertex_index']

        for attr in blender_attributes:
            if 'func_set' in attr: # Special function is needed
                attr['func_set'](*attr['func_set_args'] + [attr, attributes, blender_idxs])
            else: # Regular case
                __set_regular_attribute(attr, attributes, prim_dots)
            
        if skin:
            joints = [[] for _ in range(num_joint_sets)]
            weights = [[] for _ in range(num_joint_sets)]

            for vi in blender_idxs:
                bones = vert_bones[vi]
                for j in range(0, 4 * num_joint_sets):
                    if j < len(bones):
                        joint, weight = bones[j]
                    else:
                        joint, weight = 0, 0.0
                    joints[j//4].append(joint)
                    weights[j//4].append(weight)

            for i, (js, ws) in enumerate(zip(joints, weights)):
                attributes['JOINTS_%d' % i] = js
                attributes['WEIGHTS_%d' % i] = ws

        primitives.append({
            'attributes': attributes,
            'indices': indices,
            'material': material_idx
        })

    if export_settings['gltf_loose_edges']:
        # Find loose edges
        loose_edges = [e for e in blender_mesh.edges if e.is_loose]
        blender_idxs = [vi for e in loose_edges for vi in e.vertices]

        if blender_idxs:
            # Export one glTF vert per unique Blender vert in a loose edge
            blender_idxs = np.array(blender_idxs, dtype=np.uint32)
            blender_idxs, indices = np.unique(blender_idxs, return_inverse=True)

            attributes = {}

            for attr in blender_attributes:
                if attr['blender_domain'] != 'POINT':
                    continue
                if 'func_set' in attr:
                    attr['func_set'](*attr['func_set_args'] + [attr, attributes, blender_idxs])
                else:
                    res = np.empty((len(prim_dots), attr['len']), dtype=attr['type'])
                    for i in range(attr['len']):
                        res[:, i] = prim_dots[attr['gltf_attribute_name'] + str(i)]
                    attributes[attr['gltf_attribute_name']] = {}
                    attributes[attr['gltf_attribute_name']]["data"] = res
                    attributes[attr['gltf_attribute_name']]["component_type"] = gltf2_blender_conversion.get_component_type(attr['blender_data_type'])
                    attributes[attr['gltf_attribute_name']]["data_type"] = gltf2_blender_conversion.get_data_type(attr['blender_data_type'])


            if skin:
                joints = [[] for _ in range(num_joint_sets)]
                weights = [[] for _ in range(num_joint_sets)]

                for vi in blender_idxs:
                    bones = vert_bones[vi]
                    for j in range(0, 4 * num_joint_sets):
                        if j < len(bones):
                            joint, weight = bones[j]
                        else:
                            joint, weight = 0, 0.0
                        joints[j//4].append(joint)
                        weights[j//4].append(weight)

                for i, (js, ws) in enumerate(zip(joints, weights)):
                    attributes['JOINTS_%d' % i] = js
                    attributes['WEIGHTS_%d' % i] = ws

            primitives.append({
                'attributes': attributes,
                'indices': indices,
                'mode': 1,  # LINES
                'material': 0
            })

    if export_settings['gltf_loose_points']:
        # Find loose points
        verts_in_edge = set(vi for e in blender_mesh.edges for vi in e.vertices)
        blender_idxs = [
            vi for vi, _ in enumerate(blender_mesh.vertices)
            if vi not in verts_in_edge
        ]

        if blender_idxs:
            blender_idxs = np.array(blender_idxs, dtype=np.uint32)

            attributes = {}

            for attr in blender_attributes:
                if attr['blender_domain'] != 'POINT':
                    continue
                if 'func_set' in attr:
                    attr['func_set'](*attr['func_set_args'] + [attr, attributes, blender_idxs])
                else:
                    res = np.empty((len(prim_dots), attr['len']), dtype=attr['type'])
                    for i in range(attr['len']):
                        res[:, i] = prim_dots[attr['gltf_attribute_name'] + str(i)]
                    attributes[attr['gltf_attribute_name']] = {}
                    attributes[attr['gltf_attribute_name']]["data"] = res
                    attributes[attr['gltf_attribute_name']]["component_type"] = gltf2_blender_conversion.get_component_type(attr['blender_data_type'])
                    attributes[attr['gltf_attribute_name']]["data_type"] = gltf2_blender_conversion.get_data_type(attr['blender_data_type'])


            if skin:
                joints = [[] for _ in range(num_joint_sets)]
                weights = [[] for _ in range(num_joint_sets)]

                for vi in blender_idxs:
                    bones = vert_bones[vi]
                    for j in range(0, 4 * num_joint_sets):
                        if j < len(bones):
                            joint, weight = bones[j]
                        else:
                            joint, weight = 0, 0.0
                        joints[j//4].append(joint)
                        weights[j//4].append(weight)

                for i, (js, ws) in enumerate(zip(joints, weights)):
                    attributes['JOINTS_%d' % i] = js
                    attributes['WEIGHTS_%d' % i] = ws

            primitives.append({
                'attributes': attributes,
                'mode': 0,  # POINTS
                'material': 0
            })

    print_console('INFO', 'Primitives created: %d' % len(primitives))

    return primitives

def __set_regular_attribute(attr, attributes, prim_dots):

    res = np.empty((len(prim_dots), attr['len']), dtype=attr['type'])
    for i in range(attr['len']):
        res[:, i] = prim_dots[attr['gltf_attribute_name'] + str(i)]
    attributes[attr['gltf_attribute_name']] = {}
    attributes[attr['gltf_attribute_name']]["data"] = res
    if 'gltf_attribute_name' == "NORMAL":
        attributes[attr['gltf_attribute_name']]["component_type"] = gltf2_io_constants.ComponentType.Float
        attributes[attr['gltf_attribute_name']]["data_type"] = gltf2_io_constants.DataType.Vec3
    elif 'gltf_attribute_name' == "TANGENT":
        attributes[attr['gltf_attribute_name']]["component_type"] = gltf2_io_constants.ComponentType.Float
        attributes[attr['gltf_attribute_name']]["data_type"] = gltf2_io_constants.DataType.Vec4
    elif attr['gltf_attribute_name'].startswith('TEXCOORD_'):
        attributes[attr['gltf_attribute_name']]["component_type"] = gltf2_io_constants.ComponentType.Float
        attributes[attr['gltf_attribute_name']]["data_type"] = gltf2_io_constants.DataType.Vec2
    else:
        attributes[attr['gltf_attribute_name']]["component_type"] = gltf2_blender_conversion.get_component_type(attr['blender_data_type'])
        attributes[attr['gltf_attribute_name']]["data_type"] = gltf2_blender_conversion.get_data_type(attr['blender_data_type'])


def __set_positions_attribute(locs, attr, attributes, blender_idxs):
    attributes[attr['gltf_attribute_name']] = {}
    attributes[attr['gltf_attribute_name']]["data"] = locs[blender_idxs]
    attributes[attr['gltf_attribute_name']]["data_type"] = gltf2_io_constants.DataType.Vec3
    attributes[attr['gltf_attribute_name']]["component_type"] = gltf2_io_constants.ComponentType.Float


def __set_morph_locs_attribute(morph_locs, attr, attributes, blender_idxs):
    attributes[attr['gltf_attribute_name']] = {}
    attributes[attr['gltf_attribute_name']]["data"] = morph_locs[attr['blender_attribute_index']][blender_idxs]

def __set_morph_tangent_attribute(attr, attributes, blender_idx):
    # Morph tangent are after these 3 others, so, they are already calculated
    normals = attributes[attr['gltf_attribute_name_normal']]["data"]
    morph_normals = attributes[attr['gltf_attribute_name_morph_normal']]["data"]
    tangent = attributes[attr['gltf_attribute_name_tangent']]["data"]

    morph_tangents = __calc_morph_tangents(normals, morph_normals, tangent)
    attributes[attr['gltf_attribute_name']] = {}
    attributes[attr['gltf_attribute_name']]["data"] = morph_tangents

def __get_positions(blender_mesh, key_blocks, armature, blender_object, export_settings):
    locs = np.empty(len(blender_mesh.vertices) * 3, dtype=np.float32)
    source = key_blocks[0].relative_key.data if key_blocks else blender_mesh.vertices
    source.foreach_get('co', locs)
    locs = locs.reshape(len(blender_mesh.vertices), 3)

    morph_locs = []
    for key_block in key_blocks:
        vs = np.empty(len(blender_mesh.vertices) * 3, dtype=np.float32)
        key_block.data.foreach_get('co', vs)
        vs = vs.reshape(len(blender_mesh.vertices), 3)
        morph_locs.append(vs)

    # Transform for skinning
    if armature and blender_object:
        # apply_matrix = armature.matrix_world.inverted_safe() @ blender_object.matrix_world
        # loc_transform = armature.matrix_world @ apply_matrix

        loc_transform = blender_object.matrix_world
        locs[:] = __apply_mat_to_all(loc_transform, locs)
        for vs in morph_locs:
            vs[:] = __apply_mat_to_all(loc_transform, vs)

    # glTF stores deltas in morph targets
    for vs in morph_locs:
        vs -= locs

    if export_settings[gltf2_blender_export_keys.YUP]:
        __zup2yup(locs)
        for vs in morph_locs:
            __zup2yup(vs)

    return locs, morph_locs


def __get_normals(blender_mesh, key_blocks, armature, blender_object, export_settings):
    """Get normal for each loop."""
    if key_blocks:
        normals = key_blocks[0].relative_key.normals_split_get()
        normals = np.array(normals, dtype=np.float32)
    else:
        normals = np.empty(len(blender_mesh.loops) * 3, dtype=np.float32)
        blender_mesh.calc_normals_split()
        blender_mesh.loops.foreach_get('normal', normals)

    normals = normals.reshape(len(blender_mesh.loops), 3)

    morph_normals = []
    for key_block in key_blocks:
        ns = np.array(key_block.normals_split_get(), dtype=np.float32)
        ns = ns.reshape(len(blender_mesh.loops), 3)
        morph_normals.append(ns)

    # Transform for skinning
    if armature and blender_object:
        apply_matrix = (armature.matrix_world.inverted_safe() @ blender_object.matrix_world)
        apply_matrix = apply_matrix.to_3x3().inverted_safe().transposed()
        normal_transform = armature.matrix_world.to_3x3() @ apply_matrix

        normals[:] = __apply_mat_to_all(normal_transform, normals)
        __normalize_vecs(normals)
        for ns in morph_normals:
            ns[:] = __apply_mat_to_all(normal_transform, ns)
            __normalize_vecs(ns)

    for ns in [normals, *morph_normals]:
        # Replace zero normals with the unit UP vector.
        # Seems to happen sometimes with degenerate tris?
        is_zero = ~ns.any(axis=1)
        ns[is_zero, 2] = 1

    # glTF stores deltas in morph targets
    for ns in morph_normals:
        ns -= normals

    if export_settings[gltf2_blender_export_keys.YUP]:
        __zup2yup(normals)
        for ns in morph_normals:
            __zup2yup(ns)

    return normals, morph_normals


def __get_tangents(blender_mesh, armature, blender_object, export_settings):
    """Get an array of the tangent for each loop."""
    tangents = np.empty(len(blender_mesh.loops) * 3, dtype=np.float32)
    blender_mesh.loops.foreach_get('tangent', tangents)
    tangents = tangents.reshape(len(blender_mesh.loops), 3)

    # Transform for skinning
    if armature and blender_object:
        apply_matrix = armature.matrix_world.inverted_safe() @ blender_object.matrix_world
        tangent_transform = apply_matrix.to_quaternion().to_matrix()
        tangents = __apply_mat_to_all(tangent_transform, tangents)
        __normalize_vecs(tangents)

    if export_settings[gltf2_blender_export_keys.YUP]:
        __zup2yup(tangents)

    return tangents


def __get_bitangent_signs(blender_mesh, armature, blender_object, export_settings):
    signs = np.empty(len(blender_mesh.loops), dtype=np.float32)
    blender_mesh.loops.foreach_get('bitangent_sign', signs)

    # Transform for skinning
    if armature and blender_object:
        # Bitangent signs should flip when handedness changes
        # TODO: confirm
        apply_matrix = armature.matrix_world.inverted_safe() @ blender_object.matrix_world
        tangent_transform = apply_matrix.to_quaternion().to_matrix()
        flipped = tangent_transform.determinant() < 0
        if flipped:
            signs *= -1

    # No change for Zup -> Yup

    return signs

def __get_tangent_attribute(blender_mesh, armature, blender_object, export_settings, attr, dots):
    tangents = __get_tangents(blender_mesh, armature, blender_object, export_settings)
    dots[attr['gltf_attribute_name'] + "0"] = tangents[:, 0]
    dots[attr['gltf_attribute_name'] + "1"] = tangents[:, 1]
    dots[attr['gltf_attribute_name'] + "2"] = tangents[:, 2]
    del tangents
    signs = __get_bitangent_signs(blender_mesh, armature, blender_object, export_settings)
    dots[attr['gltf_attribute_name'] + "3"] = signs
    del signs

def __calc_morph_tangents(normals, morph_normal_deltas, tangents):
    # TODO: check if this works
    morph_tangent_deltas = np.empty((len(normals), 3), dtype=np.float32)

    for i in range(len(normals)):
        n = Vector(normals[i])
        morph_n = n + Vector(morph_normal_deltas[i])  # convert back to non-delta
        t = Vector(tangents[i, :3])

        rotation = morph_n.rotation_difference(n)

        t_morph = Vector(t)
        t_morph.rotate(rotation)
        morph_tangent_deltas[i] = t_morph - t  # back to delta

    return morph_tangent_deltas

def __get_uvs_attribute(blender_mesh, blender_uv_idx, attr, dots):
    layer = blender_mesh.uv_layers[blender_uv_idx]
    uvs = np.empty(len(blender_mesh.loops) * 2, dtype=np.float32)
    layer.data.foreach_get('uv', uvs)
    uvs = uvs.reshape(len(blender_mesh.loops), 2)

    # Blender UV space -> glTF UV space
    # u,v -> u,1-v
    uvs[:, 1] *= -1
    uvs[:, 1] += 1

    dots[attr['gltf_attribute_name'] + '0'] = uvs[:, 0]
    dots[attr['gltf_attribute_name'] + '1'] = uvs[:, 1]
    del uvs

def __get_color_attribute(blender_mesh, blender_color_idx, attr, dots):
    if attr['blender_domain'] == "POINT":
        colors = np.empty(len(blender_mesh.vertices) * 4, dtype=np.float32)
    elif attr['blender_domain'] == "CORNER":
        colors = np.empty(len(blender_mesh.loops) * 4, dtype=np.float32)
    blender_mesh.color_attributes[blender_color_idx].data.foreach_get('color', colors)
    if attr['blender_domain'] == "POINT":
        colors = colors.reshape(-1, 4)
        colors = colors[dots['vertex_index']]
    elif attr['blender_domain'] == "CORNER":
        colors = colors.reshape(-1, 4)
    # colors are already linear, no need to switch color space
    dots[attr['gltf_attribute_name'] + '0'] = colors[:, 0]
    dots[attr['gltf_attribute_name'] + '1'] = colors[:, 1]
    dots[attr['gltf_attribute_name'] + '2'] = colors[:, 2]
    dots[attr['gltf_attribute_name'] + '3'] = colors[:, 3]
    del colors

def __get_layer_attribute(blender_mesh, attr, dots):
    if attr['blender_domain'] in ['CORNER']:
        data = np.empty(len(blender_mesh.loops) * attr['len'], dtype=attr['type'])
    elif attr['blender_domain'] in ['POINT']:
        data = np.empty(len(blender_mesh.vertices) * attr['len'], dtype=attr['type'])
    elif attr['blender_domain'] in ['EDGE']:
        data = np.empty(len(blender_mesh.edges) * attr['len'], dtype=attr['type'])
    elif attr['blender_domain'] in ['FACE']:
        data = np.empty(len(blender_mesh.polygons) * attr['len'], dtype=attr['type'])
    else:
        print_console("ERROR", "domain not known")

    if attr['blender_data_type'] == "BYTE_COLOR":
        blender_mesh.attributes[attr['blender_attribute_index']].data.foreach_get('color', data)
        data = data.reshape(-1, attr['len'])
    elif attr['blender_data_type'] == "INT8":
        blender_mesh.attributes[attr['blender_attribute_index']].data.foreach_get('value', data)
        data = data.reshape(-1, attr['len'])
    elif attr['blender_data_type'] == "FLOAT2":
        blender_mesh.attributes[attr['blender_attribute_index']].data.foreach_get('vector', data)
        data = data.reshape(-1, attr['len'])
    elif attr['blender_data_type'] == "BOOLEAN":
        blender_mesh.attributes[attr['blender_attribute_index']].data.foreach_get('value', data)
        data = data.reshape(-1, attr['len'])
    elif attr['blender_data_type'] == "STRING":
        blender_mesh.attributes[attr['blender_attribute_index']].data.foreach_get('value', data)
        data = data.reshape(-1, attr['len'])
    elif attr['blender_data_type'] == "FLOAT_COLOR":
        blender_mesh.attributes[attr['blender_attribute_index']].data.foreach_get('color', data)
        data = data.reshape(-1, attr['len'])
    elif attr['blender_data_type'] == "FLOAT_VECTOR":
        blender_mesh.attributes[attr['blender_attribute_index']].data.foreach_get('vector', data)
        data = data.reshape(-1, attr['len'])
    elif attr['blender_data_type'] == "FLOAT_VECTOR_4": # Specific case for tangent
        pass
    elif attr['blender_data_type'] == "INT":
        blender_mesh.attributes[attr['blender_attribute_index']].data.foreach_get('value', data)
        data = data.reshape(-1, attr['len'])
    elif attr['blender_data_type'] == "FLOAT":
        blender_mesh.attributes[attr['blender_attribute_index']].data.foreach_get('value', data)
        data = data.reshape(-1, attr['len'])
    else:
        print_console('ERROR',"blender type not found " +  attr['blender_data_type'])

    if attr['blender_domain'] in ['CORNER']:
        for i in range(attr['len']):
            dots[attr['gltf_attribute_name'] + str(i)] = data[:, i]
    elif attr['blender_domain'] in ['POINT']:
        if attr['len'] > 1:
            data = data.reshape(-1, attr['len'])
        data = data[dots['vertex_index']]
        for i in range(attr['len']):
            dots[attr['gltf_attribute_name'] + str(i)] = data[:, i]
    elif attr['blender_domain'] in ['EDGE']:
        # edgevidxs = np.array([tuple(edge.vertices) for edge in blender_mesh.edges[:]], dtype="object")
        # TODOATTR need to find how to dispatch edges data to right dots
        pass
    elif attr['blender_domain'] in ['FACE']:
        if attr['len'] > 1:
            data = data.reshape(-1, attr['len'])
        data = data.repeat(4, axis=0)
        for i in range(attr['len']):
            dots[attr['gltf_attribute_name'] + str(i)] = data[:, i]

    else:
        print_console("ERROR", "domain not known")

def __get_normal_attribute(blender_object, armature, blender_mesh, key_blocks, use_morph_normals, export_settings, attr, dots):
    kbs = key_blocks if use_morph_normals else []
    normals, morph_normals = __get_normals(
        blender_mesh, kbs, armature, blender_object, export_settings
    )
    dots[attr['gltf_attribute_name'] + "0"] = normals[:, 0]
    dots[attr['gltf_attribute_name'] + "1"] = normals[:, 1]
    dots[attr['gltf_attribute_name'] + "2"] = normals[:, 2]

    if use_morph_normals:
        for morph_i, ns in enumerate(morph_normals):
            dots[attr['gltf_attribute_name_morph'] + str(morph_i) + "0"] = ns[:, 0]
            dots[attr['gltf_attribute_name_morph'] + str(morph_i) + "1"] = ns[:, 1]
            dots[attr['gltf_attribute_name_morph'] + str(morph_i) + "2"] = ns[:, 2]
        del normals
        del morph_normals

def __get_bone_data(blender_mesh, skin, blender_vertex_groups):

    need_neutral_bone = False
    min_influence = 0.0001

    joint_name_to_index = {joint.name: index for index, joint in enumerate(skin.joints)}
    group_to_joint = [joint_name_to_index.get(g.name) for g in blender_vertex_groups]

    # List of (joint, weight) pairs for each vert
    vert_bones = []
    max_num_influences = 0

    for vertex in blender_mesh.vertices:
        bones = []
        if vertex.groups:
            for group_element in vertex.groups:
                weight = group_element.weight
                if weight <= min_influence:
                    continue
                try:
                    joint = group_to_joint[group_element.group]
                except Exception:
                    continue
                if joint is None:
                    continue
                bones.append((joint, weight))
        bones.sort(key=lambda x: x[1], reverse=True)
        if not bones:
            # Is not assign to any bone
            bones = ((len(skin.joints), 1.0),)  # Assign to a joint that will be created later
            need_neutral_bone = True
        vert_bones.append(bones)
        if len(bones) > max_num_influences:
            max_num_influences = len(bones)

    # How many joint sets do we need? 1 set = 4 influences
    num_joint_sets = (max_num_influences + 3) // 4

    return vert_bones, num_joint_sets, need_neutral_bone


def __zup2yup(array):
    # x,y,z -> x,z,-y
    array[:, [1,2]] = array[:, [2,1]]  # x,z,y
    array[:, 2] *= -1  # x,z,-y


def __apply_mat_to_all(matrix, vectors):
    """Given matrix m and vectors [v1,v2,...], computes [m@v1,m@v2,...]"""
    # Linear part
    m = matrix.to_3x3() if len(matrix) == 4 else matrix
    res = np.matmul(vectors, np.array(m.transposed()))
    # Translation part
    if len(matrix) == 4:
        res += np.array(matrix.translation)
    return res


def __normalize_vecs(vectors):
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    np.divide(vectors, norms, out=vectors, where=norms != 0)
