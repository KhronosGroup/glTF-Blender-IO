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

#
# Imports
#

from mathutils import Vector, Quaternion, Matrix

from . import gltf2_blender_export_keys
from ...io.com.gltf2_io_debug import print_console
from ...io.com.gltf2_io_color_management import color_srgb_to_scene_linear
from io_scene_gltf2.blender.exp import gltf2_blender_gather_skins


#
# Classes
#

class Prim:
    def __init__(self):
        self.verts = {}
        self.indices = []

class ShapeKey:
    def __init__(self, shape_key, split_normals):
        self.shape_key = shape_key
        self.split_normals = split_normals


#
# Functions
#

def convert_swizzle_normal(loc, armature, blender_object, export_settings):
    """Convert a normal data from Blender coordinate system to glTF coordinate system."""
    if (not armature) or (not blender_object):
        # Classic case. Mesh is not skined, no need to apply armature transfoms on vertices / normals / tangents
        if export_settings[gltf2_blender_export_keys.YUP]:
            return Vector((loc[0], loc[2], -loc[1]))
        else:
            return Vector((loc[0], loc[1], loc[2]))
    else:
        # Mesh is skined, we have to apply armature transforms on data
        apply_matrix = (armature.matrix_world.inverted() @ blender_object.matrix_world).to_3x3().inverted()
        apply_matrix.transpose()
        new_loc = ((armature.matrix_world.to_3x3() @ apply_matrix).to_4x4() @ Matrix.Translation(Vector((loc[0], loc[1], loc[2])))).to_translation()
        new_loc.normalize()

        if export_settings[gltf2_blender_export_keys.YUP]:
            return Vector((new_loc[0], new_loc[2], -new_loc[1]))
        else:
            return Vector((new_loc[0], new_loc[1], new_loc[2]))

def convert_swizzle_location(loc, armature, blender_object, export_settings):
    """Convert a location from Blender coordinate system to glTF coordinate system."""
    if (not armature) or (not blender_object):
        # Classic case. Mesh is not skined, no need to apply armature transfoms on vertices / normals / tangents
        if export_settings[gltf2_blender_export_keys.YUP]:
            return Vector((loc[0], loc[2], -loc[1]))
        else:
            return Vector((loc[0], loc[1], loc[2]))
    else:
        # Mesh is skined, we have to apply armature transforms on data
        apply_matrix = armature.matrix_world.inverted() @ blender_object.matrix_world
        new_loc = (armature.matrix_world @ apply_matrix @ Matrix.Translation(Vector((loc[0], loc[1], loc[2])))).to_translation()

        if export_settings[gltf2_blender_export_keys.YUP]:
            return Vector((new_loc[0], new_loc[2], -new_loc[1]))
        else:
            return Vector((new_loc[0], new_loc[1], new_loc[2]))


def convert_swizzle_tangent(tan, armature, blender_object, export_settings):
    """Convert a tangent from Blender coordinate system to glTF coordinate system."""
    if tan[0] == 0.0 and tan[1] == 0.0 and tan[2] == 0.0:
        print_console('WARNING', 'Tangent has zero length.')

    if (not armature) or (not blender_object):
        # Classic case. Mesh is not skined, no need to apply armature transfoms on vertices / normals / tangents
        if export_settings[gltf2_blender_export_keys.YUP]:
            return Vector((tan[0], tan[2], -tan[1]))
        else:
            return Vector((tan[0], tan[1], tan[2]))
    else:
        # Mesh is skined, we have to apply armature transforms on data
        apply_matrix = armature.matrix_world.inverted() @ blender_object.matrix_world
        new_tan = apply_matrix.to_quaternion() @ Vector((tan[0], tan[1], tan[2]))
        if export_settings[gltf2_blender_export_keys.YUP]:
            return Vector((new_tan[0], new_tan[2], -new_tan[1]))
        else:
            return Vector((new_tan[0], new_tan[1], new_tan[2]))

def convert_swizzle_rotation(rot, export_settings):
    """
    Convert a quaternion rotation from Blender coordinate system to glTF coordinate system.

    'w' is still at first position.
    """
    if export_settings[gltf2_blender_export_keys.YUP]:
        return Quaternion((rot[0], rot[1], rot[3], -rot[2]))
    else:
        return Quaternion((rot[0], rot[1], rot[2], rot[3]))


def convert_swizzle_scale(scale, export_settings):
    """Convert a scale from Blender coordinate system to glTF coordinate system."""
    if export_settings[gltf2_blender_export_keys.YUP]:
        return Vector((scale[0], scale[2], scale[1]))
    else:
        return Vector((scale[0], scale[1], scale[2]))


def extract_primitives(glTF, blender_mesh, library, blender_object, blender_vertex_groups, modifiers, export_settings):
    """
    Extract primitives from a mesh. Polygons are triangulated and sorted by material.
    Vertices in multiple faces get split up as necessary.
    """
    print_console('INFO', 'Extracting primitive: ' + blender_mesh.name)

    #
    # First, decide what attributes to gather (eg. how many COLOR_n, etc.)
    # Also calculate normals/tangents now if necessary.
    #

    use_normals = export_settings[gltf2_blender_export_keys.NORMALS]
    if use_normals:
        if blender_mesh.has_custom_normals:
            # Custom normals are all (0, 0, 0) until calling calc_normals_split() or calc_tangents().
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

    color_max = 0
    if export_settings[gltf2_blender_export_keys.COLORS]:
        color_max = len(blender_mesh.vertex_colors)

    bone_max = 0  # number of JOINTS_n sets needed (1 set = 4 influences)
    armature = None
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
            skin = gltf2_blender_gather_skins.gather_skin(armature, export_settings)
            if not skin:
                armature = None
            else:
                joint_name_to_index = {joint.name: index for index, joint in enumerate(skin.joints)}
                group_to_joint = [joint_name_to_index.get(g.name) for g in blender_vertex_groups]

                # Find out max number of bone influences
                for blender_polygon in blender_mesh.polygons:
                    for loop_index in blender_polygon.loop_indices:
                        vertex_index = blender_mesh.loops[loop_index].vertex_index
                        groups_count = len(blender_mesh.vertices[vertex_index].groups)
                        bones_count = (groups_count + 3) // 4
                        bone_max = max(bone_max, bones_count)

    use_morph_normals = use_normals and export_settings[gltf2_blender_export_keys.MORPH_NORMAL]
    use_morph_tangents = use_morph_normals and use_tangents and export_settings[gltf2_blender_export_keys.MORPH_TANGENT]

    shape_keys = []
    if blender_mesh.shape_keys and export_settings[gltf2_blender_export_keys.MORPH]:
        for blender_shape_key in blender_mesh.shape_keys.key_blocks:
            if blender_shape_key == blender_shape_key.relative_key or blender_shape_key.mute:
                continue

            split_normals = None
            if use_morph_normals:
                split_normals = blender_shape_key.normals_split_get()

            shape_keys.append(ShapeKey(
                blender_shape_key,
                split_normals,
            ))


    use_materials = export_settings[gltf2_blender_export_keys.MATERIALS]

    #
    # Gather the verts and indices for each primitive.
    #

    prims = {}

    blender_mesh.calc_loop_triangles()

    for loop_tri in blender_mesh.loop_triangles:
        blender_polygon = blender_mesh.polygons[loop_tri.polygon_index]

        material_idx = -1
        if use_materials:
            material_idx = blender_polygon.material_index

        prim = prims.get(material_idx)
        if not prim:
            prim = Prim()
            prims[material_idx] = prim

        if use_normals:
            face_normal = None
            if not (blender_polygon.use_smooth or blender_mesh.use_auto_smooth):
                # Calc face normal/tangents
                face_normal = blender_polygon.normal
                if use_tangents:
                    face_tangent = Vector((0.0, 0.0, 0.0))
                    face_bitangent = Vector((0.0, 0.0, 0.0))
                    for loop_index in blender_polygon.loop_indices:
                        loop = blender_mesh.loops[loop_index]
                        face_tangent += loop.tangent
                        face_bitangent += loop.bitangent
                    face_tangent.normalize()
                    face_bitangent.normalize()

        for loop_index in loop_tri.loops:
            vertex_index = blender_mesh.loops[loop_index].vertex_index
            vertex = blender_mesh.vertices[vertex_index]

            # vert will be a tuple of all the vertex attributes.
            # Used as cache key in prim.verts.
            vert = (vertex_index,)

            v = vertex.co
            vert += ((v[0], v[1], v[2]),)

            if use_normals:
                if face_normal is None:
                    if blender_mesh.has_custom_normals:
                        n = blender_mesh.loops[loop_index].normal
                    else:
                        n = vertex.normal
                    if use_tangents:
                        t = blender_mesh.loops[loop_index].tangent
                        b = blender_mesh.loops[loop_index].bitangent
                else:
                    n = face_normal
                    if use_tangents:
                        t = face_tangent
                        b = face_bitangent
                vert += ((n[0], n[1], n[2]),)
                if use_tangents:
                    vert += ((t[0], t[1], t[2]),)
                    vert += ((b[0], b[1], b[2]),)
                    # TODO: store just bitangent_sign in vert, not whole bitangent?

            for tex_coord_index in range(0, tex_coord_max):
                uv = blender_mesh.uv_layers[tex_coord_index].data[loop_index].uv
                uv = (uv.x, 1.0 - uv.y)
                vert += (uv,)

            for color_index in range(0, color_max):
                color = blender_mesh.vertex_colors[color_index].data[loop_index].color
                col = (
                    color_srgb_to_scene_linear(color[0]),
                    color_srgb_to_scene_linear(color[1]),
                    color_srgb_to_scene_linear(color[2]),
                    color[3],
                )
                vert += (col,)

            if bone_max:
                bones = []
                if vertex.groups:
                    for group_element in vertex.groups:
                        weight = group_element.weight
                        if weight <= 0.0:
                            continue
                        try:
                            joint = group_to_joint[group_element.group]
                        except Exception:
                            continue
                        if joint is None:
                            continue
                        bones.append((joint, weight))
                bones.sort(key=lambda x: x[1], reverse=True)
                bones = tuple(bones)
                vert += (bones,)

            for shape_key in shape_keys:
                v_morph = shape_key.shape_key.data[vertex_index].co
                v_morph = v_morph - v  # store delta
                vert += ((v_morph[0], v_morph[1], v_morph[2]),)

                if use_morph_normals:
                    normals = shape_key.split_normals
                    n_morph = Vector(normals[loop_index * 3 : loop_index * 3 + 3])
                    n_morph = n_morph - n  # store delta
                    vert += ((n_morph[0], n_morph[1], n_morph[2]),)

            vert_idx = prim.verts.setdefault(vert, len(prim.verts))
            prim.indices.append(vert_idx)

    #
    # Put the verts into attribute arrays.
    #

    result_primitives = []

    for material_idx, prim in prims.items():
        if not prim.indices:
            continue

        vs = []
        ns = []
        ts = []
        uvs = [[] for _ in range(tex_coord_max)]
        cols = [[] for _ in range(color_max)]
        joints = [[] for _ in range(bone_max)]
        weights = [[] for _ in range(bone_max)]
        vs_morph = [[] for _ in shape_keys]
        ns_morph = [[] for _ in shape_keys]
        ts_morph = [[] for _ in shape_keys]

        for vert in prim.verts.keys():
            i = 0

            i += 1  # skip over Blender mesh index

            v = vert[i]
            i += 1
            v = convert_swizzle_location(v, armature, blender_object, export_settings)
            vs.extend(v)

            if use_normals:
                n = vert[i]
                i += 1
                n = convert_swizzle_normal(n, armature, blender_object, export_settings)
                ns.extend(n)

                if use_tangents:
                    t = vert[i]
                    i += 1
                    t = convert_swizzle_tangent(t, armature, blender_object, export_settings)
                    ts.extend(t)

                    b = vert[i]
                    i += 1
                    b = convert_swizzle_tangent(b, armature, blender_object, export_settings)
                    b_sign = -1.0 if (Vector(n).cross(Vector(t))).dot(Vector(b)) < 0.0 else 1.0
                    ts.append(b_sign)

            for tex_coord_index in range(0, tex_coord_max):
                uv = vert[i]
                i += 1
                uvs[tex_coord_index].extend(uv)

            for color_index in range(0, color_max):
                col = vert[i]
                i += 1
                cols[color_index].extend(col)

            if bone_max:
                bones = vert[i]
                i += 1
                for j in range(0, 4 * bone_max):
                    if j < len(bones):
                        joint, weight = bones[j]
                    else:
                        joint, weight = 0, 0.0
                    joints[j//4].append(joint)
                    weights[j//4].append(weight)

            for shape_key_index in range(0, len(shape_keys)):
                v_morph = vert[i]
                i += 1
                v_morph = convert_swizzle_location(v_morph, armature, blender_object, export_settings)
                vs_morph[shape_key_index].extend(v_morph)

                if use_morph_normals:
                    n_morph = vert[i]
                    i += 1
                    n_morph = convert_swizzle_normal(n_morph, armature, blender_object, export_settings)
                    ns_morph[shape_key_index].extend(n_morph)

                if use_morph_tangents:
                    rotation = n_morph.rotation_difference(n)
                    t_morph = Vector(t)
                    t_morph.rotate(rotation)
                    ts_morph[shape_key_index].extend(t_morph)

        attributes = {}
        attributes['POSITION'] = vs
        if ns: attributes['NORMAL'] = ns
        if ts: attributes['TANGENT'] = ts
        for i, uv in enumerate(uvs): attributes['TEXCOORD_%d' % i] = uv
        for i, col in enumerate(cols): attributes['COLOR_%d' % i] = col
        for i, js in enumerate(joints): attributes['JOINTS_%d' % i] = js
        for i, ws in enumerate(weights): attributes['WEIGHTS_%d' % i] = ws
        for i, vm in enumerate(vs_morph): attributes['MORPH_POSITION_%d' % i] = vm
        for i, nm in enumerate(ns_morph): attributes['MORPH_NORMAL_%d' % i] = nm
        for i, tm in enumerate(ts_morph): attributes['MORPH_TANGENT_%d' % i] = tm

        result_primitives.append({
            'attributes': attributes,
            'indices': prim.indices,
            'material': material_idx,
        })

    print_console('INFO', 'Primitives created: %d' % len(result_primitives))

    return result_primitives
