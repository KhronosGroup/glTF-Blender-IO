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
from mathutils.geometry import tessellate_polygon
from operator import attrgetter

from . import gltf2_blender_export_keys
from ...io.com.gltf2_io_debug import print_console
from ...io.com.gltf2_io_color_management import color_srgb_to_scene_linear
from io_scene_gltf2.blender.exp import gltf2_blender_gather_skins
import bpy

#
# Globals
#

INDICES_ID = 'indices'
MATERIAL_ID = 'material'
ATTRIBUTES_ID = 'attributes'

COLOR_PREFIX = 'COLOR_'
MORPH_TANGENT_PREFIX = 'MORPH_TANGENT_'
MORPH_NORMAL_PREFIX = 'MORPH_NORMAL_'
MORPH_POSITION_PREFIX = 'MORPH_POSITION_'
TEXCOORD_PREFIX = 'TEXCOORD_'
WEIGHTS_PREFIX = 'WEIGHTS_'
JOINTS_PREFIX = 'JOINTS_'

TANGENT_ATTRIBUTE = 'TANGENT'
NORMAL_ATTRIBUTE = 'NORMAL'
POSITION_ATTRIBUTE = 'POSITION'

GLTF_MAX_COLORS = 2


#
# Classes
#

class ShapeKey:
    def __init__(self, shape_key, vertex_normals, polygon_normals):
        self.shape_key = shape_key
        self.vertex_normals = vertex_normals
        self.polygon_normals = polygon_normals


#
# Functions
#

def convert_swizzle_normal_and_tangent(loc, armature, blender_object, export_settings):
    """Convert a normal data from Blender coordinate system to glTF coordinate system."""
    if not armature:
        # Classic case. Mesh is not skined, no need to apply armature transfoms on vertices / normals / tangents
        if export_settings[gltf2_blender_export_keys.YUP]:
            return Vector((loc[0], loc[2], -loc[1]))
        else:
            return Vector((loc[0], loc[1], loc[2]))
    else:
        # Mesh is skined, we have to apply armature transforms on data
        if bpy.app.version < (2, 80, 0):
            apply_matrix = armature.matrix_world.inverted() * blender_object.matrix_world
            new_loc = (armature.matrix_world * apply_matrix * Matrix.Translation(Vector((loc[0], loc[1], loc[2])))).to_translation()
        else:
            apply_matrix = armature.matrix_world.inverted() @ blender_object.matrix_world
            new_loc = apply_matrix.to_quaternion() @ loc
        if export_settings[gltf2_blender_export_keys.YUP]:
            return Vector((new_loc[0], new_loc[2], -new_loc[1]))
        else:
            return Vector((new_loc[0], new_loc[1], new_loc[2]))

def convert_swizzle_location(loc, armature, blender_object, export_settings):
    """Convert a location from Blender coordinate system to glTF coordinate system."""
    if not armature:
        # Classic case. Mesh is not skined, no need to apply armature transfoms on vertices / normals / tangents
        if export_settings[gltf2_blender_export_keys.YUP]:
            return Vector((loc[0], loc[2], -loc[1]))
        else:
            return Vector((loc[0], loc[1], loc[2]))
    else:
        # Mesh is skined, we have to apply armature transforms on data
        if bpy.app.version < (2, 80, 0):
            apply_matrix = armature.matrix_world.inverted() * blender_object.matrix_world
            new_loc = (armature.matrix_world * apply_matrix * Matrix.Translation(Vector((loc[0], loc[1], loc[2])))).to_translation()
        else:
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

    if not armature:
        # Classic case. Mesh is not skined, no need to apply armature transfoms on vertices / normals / tangents
        if export_settings[gltf2_blender_export_keys.YUP]:
            return Vector((tan[0], tan[2], -tan[1], 1.0))
        else:
            return Vector((tan[0], tan[1], tan[2], 1.0))
    else:
        # Mesh is skined, we have to apply armature transforms on data
        if bpy.app.version < (2, 80, 0):
            apply_matrix = armature.matrix_world.inverted() * blender_object.matrix_world
            new_tan = (armature.matrix_world * apply_matrix * Matrix.Translation(Vector((tan[0], tan[1], tan[2])))).to_translation()
        else:
            apply_matrix = armature.matrix_world.inverted() @ blender_object.matrix_world
            new_tan = apply_matrix.to_quaternion() @ tan
        if export_settings[gltf2_blender_export_keys.YUP]:
            return Vector((new_tan[0], new_tan[2], -new_tan[1], 1.0))
        else:
            return Vector((new_tan[0], new_tan[1], new_tan[2], 1.0))

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


def decompose_transition(matrix, export_settings):
    translation, rotation, scale = matrix.decompose()

    return translation, rotation, scale

def extract_primitive_floor(a, indices, use_tangents):
    """Shift indices, that the first one starts with 0. It is assumed, that the indices are packed."""
    attributes = {
        POSITION_ATTRIBUTE: [],
        NORMAL_ATTRIBUTE: []
    }

    if use_tangents:
        attributes[TANGENT_ATTRIBUTE] = []

    result_primitive = {
        MATERIAL_ID: a[MATERIAL_ID],
        INDICES_ID: [],
        ATTRIBUTES_ID: attributes
    }

    source_attributes = a[ATTRIBUTES_ID]

    #

    tex_coord_index = 0
    process_tex_coord = True
    while process_tex_coord:
        tex_coord_id = TEXCOORD_PREFIX + str(tex_coord_index)

        if source_attributes.get(tex_coord_id) is not None:
            attributes[tex_coord_id] = []
            tex_coord_index += 1
        else:
            process_tex_coord = False

    tex_coord_max = tex_coord_index

    #

    color_index = 0
    process_color = True
    while process_color:
        color_id = COLOR_PREFIX + str(color_index)

        if source_attributes.get(color_id) is not None:
            attributes[color_id] = []
            color_index += 1
        else:
            process_color = False

    color_max = color_index

    #

    bone_index = 0
    process_bone = True
    while process_bone:
        joint_id = JOINTS_PREFIX + str(bone_index)
        weight_id = WEIGHTS_PREFIX + str(bone_index)

        if source_attributes.get(joint_id) is not None:
            attributes[joint_id] = []
            attributes[weight_id] = []
            bone_index += 1
        else:
            process_bone = False

    bone_max = bone_index

    #

    morph_index = 0
    process_morph = True
    while process_morph:
        morph_position_id = MORPH_POSITION_PREFIX + str(morph_index)
        morph_normal_id = MORPH_NORMAL_PREFIX + str(morph_index)
        morph_tangent_id = MORPH_TANGENT_PREFIX + str(morph_index)

        if source_attributes.get(morph_position_id) is not None:
            attributes[morph_position_id] = []
            attributes[morph_normal_id] = []
            if use_tangents:
                attributes[morph_tangent_id] = []
            morph_index += 1
        else:
            process_morph = False

    morph_max = morph_index

    #

    min_index = min(indices)
    max_index = max(indices)

    for old_index in indices:
        result_primitive[INDICES_ID].append(old_index - min_index)

    for old_index in range(min_index, max_index + 1):
        for vi in range(0, 3):
            attributes[POSITION_ATTRIBUTE].append(source_attributes[POSITION_ATTRIBUTE][old_index * 3 + vi])
            attributes[NORMAL_ATTRIBUTE].append(source_attributes[NORMAL_ATTRIBUTE][old_index * 3 + vi])

        if use_tangents:
            for vi in range(0, 4):
                attributes[TANGENT_ATTRIBUTE].append(source_attributes[TANGENT_ATTRIBUTE][old_index * 4 + vi])

        for tex_coord_index in range(0, tex_coord_max):
            tex_coord_id = TEXCOORD_PREFIX + str(tex_coord_index)
            for vi in range(0, 2):
                attributes[tex_coord_id].append(source_attributes[tex_coord_id][old_index * 2 + vi])

        for color_index in range(0, color_max):
            color_id = COLOR_PREFIX + str(color_index)
            for vi in range(0, 4):
                attributes[color_id].append(source_attributes[color_id][old_index * 4 + vi])

        for bone_index in range(0, bone_max):
            joint_id = JOINTS_PREFIX + str(bone_index)
            weight_id = WEIGHTS_PREFIX + str(bone_index)
            for vi in range(0, 4):
                attributes[joint_id].append(source_attributes[joint_id][old_index * 4 + vi])
                attributes[weight_id].append(source_attributes[weight_id][old_index * 4 + vi])

        for morph_index in range(0, morph_max):
            morph_position_id = MORPH_POSITION_PREFIX + str(morph_index)
            morph_normal_id = MORPH_NORMAL_PREFIX + str(morph_index)
            morph_tangent_id = MORPH_TANGENT_PREFIX + str(morph_index)
            for vi in range(0, 3):
                attributes[morph_position_id].append(source_attributes[morph_position_id][old_index * 3 + vi])
                attributes[morph_normal_id].append(source_attributes[morph_normal_id][old_index * 3 + vi])
            if use_tangents:
                for vi in range(0, 4):
                    attributes[morph_tangent_id].append(source_attributes[morph_tangent_id][old_index * 4 + vi])

    return result_primitive


def extract_primitive_pack(a, indices, use_tangents):
    """Pack indices, that the first one starts with 0. Current indices can have gaps."""
    attributes = {
        POSITION_ATTRIBUTE: [],
        NORMAL_ATTRIBUTE: []
    }

    if use_tangents:
        attributes[TANGENT_ATTRIBUTE] = []

    result_primitive = {
        MATERIAL_ID: a[MATERIAL_ID],
        INDICES_ID: [],
        ATTRIBUTES_ID: attributes
    }

    source_attributes = a[ATTRIBUTES_ID]

    #

    tex_coord_index = 0
    process_tex_coord = True
    while process_tex_coord:
        tex_coord_id = TEXCOORD_PREFIX + str(tex_coord_index)

        if source_attributes.get(tex_coord_id) is not None:
            attributes[tex_coord_id] = []
            tex_coord_index += 1
        else:
            process_tex_coord = False

    tex_coord_max = tex_coord_index

    #

    color_index = 0
    process_color = True
    while process_color:
        color_id = COLOR_PREFIX + str(color_index)

        if source_attributes.get(color_id) is not None:
            attributes[color_id] = []
            color_index += 1
        else:
            process_color = False

    color_max = color_index

    #

    bone_index = 0
    process_bone = True
    while process_bone:
        joint_id = JOINTS_PREFIX + str(bone_index)
        weight_id = WEIGHTS_PREFIX + str(bone_index)

        if source_attributes.get(joint_id) is not None:
            attributes[joint_id] = []
            attributes[weight_id] = []
            bone_index += 1
        else:
            process_bone = False

    bone_max = bone_index

    #

    morph_index = 0
    process_morph = True
    while process_morph:
        morph_position_id = MORPH_POSITION_PREFIX + str(morph_index)
        morph_normal_id = MORPH_NORMAL_PREFIX + str(morph_index)
        morph_tangent_id = MORPH_TANGENT_PREFIX + str(morph_index)

        if source_attributes.get(morph_position_id) is not None:
            attributes[morph_position_id] = []
            attributes[morph_normal_id] = []
            if use_tangents:
                attributes[morph_tangent_id] = []
            morph_index += 1
        else:
            process_morph = False

    morph_max = morph_index

    #

    old_to_new_indices = {}
    new_to_old_indices = {}

    new_index = 0
    for old_index in indices:
        if old_to_new_indices.get(old_index) is None:
            old_to_new_indices[old_index] = new_index
            new_to_old_indices[new_index] = old_index
            new_index += 1

        result_primitive[INDICES_ID].append(old_to_new_indices[old_index])

    end_new_index = new_index

    for new_index in range(0, end_new_index):
        old_index = new_to_old_indices[new_index]

        for vi in range(0, 3):
            attributes[POSITION_ATTRIBUTE].append(source_attributes[POSITION_ATTRIBUTE][old_index * 3 + vi])
            attributes[NORMAL_ATTRIBUTE].append(source_attributes[NORMAL_ATTRIBUTE][old_index * 3 + vi])

        if use_tangents:
            for vi in range(0, 4):
                attributes[TANGENT_ATTRIBUTE].append(source_attributes[TANGENT_ATTRIBUTE][old_index * 4 + vi])

        for tex_coord_index in range(0, tex_coord_max):
            tex_coord_id = TEXCOORD_PREFIX + str(tex_coord_index)
            for vi in range(0, 2):
                attributes[tex_coord_id].append(source_attributes[tex_coord_id][old_index * 2 + vi])

        for color_index in range(0, color_max):
            color_id = COLOR_PREFIX + str(color_index)
            for vi in range(0, 4):
                attributes[color_id].append(source_attributes[color_id][old_index * 4 + vi])

        for bone_index in range(0, bone_max):
            joint_id = JOINTS_PREFIX + str(bone_index)
            weight_id = WEIGHTS_PREFIX + str(bone_index)
            for vi in range(0, 4):
                attributes[joint_id].append(source_attributes[joint_id][old_index * 4 + vi])
                attributes[weight_id].append(source_attributes[weight_id][old_index * 4 + vi])

        for morph_index in range(0, morph_max):
            morph_position_id = MORPH_POSITION_PREFIX + str(morph_index)
            morph_normal_id = MORPH_NORMAL_PREFIX + str(morph_index)
            morph_tangent_id = MORPH_TANGENT_PREFIX + str(morph_index)
            for vi in range(0, 3):
                attributes[morph_position_id].append(source_attributes[morph_position_id][old_index * 3 + vi])
                attributes[morph_normal_id].append(source_attributes[morph_normal_id][old_index * 3 + vi])
            if use_tangents:
                for vi in range(0, 4):
                    attributes[morph_tangent_id].append(source_attributes[morph_tangent_id][old_index * 4 + vi])

    return result_primitive


def extract_primitives(glTF, blender_mesh, blender_object, blender_vertex_groups, modifiers, export_settings):
    """
    Extract primitives from a mesh. Polygons are triangulated and sorted by material.

    Furthermore, primitives are split up, if the indices range is exceeded.
    Finally, triangles are also split up/duplicated, if face normals are used instead of vertex normals.
    """
    print_console('INFO', 'Extracting primitive: ' + blender_mesh.name)

    if blender_mesh.has_custom_normals:
        # Custom normals are all (0, 0, 0) until calling calc_normals_split() or calc_tangents().
        blender_mesh.calc_normals_split()

    use_tangents = False
    if blender_mesh.uv_layers.active and len(blender_mesh.uv_layers) > 0:
        try:
            blender_mesh.calc_tangents()
            use_tangents = True
        except Exception:
            print_console('WARNING', 'Could not calculate tangents. Please try to triangulate the mesh first.')

    #

    material_map = {}

    #
    # Gathering position, normal and tex_coords.
    #
    no_material_attributes = {
        POSITION_ATTRIBUTE: [],
        NORMAL_ATTRIBUTE: []
    }

    if use_tangents:
        no_material_attributes[TANGENT_ATTRIBUTE] = []

    #
    # Directory of materials with its primitive.
    #
    no_material_primitives = {
        MATERIAL_ID: 0,
        INDICES_ID: [],
        ATTRIBUTES_ID: no_material_attributes
    }

    material_idx_to_primitives = {0: no_material_primitives}

    #

    vertex_index_to_new_indices = {}

    material_map[0] = vertex_index_to_new_indices

    #
    # Create primitive for each material.
    #
    for (mat_idx, _) in enumerate(blender_mesh.materials):
        attributes = {
            POSITION_ATTRIBUTE: [],
            NORMAL_ATTRIBUTE: []
        }

        if use_tangents:
            attributes[TANGENT_ATTRIBUTE] = []

        primitive = {
            MATERIAL_ID: mat_idx,
            INDICES_ID: [],
            ATTRIBUTES_ID: attributes
        }

        material_idx_to_primitives[mat_idx] = primitive

        #

        vertex_index_to_new_indices = {}

        material_map[mat_idx] = vertex_index_to_new_indices

    tex_coord_max = 0
    if blender_mesh.uv_layers.active:
        tex_coord_max = len(blender_mesh.uv_layers)

    #

    vertex_colors = {}

    color_index = 0
    for vertex_color in blender_mesh.vertex_colors:
        vertex_color_name = COLOR_PREFIX + str(color_index)
        vertex_colors[vertex_color_name] = vertex_color

        color_index += 1
        if color_index >= GLTF_MAX_COLORS:
            break
    color_max = color_index

    #

    bone_max = 0
    for blender_polygon in blender_mesh.polygons:
        for loop_index in blender_polygon.loop_indices:
            vertex_index = blender_mesh.loops[loop_index].vertex_index
            bones_count = len(blender_mesh.vertices[vertex_index].groups)
            if bones_count > 0:
                if bones_count % 4 == 0:
                    bones_count -= 1
                bone_max = max(bone_max, bones_count // 4 + 1)

    #

    morph_max = 0

    blender_shape_keys = []

    if blender_mesh.shape_keys is not None:
        for blender_shape_key in blender_mesh.shape_keys.key_blocks:
            if blender_shape_key != blender_shape_key.relative_key:
                if blender_shape_key.mute is False:
                    morph_max += 1
                    blender_shape_keys.append(ShapeKey(
                        blender_shape_key,
                        blender_shape_key.normals_vertex_get(),  # calculate vertex normals for this shape key
                        blender_shape_key.normals_polygon_get()))  # calculate polygon normals for this shape key


    armature = None
    if modifiers is not None:
        modifiers_dict = {m.type: m for m in modifiers}
        if "ARMATURE" in modifiers_dict:
            modifier = modifiers_dict["ARMATURE"]
            armature = modifier.object


    #
    # Convert polygon to primitive indices and eliminate invalid ones. Assign to material.
    #
    for blender_polygon in blender_mesh.polygons:
        export_color = True

        #

        if not blender_polygon.material_index in material_idx_to_primitives:
            primitive = material_idx_to_primitives[0]
            vertex_index_to_new_indices = material_map[0]
        else:
            primitive = material_idx_to_primitives[blender_polygon.material_index]
            vertex_index_to_new_indices = material_map[blender_polygon.material_index]
        #

        attributes = primitive[ATTRIBUTES_ID]

        face_normal = blender_polygon.normal
        face_tangent = Vector((0.0, 0.0, 0.0))
        face_bitangent = Vector((0.0, 0.0, 0.0))
        if use_tangents:
            for loop_index in blender_polygon.loop_indices:
                temp_vertex = blender_mesh.loops[loop_index]
                face_tangent += temp_vertex.tangent
                face_bitangent += temp_vertex.bitangent

            face_tangent.normalize()
            face_bitangent.normalize()

        #

        indices = primitive[INDICES_ID]

        loop_index_list = []

        if len(blender_polygon.loop_indices) == 3:
            loop_index_list.extend(blender_polygon.loop_indices)
        elif len(blender_polygon.loop_indices) > 3:
            # Triangulation of polygon. Using internal function, as non-convex polygons could exist.
            polyline = []

            for loop_index in blender_polygon.loop_indices:
                vertex_index = blender_mesh.loops[loop_index].vertex_index
                v = blender_mesh.vertices[vertex_index].co
                polyline.append(Vector((v[0], v[1], v[2])))

            triangles = tessellate_polygon((polyline,))

            for triangle in triangles:
                for triangle_index in triangle:
                    loop_index_list.append(blender_polygon.loop_indices[triangle_index])
        else:
            continue

        for loop_index in loop_index_list:
            vertex_index = blender_mesh.loops[loop_index].vertex_index

            if vertex_index_to_new_indices.get(vertex_index) is None:
                vertex_index_to_new_indices[vertex_index] = []

            #

            v = None
            n = None
            t = None
            b = None
            uvs = []
            colors = []
            joints = []
            weights = []

            target_positions = []
            target_normals = []
            target_tangents = []

            vertex = blender_mesh.vertices[vertex_index]

            v = convert_swizzle_location(vertex.co, armature, blender_object, export_settings)
            if blender_polygon.use_smooth or blender_mesh.use_auto_smooth:
                if blender_mesh.has_custom_normals:
                    n = convert_swizzle_normal_and_tangent(blender_mesh.loops[loop_index].normal, armature, blender_object, export_settings)
                else:
                    n = convert_swizzle_normal_and_tangent(vertex.normal, armature, blender_object, export_settings)
                if use_tangents:
                    t = convert_swizzle_tangent(blender_mesh.loops[loop_index].tangent, armature, blender_object, export_settings)
                    b = convert_swizzle_location(blender_mesh.loops[loop_index].bitangent, armature, blender_object, export_settings)
            else:
                n = convert_swizzle_normal_and_tangent(face_normal, armature, blender_object, export_settings)
                if use_tangents:
                    t = convert_swizzle_tangent(face_tangent, armature, blender_object, export_settings)
                    b = convert_swizzle_location(face_bitangent, armature, blender_object, export_settings)

            if use_tangents:
                tv = Vector((t[0], t[1], t[2]))
                bv = Vector((b[0], b[1], b[2]))
                nv = Vector((n[0], n[1], n[2]))

                if (nv.cross(tv)).dot(bv) < 0.0:
                    t[3] = -1.0

            if blender_mesh.uv_layers.active:
                for tex_coord_index in range(0, tex_coord_max):
                    uv = blender_mesh.uv_layers[tex_coord_index].data[loop_index].uv
                    uvs.append([uv.x, 1.0 - uv.y])

            #

            if color_max > 0 and export_color:
                for color_index in range(0, color_max):
                    color_name = COLOR_PREFIX + str(color_index)
                    color = vertex_colors[color_name].data[loop_index].color
                    if len(color) == 3:
                        colors.append([
                            color_srgb_to_scene_linear(color[0]),
                            color_srgb_to_scene_linear(color[1]),
                            color_srgb_to_scene_linear(color[2]),
                            1.0
                        ])
                    else:
                        colors.append([
                            color_srgb_to_scene_linear(color[0]),
                            color_srgb_to_scene_linear(color[1]),
                            color_srgb_to_scene_linear(color[2]),
                            color[3]
                        ])

            #

            bone_count = 0

            if blender_vertex_groups is not None and vertex.groups is not None and len(vertex.groups) > 0 and export_settings[gltf2_blender_export_keys.SKINS]:
                joint = []
                weight = []
                vertex_groups = vertex.groups
                if not export_settings['gltf_all_vertex_influences']:
                    # sort groups by weight descending
                    vertex_groups = sorted(vertex.groups, key=attrgetter('weight'), reverse=True)
                for group_element in vertex_groups:

                    if len(joint) == 4:
                        bone_count += 1
                        joints.append(joint)
                        weights.append(weight)
                        joint = []
                        weight = []

                    #

                    joint_weight = group_element.weight
                    if joint_weight <= 0.0:
                        continue

                    #

                    vertex_group_index = group_element.group
                    vertex_group_name = blender_vertex_groups[vertex_group_index].name

                    joint_index = None

                    if armature:
                        skin = gltf2_blender_gather_skins.gather_skin(armature, export_settings)
                        for index, j in enumerate(skin.joints):
                            if j.name == vertex_group_name:
                                joint_index = index
                                break

                    #
                    if joint_index is not None:
                        joint.append(joint_index)
                        weight.append(joint_weight)

                if len(joint) > 0:
                    bone_count += 1

                    for fill in range(0, 4 - len(joint)):
                        joint.append(0)
                        weight.append(0.0)

                    joints.append(joint)
                    weights.append(weight)

            for fill in range(0, bone_max - bone_count):
                joints.append([0, 0, 0, 0])
                weights.append([0.0, 0.0, 0.0, 0.0])

            #

            if morph_max > 0 and export_settings[gltf2_blender_export_keys.MORPH]:
                for morph_index in range(0, morph_max):
                    blender_shape_key = blender_shape_keys[morph_index]

                    v_morph = convert_swizzle_location(blender_shape_key.shape_key.data[vertex_index].co,
                                                       armature, blender_object,
                                                       export_settings)

                    # Store delta.
                    v_morph -= v

                    target_positions.append(v_morph)

                    #

                    n_morph = None

                    if blender_polygon.use_smooth:
                        temp_normals = blender_shape_key.vertex_normals
                        n_morph = (temp_normals[vertex_index * 3 + 0], temp_normals[vertex_index * 3 + 1],
                                   temp_normals[vertex_index * 3 + 2])
                    else:
                        temp_normals = blender_shape_key.polygon_normals
                        n_morph = (
                            temp_normals[blender_polygon.index * 3 + 0], temp_normals[blender_polygon.index * 3 + 1],
                            temp_normals[blender_polygon.index * 3 + 2])

                    n_morph = convert_swizzle_normal_and_tangent(Vector(n_morph), armature, blender_object, export_settings)

                    # Store delta.
                    n_morph -= n

                    target_normals.append(n_morph)

                    #

                    if use_tangents:
                        rotation = n_morph.rotation_difference(n)

                        t_morph = Vector((t[0], t[1], t[2]))

                        t_morph.rotate(rotation)

                        target_tangents.append(t_morph)

            #
            #

            create = True

            for current_new_index in vertex_index_to_new_indices[vertex_index]:
                found = True

                for i in range(0, 3):
                    if attributes[POSITION_ATTRIBUTE][current_new_index * 3 + i] != v[i]:
                        found = False
                        break

                    if attributes[NORMAL_ATTRIBUTE][current_new_index * 3 + i] != n[i]:
                        found = False
                        break

                if use_tangents:
                    for i in range(0, 4):
                        if attributes[TANGENT_ATTRIBUTE][current_new_index * 4 + i] != t[i]:
                            found = False
                            break

                if not found:
                    continue

                for tex_coord_index in range(0, tex_coord_max):
                    uv = uvs[tex_coord_index]

                    tex_coord_id = TEXCOORD_PREFIX + str(tex_coord_index)
                    for i in range(0, 2):
                        if attributes[tex_coord_id][current_new_index * 2 + i] != uv[i]:
                            found = False
                            break

                if export_color:
                    for color_index in range(0, color_max):
                        color = colors[color_index]

                        color_id = COLOR_PREFIX + str(color_index)
                        for i in range(0, 3):
                            # Alpha is always 1.0 - see above.
                            current_color = attributes[color_id][current_new_index * 4 + i]
                            if color_srgb_to_scene_linear(current_color) != color[i]:
                                found = False
                                break

                if export_settings[gltf2_blender_export_keys.SKINS]:
                    for bone_index in range(0, bone_max):
                        joint = joints[bone_index]
                        weight = weights[bone_index]

                        joint_id = JOINTS_PREFIX + str(bone_index)
                        weight_id = WEIGHTS_PREFIX + str(bone_index)
                        for i in range(0, 4):
                            if attributes[joint_id][current_new_index * 4 + i] != joint[i]:
                                found = False
                                break
                            if attributes[weight_id][current_new_index * 4 + i] != weight[i]:
                                found = False
                                break

                if export_settings[gltf2_blender_export_keys.MORPH]:
                    for morph_index in range(0, morph_max):
                        target_position = target_positions[morph_index]
                        target_normal = target_normals[morph_index]
                        if use_tangents:
                            target_tangent = target_tangents[morph_index]

                        target_position_id = MORPH_POSITION_PREFIX + str(morph_index)
                        target_normal_id = MORPH_NORMAL_PREFIX + str(morph_index)
                        target_tangent_id = MORPH_TANGENT_PREFIX + str(morph_index)
                        for i in range(0, 3):
                            if attributes[target_position_id][current_new_index * 3 + i] != target_position[i]:
                                found = False
                                break
                            if attributes[target_normal_id][current_new_index * 3 + i] != target_normal[i]:
                                found = False
                                break
                            if use_tangents:
                                if attributes[target_tangent_id][current_new_index * 3 + i] != target_tangent[i]:
                                    found = False
                                    break

                if found:
                    indices.append(current_new_index)

                    create = False
                    break

            if not create:
                continue

            new_index = 0

            if primitive.get('max_index') is not None:
                new_index = primitive['max_index'] + 1

            primitive['max_index'] = new_index

            vertex_index_to_new_indices[vertex_index].append(new_index)

            #
            #

            indices.append(new_index)

            #

            attributes[POSITION_ATTRIBUTE].extend(v)
            attributes[NORMAL_ATTRIBUTE].extend(n)
            if use_tangents:
                attributes[TANGENT_ATTRIBUTE].extend(t)

            if blender_mesh.uv_layers.active:
                for tex_coord_index in range(0, tex_coord_max):
                    tex_coord_id = TEXCOORD_PREFIX + str(tex_coord_index)

                    if attributes.get(tex_coord_id) is None:
                        attributes[tex_coord_id] = []

                    attributes[tex_coord_id].extend(uvs[tex_coord_index])

            if export_color:
                for color_index in range(0, color_max):
                    color_id = COLOR_PREFIX + str(color_index)

                    if attributes.get(color_id) is None:
                        attributes[color_id] = []

                    attributes[color_id].extend(colors[color_index])

            if export_settings[gltf2_blender_export_keys.SKINS]:
                for bone_index in range(0, bone_max):
                    joint_id = JOINTS_PREFIX + str(bone_index)

                    if attributes.get(joint_id) is None:
                        attributes[joint_id] = []

                    attributes[joint_id].extend(joints[bone_index])

                    weight_id = WEIGHTS_PREFIX + str(bone_index)

                    if attributes.get(weight_id) is None:
                        attributes[weight_id] = []

                    attributes[weight_id].extend(weights[bone_index])

            if export_settings[gltf2_blender_export_keys.MORPH]:
                for morph_index in range(0, morph_max):
                    target_position_id = MORPH_POSITION_PREFIX + str(morph_index)

                    if attributes.get(target_position_id) is None:
                        attributes[target_position_id] = []

                    attributes[target_position_id].extend(target_positions[morph_index])

                    target_normal_id = MORPH_NORMAL_PREFIX + str(morph_index)

                    if attributes.get(target_normal_id) is None:
                        attributes[target_normal_id] = []

                    attributes[target_normal_id].extend(target_normals[morph_index])

                    if use_tangents:
                        target_tangent_id = MORPH_TANGENT_PREFIX + str(morph_index)

                        if attributes.get(target_tangent_id) is None:
                            attributes[target_tangent_id] = []

                        attributes[target_tangent_id].extend(target_tangents[morph_index])

    #
    # Add non-empty primitives
    #

    result_primitives = [
        primitive
        for primitive in material_idx_to_primitives.values()
        if len(primitive[INDICES_ID]) != 0
    ]

    print_console('INFO', 'Primitives created: ' + str(len(result_primitives)))

    return result_primitives
