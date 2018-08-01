# Copyright (c) 2017 The Khronos Group Inc.
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

import mathutils
import mathutils.geometry

from .gltf2_debug import *

#
# Globals
#

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

def convert_swizzle_location(loc, export_settings):
    """
    Converts a location from Blender coordinate system to glTF coordinate system.
    """
    if export_settings['gltf_yup']:
        return mathutils.Vector((loc[0], loc[2], -loc[1]))
    else:
        return mathutils.Vector((loc[0], loc[1], loc[2]))


def convert_swizzle_tangent(tan, export_settings):
    """
    Converts a tangent from Blender coordinate system to glTF coordinate system.
    """
    
    if tan[0] == 0.0 and tan[1] == 0.0 and tan[2] == 0.0:
        print_console('WARNING', 'Tangent has zero length.')
    
    if export_settings['gltf_yup']:
        return mathutils.Vector((tan[0], tan[2], -tan[1], 1.0))
    else:
        return mathutils.Vector((tan[0], tan[1], tan[2], 1.0))


def convert_swizzle_rotation(rot, export_settings):
    """
    Converts a quaternion rotation from Blender coordinate system to glTF coordinate system.
    'w' is still at first position.
    """
    if export_settings['gltf_yup']:
        return mathutils.Quaternion((rot[0], rot[1], rot[3], -rot[2]))
    else:
        return mathutils.Quaternion((rot[0], rot[1], rot[2], rot[3]))


def convert_swizzle_scale(scale, export_settings):
    """
    Converts a scale from Blender coordinate system to glTF coordinate system.
    """
    if export_settings['gltf_yup']:
        return mathutils.Vector((scale[0], scale[2], scale[1]))
    else:
        return mathutils.Vector((scale[0], scale[1], scale[2]))


def decompose_transition(matrix, context, export_settings):
    translation, rotation, scale = matrix.decompose()
    """
    Decompose a matrix depending if it is associated to a joint or node.
    """

    if context == 'NODE':
        translation = convert_swizzle_location(translation, export_settings)
        rotation = convert_swizzle_rotation(rotation, export_settings)
        scale = convert_swizzle_scale(scale, export_settings)
    
    # Put w at the end.    
    rotation = mathutils.Quaternion((rotation[1], rotation[2], rotation[3], rotation[0]))
    
    return translation, rotation, scale


def color_srgb_to_scene_linear(c):
    """
    Convert from sRGB to scene linear colorspace.
    Source: Cycles addon implementation, node_color.h.
    """
    if c < 0.04045:
        return 0.0 if c < 0.0 else c * (1.0 / 12.92)
    else:
        return pow((c + 0.055) * (1.0 / 1.055), 2.4)


def extract_primitive_floor(a, indices, use_tangents):
    """
    Shift indices, that the first one starts with 0. It is assumed, that the indices are packed.
    """

    attributes = {
        'POSITION' : [],
        'NORMAL' : []
    }
    
    if use_tangents:
        attributes['TANGENT'] = []
    
    result_primitive = {
        'material' : a['material'],
        'indices' : [],
        'attributes' : attributes
    }
    
    source_attributes = a['attributes']
    
    #
    
    texcoord_index = 0
    process_texcoord = True
    while process_texcoord:  
        texcoord_id = 'TEXCOORD_' + str(texcoord_index)
        
        if source_attributes.get(texcoord_id) is not None:
            attributes[texcoord_id] = []
            texcoord_index += 1
        else:
            process_texcoord = False
        
    texcoord_max = texcoord_index 

    #
    
    color_index = 0
    process_color = True
    while process_color:  
        color_id = 'COLOR_' + str(color_index)
        
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
        joint_id = 'JOINTS_' + str(bone_index)
        weight_id = 'WEIGHTS_' + str(bone_index)
        
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
        morph_position_id = 'MORPH_POSITION_' + str(morph_index)
        morph_normal_id = 'MORPH_NORMAL_' + str(morph_index)
        morph_tangent_id = 'MORPH_TANGENT_' + str(morph_index)
        
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
        result_primitive['indices'].append(old_index - min_index)
    
    for old_index in range(min_index, max_index + 1):
        for vi in range(0, 3):
            attributes['POSITION'].append(source_attributes['POSITION'][old_index * 3 + vi])     
            attributes['NORMAL'].append(source_attributes['NORMAL'][old_index * 3 + vi])

        if use_tangents:
            for vi in range(0, 4):
                attributes['TANGENT'].append(source_attributes['TANGENT'][old_index * 4 + vi])
            
        for texcoord_index in range(0, texcoord_max):
            texcoord_id = 'TEXCOORD_' + str(texcoord_index)
            for vi in range(0, 2):
                attributes[texcoord_id].append(source_attributes[texcoord_id][old_index * 2 + vi])

        for color_index in range(0, color_max):
            color_id = 'COLOR_' + str(color_index)
            for vi in range(0, 4):
                attributes[color_id].append(source_attributes[color_id][old_index * 4 + vi])

        for bone_index in range(0, bone_max):
            joint_id = 'JOINTS_' + str(bone_index)
            weight_id = 'WEIGHTS_' + str(bone_index)
            for vi in range(0, 4):
                attributes[joint_id].append(source_attributes[joint_id][old_index * 4 + vi])
                attributes[weight_id].append(source_attributes[weight_id][old_index * 4 + vi])
                
        for morph_index in range(0, morph_max):
            morph_position_id = 'MORPH_POSITION_' + str(morph_index)
            morph_normal_id = 'MORPH_NORMAL_' + str(morph_index)
            morph_tangent_id = 'MORPH_TANGENT_' + str(morph_index)
            for vi in range(0, 3):
                attributes[morph_position_id].append(source_attributes[morph_position_id][old_index * 3 + vi])
                attributes[morph_normal_id].append(source_attributes[morph_normal_id][old_index * 3 + vi])
            if use_tangents:
                for vi in range(0, 4):
                    attributes[morph_tangent_id].append(source_attributes[morph_tangent_id][old_index * 4 + vi])

    return result_primitive


def extract_primitive_pack(a, indices, use_tangents):
    """
    Packs indices, that the first one starts with 0. Current indices can have gaps.
    """

    attributes = {
        'POSITION' : [],
        'NORMAL' : []
    }
    
    if use_tangents:
        attributes['TANGENT'] = []
    
    result_primitive = {
        'material' : a['material'],
        'indices' : [],
        'attributes' : attributes
    }

    source_attributes = a['attributes']
    
    #
    
    texcoord_index = 0
    process_texcoord = True
    while process_texcoord:  
        texcoord_id = 'TEXCOORD_' + str(texcoord_index)
        
        if source_attributes.get(texcoord_id) is not None:
            attributes[texcoord_id] = []
            texcoord_index += 1
        else:
            process_texcoord = False
        
    texcoord_max = texcoord_index 

    #
    
    color_index = 0
    process_color = True
    while process_color:  
        color_id = 'COLOR_' + str(color_index)
        
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
        joint_id = 'JOINTS_' + str(bone_index)
        weight_id = 'WEIGHTS_' + str(bone_index)
        
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
        morph_position_id = 'MORPH_POSITION_' + str(morph_index)
        morph_normal_id = 'MORPH_NORMAL_' + str(morph_index)
        morph_tangent_id = 'MORPH_TANGENT_' + str(morph_index)
        
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
        
        result_primitive['indices'].append(old_to_new_indices[old_index])

    end_new_index = new_index
        
    for new_index in range(0, end_new_index):
        old_index = new_to_old_indices[new_index]
        
        for vi in range(0, 3):
            attributes['POSITION'].append(source_attributes['POSITION'][old_index * 3 + vi])     
            attributes['NORMAL'].append(source_attributes['NORMAL'][old_index * 3 + vi])

        if use_tangents:
            for vi in range(0, 4):
                attributes['TANGENT'].append(source_attributes['TANGENT'][old_index * 4 + vi])
            
        for texcoord_index in range(0, texcoord_max):
            texcoord_id = 'TEXCOORD_' + str(texcoord_index)
            for vi in range(0, 2):
                attributes[texcoord_id].append(source_attributes[texcoord_id][old_index * 2 + vi])
    
        for color_index in range(0, color_max):
            color_id = 'COLOR_' + str(color_index)
            for vi in range(0, 4):
                attributes[color_id].append(source_attributes[color_id][old_index * 4 + vi])
    
        for bone_index in range(0, bone_max):
            joint_id = 'JOINTS_' + str(bone_index)
            weight_id = 'WEIGHTS_' + str(bone_index)
            for vi in range(0, 4):
                attributes[joint_id].append(source_attributes[joint_id][old_index * 4 + vi])
                attributes[weight_id].append(source_attributes[weight_id][old_index * 4 + vi])
                
        for morph_index in range(0, morph_max):
            morph_position_id = 'MORPH_POSITION_' + str(morph_index)
            morph_normal_id = 'MORPH_NORMAL_' + str(morph_index)
            morph_tangent_id = 'MORPH_TANGENT_' + str(morph_index)
            for vi in range(0, 3):
                attributes[morph_position_id].append(source_attributes[morph_position_id][old_index * 3 + vi])
                attributes[morph_normal_id].append(source_attributes[morph_normal_id][old_index * 3 + vi])
            if use_tangents:
                for vi in range(0, 4):
                    attributes[morph_tangent_id].append(source_attributes[morph_tangent_id][old_index * 4 + vi])
    
    return result_primitive     

    
def extract_primitives(glTF, blender_mesh, blender_vertex_groups, export_settings):
    """
    Extracting primitives from a mesh. Polygons are triangulated and sorted by material.
    Furthermore, primitives are splitted up, if the indices range is exceeded.
    Finally, triangles are also splitted up/dublicatted, if face normals are used instead of vertex normals. 
    """

    print_console('INFO', 'Extracting primitive')
    
    use_tangents = False
    if blender_mesh.uv_layers.active and len(blender_mesh.uv_layers) > 0:
        try:
            blender_mesh.calc_tangents()
            use_tangents = True
        except:
            print_console('WARNING', 'Could not calculate tangents. Please try to triangulate the mesh first.')
    
    #
    
    material_map = {}
    
    #
    # Gathering position, normal and texcoords.
    #
    no_material_attributes = {
        'POSITION' : [],
        'NORMAL' : []
    }
    
    if use_tangents:
        no_material_attributes['TANGENT'] = []
        
    #
    # Directory of materials with its primitive.
    #
    no_material_primitives = {
        'material' : '',
        'indices' : [],
        'attributes' : no_material_attributes
    }
    
    material_name_to_primitives = {'' : no_material_primitives}

    #
    
    vertex_index_to_new_indices = {}
    
    material_map[''] = vertex_index_to_new_indices 
    
    #
    # Create primitive for each material.
    #
    for blender_material in blender_mesh.materials:
        if blender_material is None:
            continue

        attributes = {
            'POSITION' : [],
            'NORMAL' : []
        }
        
        if use_tangents:
            attributes['TANGENT'] = []
        
        primitive = {
            'material' : blender_material.name,
            'indices' : [],
            'attributes' : attributes
        }
        
        material_name_to_primitives[blender_material.name] = primitive
        
        #
        
        vertex_index_to_new_indices = {}
        
        material_map[blender_material.name] = vertex_index_to_new_indices 

    texcoord_max = 0
    if blender_mesh.uv_layers.active:
        texcoord_max = len(blender_mesh.uv_layers)

    #
    
    vertex_colors = {}
    
    color_max = 0
    color_index = 0
    for vertex_color in blender_mesh.vertex_colors:
        vertex_color_name = 'COLOR_' + str(color_index)
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
        morph_max = len(blender_mesh.shape_keys.key_blocks) - 1
        
        for blender_shape_key in blender_mesh.shape_keys.key_blocks:
            if blender_shape_key != blender_shape_key.relative_key:
                blender_shape_keys.append(ShapeKey(
                    blender_shape_key,
                    blender_shape_key.normals_vertex_get(),   # calculate vertex normals for this shape key
                    blender_shape_key.normals_polygon_get())) # calculate polygon normals for this shape key

        
    #
    # Convert polygon to primitive indices and eliminate invalid ones. Assign to material.
    #
    for blender_polygon in blender_mesh.polygons:
        export_color = True
        
        #
        
        primitive = None
        vertex_index_to_new_indices = None
        if blender_polygon.material_index < 0 or blender_polygon.material_index >= len(blender_mesh.materials) or blender_mesh.materials[blender_polygon.material_index] is None:
            primitive = material_name_to_primitives['']
            vertex_index_to_new_indices = material_map['']
        else:
            primitive = material_name_to_primitives[blender_mesh.materials[blender_polygon.material_index].name]
            vertex_index_to_new_indices = material_map[blender_mesh.materials[blender_polygon.material_index].name]
            
            # 
            
            if blender_mesh.materials[blender_polygon.material_index].name in export_settings['gltf_use_no_color']: 
                export_color = False
        #
        
        attributes = primitive['attributes']
        
        face_normal = blender_polygon.normal
        face_tangent = mathutils.Vector((0.0, 0.0, 0.0))
        face_bitangent = mathutils.Vector((0.0, 0.0, 0.0))
        if use_tangents:
            for loop_index in blender_polygon.loop_indices:
                temp_vertex = blender_mesh.loops[loop_index]
                face_tangent += temp_vertex.tangent
                face_bitangent += temp_vertex.bitangent
                
            face_tangent.normalize() 
            face_bitangent.normalize()
        
        #
        
        indices = primitive['indices']
        
        loop_index_list = []
        
        if len(blender_polygon.loop_indices) == 3:
            loop_index_list.extend(blender_polygon.loop_indices)
        elif len(blender_polygon.loop_indices) > 3:
            # Triangulation of polygon. Using internal function, as non-convex polygons could exist.
            polyline = []
            
            for loop_index in blender_polygon.loop_indices:
                vertex_index = blender_mesh.loops[loop_index].vertex_index
                v = blender_mesh.vertices[vertex_index].co
                polyline.append(mathutils.Vector((v[0], v[1], v[2])))
                
            triangles = mathutils.geometry.tessellate_polygon((polyline,))
            
            for triangle in triangles:
                loop_index_list.append(blender_polygon.loop_indices[triangle[0]])
                loop_index_list.append(blender_polygon.loop_indices[triangle[2]])
                loop_index_list.append(blender_polygon.loop_indices[triangle[1]])
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
            
            v = convert_swizzle_location(vertex.co, export_settings)
            if blender_polygon.use_smooth:
                n = convert_swizzle_location(vertex.normal, export_settings)
                if use_tangents:
                    t = convert_swizzle_tangent(blender_mesh.loops[loop_index].tangent, export_settings)
                    b = convert_swizzle_location(blender_mesh.loops[loop_index].bitangent, export_settings)
            else:
                n = convert_swizzle_location(face_normal, export_settings)
                if use_tangents:
                    t = convert_swizzle_tangent(face_tangent, export_settings)
                    b = convert_swizzle_location(face_bitangent, export_settings)

            if use_tangents:
                tv = mathutils.Vector((t[0], t[1], t[2]))
                bv = mathutils.Vector((b[0], b[1], b[2]))
                nv = mathutils.Vector((n[0], n[1], n[2]))
                
                if (nv.cross(tv)).dot(bv) < 0.0:
                    t[3] = -1.0
                
            if blender_mesh.uv_layers.active:
                for texcoord_index in range(0, texcoord_max):
                    uv = blender_mesh.uv_layers[texcoord_index].data[loop_index].uv
                    uvs.append([uv.x, 1.0 - uv.y])
                    
            #
            
            if color_max > 0 and export_color:
                for color_index in range(0, color_max):
                    color_name = 'COLOR_' + str(color_index)
                    color = vertex_colors[color_name].data[loop_index].color
                    colors.append([
                        color_srgb_to_scene_linear(color[0]),
                        color_srgb_to_scene_linear(color[1]),
                        color_srgb_to_scene_linear(color[2]),
                        1.0
                    ])
            
            #
            
            bone_count = 0

            if vertex.groups is not None and len(vertex.groups) > 0 and export_settings['gltf_skins']:
                joint = []
                weight = []
                for group_element in vertex.groups:

                    if len(joint) == 4:
                        bone_count += 1
                        joints.append(joint)
                        weights.append(weight)
                        joint = []
                        weight = []
                    
                    #
                    
                    vertex_group_index = group_element.group
                    
                    vertex_group_name = blender_vertex_groups[vertex_group_index].name
                    
                    #
                    
                    joint_index = 0
                    joint_weight = 0.0 
                    
                    if export_settings['group_index'].get(vertex_group_name) is not None:
                        joint_index = export_settings['group_index'][vertex_group_name]
                        joint_weight = group_element.weight
                    
                    #
                    
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
            
            if morph_max > 0 and export_settings['gltf_morph']:
                for morph_index in range(0, morph_max):
                    blender_shape_key = blender_shape_keys[morph_index]
                    
                    v_morph = convert_swizzle_location(blender_shape_key.shape_key.data[vertex_index].co, export_settings)
                    
                    # Store delta.
                    v_morph -= v
                    
                    target_positions.append(v_morph)
                    
                    #
                    
                    n_morph = None
                    
                    if blender_polygon.use_smooth:
                        temp_normals = blender_shape_key.vertex_normals
                        n_morph = (temp_normals[vertex_index * 3 + 0], temp_normals[vertex_index * 3 + 1], temp_normals[vertex_index * 3 + 2])
                    else:
                        temp_normals = blender_shape_key.polygon_normals
                        n_morph = (temp_normals[blender_polygon.index * 3 + 0], temp_normals[blender_polygon.index * 3 + 1], temp_normals[blender_polygon.index * 3 + 2])
                        
                    n_morph = convert_swizzle_location(n_morph, export_settings)

                    # Store delta.
                    n_morph -= n
                        
                    target_normals.append(n_morph)
                    
                    #
                    
                    if use_tangents:
                        rotation = n_morph.rotation_difference(n)
    
                        t_morph = mathutils.Vector((t[0], t[1], t[2]))
                        
                        t_morph.rotate(rotation)
                        
                        target_tangents.append(t_morph)
            
            #
            #

            create = True
                
            for current_new_index in vertex_index_to_new_indices[vertex_index]:
                found = True
                
                for i in range(0, 3):
                    if attributes['POSITION'][current_new_index * 3 + i] != v[i]:
                        found = False
                        break

                    if attributes['NORMAL'][current_new_index * 3 + i] != n[i]:
                        found = False
                        break

                if use_tangents:
                    for i in range(0, 4):
                        if attributes['TANGENT'][current_new_index * 4 + i] != t[i]:
                            found = False
                            break
                
                if not found:
                    continue
                
                for texcoord_index in range(0, texcoord_max):
                    uv = uvs[texcoord_index]
                    
                    texcoord_id = 'TEXCOORD_' + str(texcoord_index)
                    for i in range(0, 2):
                        if attributes[texcoord_id][current_new_index * 2 + i] != uv[i]:
                            found = False
                            break
                
                if export_color:
                    for color_index in range(0, color_max):
                        color = colors[color_index]
                        
                        color_id = 'COLOR_' + str(color_index)
                        for i in range(0, 3):
                            # Alpha is always 1.0 - see above.
                            current_color = attributes[color_id][current_new_index * 4 + i]
                            if color_srgb_to_scene_linear(current_color) != color[i]:
                                found = False
                                break

                if export_settings['gltf_skins']:
                    for bone_index in range(0, bone_max):
                        joint = joints[bone_index]
                        weight = weights[bone_index]
                                            
                        joint_id = 'JOINTS_' + str(bone_index)
                        weight_id = 'WEIGHTS_' + str(bone_index)
                        for i in range(0, 4):
                            if attributes[joint_id][current_new_index * 4 + i] != joint[i]:
                                found = False
                                break
                            if attributes[weight_id][current_new_index * 4 + i] != weight[i]:
                                found = False
                                break
                            
                if export_settings['gltf_morph']:
                    for morph_index in range(0, morph_max):
                        target_position = target_positions[morph_index]
                        target_normal = target_normals[morph_index]
                        if use_tangents:
                            target_tangent = target_tangents[morph_index]
                                            
                        target_position_id = 'MORPH_POSITION_' + str(morph_index)
                        target_normal_id = 'MORPH_NORMAL_' + str(morph_index)
                        target_tangent_id = 'MORPH_TANGENT_' + str(morph_index)
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
            
            attributes['POSITION'].extend(v)
            attributes['NORMAL'].extend(n)
            if use_tangents:
                attributes['TANGENT'].extend(t)
                
            if blender_mesh.uv_layers.active:
                for texcoord_index in range(0, texcoord_max):
                    texcoord_id = 'TEXCOORD_' + str(texcoord_index)
                    
                    if attributes.get(texcoord_id) is None:
                        attributes[texcoord_id] = []
                    
                    attributes[texcoord_id].extend(uvs[texcoord_index])

            if export_color:
                for color_index in range(0, color_max):
                    color_id = 'COLOR_' + str(color_index)
                    
                    if attributes.get(color_id) is None:
                        attributes[color_id] = []
                    
                    attributes[color_id].extend(colors[color_index])

            if export_settings['gltf_skins']:
                for bone_index in range(0, bone_max):
                    joint_id = 'JOINTS_' + str(bone_index)
                    
                    if attributes.get(joint_id) is None:
                        attributes[joint_id] = []
                    
                    attributes[joint_id].extend(joints[bone_index])
    
                    weight_id = 'WEIGHTS_' + str(bone_index)
                    
                    if attributes.get(weight_id) is None:
                        attributes[weight_id] = []
                    
                    attributes[weight_id].extend(weights[bone_index])
                    
            if export_settings['gltf_morph']:
                for morph_index in range(0, morph_max):
                    target_position_id = 'MORPH_POSITION_' + str(morph_index)
                    
                    if attributes.get(target_position_id) is None:
                        attributes[target_position_id] = []
                    
                    attributes[target_position_id].extend(target_positions[morph_index])
    
                    target_normal_id = 'MORPH_NORMAL_' + str(morph_index)
                    
                    if attributes.get(target_normal_id) is None:
                        attributes[target_normal_id] = []
                    
                    attributes[target_normal_id].extend(target_normals[morph_index])

                    if use_tangents:
                        target_tangent_id = 'MORPH_TANGENT_' + str(morph_index)
                    
                        if attributes.get(target_tangent_id) is None:
                            attributes[target_tangent_id] = []
                        
                        attributes[target_tangent_id].extend(target_tangents[morph_index])
    
    #
    # Add primitive plus split them if needed.
    # 
    
    result_primitives = []
    
    for material_name, primitive in material_name_to_primitives.items():
        export_color = True
        if material_name in export_settings['gltf_use_no_color']: 
            export_color = False

        #
        
        indices = primitive['indices']
        
        if len(indices) == 0:
            continue
        
        position = primitive['attributes']['POSITION']
        normal = primitive['attributes']['NORMAL']
        if use_tangents:
            tangent = primitive['attributes']['TANGENT']
        texcoords = []
        for texcoord_index in range(0, texcoord_max):
            texcoords.append(primitive['attributes']['TEXCOORD_' + str(texcoord_index)])
        colors = []
        if export_color:
            for color_index in range(0, color_max):
                texcoords.append(primitive['attributes']['COLOR_' + str(color_index)])
        joints = []
        weights = []
        if export_settings['gltf_skins']:
            for bone_index in range(0, bone_max):
                joints.append(primitive['attributes']['JOINTS_' + str(bone_index)])
                weights.append(primitive['attributes']['WEIGHTS_' + str(bone_index)])
         
        target_positions = []
        target_normals = []
        target_tangents = []
        if export_settings['gltf_morph']:
            for morph_index in range(0, morph_max):
                target_positions.append(primitive['attributes']['MORPH_POSITION_' + str(morph_index)])
                target_normals.append(primitive['attributes']['MORPH_NORMAL_' + str(morph_index)])
                if use_tangents:
                    target_tangents.append(primitive['attributes']['MORPH_TANGENT_' + str(morph_index)])
            
        #
        
        count = len(indices) 
        
        if count == 0:
            continue
        
        max_index = max(indices)
        
        #
        
        range_indices = 65536
        if export_settings['gltf_indices'] == 'UNSIGNED_BYTE':
            range_indices = 256
        elif export_settings['gltf_indices'] == 'UNSIGNED_INT':
            range_indices = 4294967296
        
        # 

        if max_index >= range_indices:
            #
            # Spliting result_primitives.
            #
                    
            # At start, all indicees are pending.
            pending_attributes = {
                'POSITION' : [],
                'NORMAL' : []
            }
            
            if use_tangents:
                pending_attributes['TANGENT'] = []
            
            pending_primitive = {
                'material' : material_name,
                'indices' : [],
                'attributes' : pending_attributes
            }
            
            pending_primitive['indices'].extend(indices)
            
                            
            pending_attributes['POSITION'].extend(position)
            pending_attributes['NORMAL'].extend(normal)
            if use_tangents:
                pending_attributes['TANGENT'].extend(tangent)
            texcoord_index = 0
            for texcoord in texcoords:
                pending_attributes['TEXCOORD_' + str(texcoord_index)] = texcoord
                texcoord_index += 1
            if export_color:
                color_index = 0
                for color in colors:
                    pending_attributes['COLOR_' + str(color_index)] = color
                    color_index += 1 
            if export_settings['gltf_skins']:
                joint_index = 0
                for joint in joints:
                    pending_attributes['JOINTS_' + str(joint_index)] = joint
                    joint_index += 1 
                weight_index = 0
                for weight in weights:
                    pending_attributes['WEIGHTS_' + str(weight_index)] = weight
                    weight_index += 1 
            if export_settings['gltf_morph']:
                morph_index = 0
                for target_position in target_positions:
                    pending_attributes['MORPH_POSITION_' + str(morph_index)] = target_position
                    morph_index += 1 
                morph_index = 0
                for target_normal in target_normals:
                    pending_attributes['MORPH_NORMAL_' + str(morph_index)] = target_normal
                    morph_index += 1 
                if use_tangents:
                    morph_index = 0
                    for target_tangent in target_tangents:
                        pending_attributes['MORPH_TANGENT_' + str(morph_index)] = target_tangent
                        morph_index += 1 
            
            pending_indices = pending_primitive['indices']
            
            # Continue until all are processed.
            while len(pending_indices) > 0:
                
                process_indices = pending_primitive['indices']
                
                pending_indices = []

                #
                #
                
                all_local_indices = []

                for i in range(0, (max(process_indices) // range_indices) + 1):
                    all_local_indices.append([])
                
                #
                #
                
                # For all faces ...
                for face_index in range(0, len(process_indices), 3):
                    
                    written = False

                    face_min_index = min(process_indices[face_index + 0], process_indices[face_index + 1], process_indices[face_index + 2])
                    face_max_index = max(process_indices[face_index + 0], process_indices[face_index + 1], process_indices[face_index + 2])

                    # ... check if it can be but in a range of maximum indices.
                    for i in range(0, (max(process_indices) // range_indices) + 1):
                        offset = i * range_indices 
                        
                        # Yes, so store the primitive with its indices.
                        if face_min_index >= offset and face_max_index < offset + range_indices:
                            all_local_indices[i].extend([process_indices[face_index + 0], process_indices[face_index + 1], process_indices[face_index + 2]])
                            
                            written = True
                            break
                    
                    # If not written, the triangel face has indices from different ranges.
                    if not written:
                        pending_indices.extend([process_indices[face_index + 0], process_indices[face_index + 1], process_indices[face_index + 2]])

                # Only add result_primitives, which do have indices in it.
                for local_indices in all_local_indices:
                    if len(local_indices) > 0:
                        current_primitive = extract_primitive_floor(pending_primitive, local_indices, use_tangents)
                        
                        result_primitives.append(current_primitive)
                        
                        print_console('DEBUG', 'Adding primitive with splitting. Indices: ' + str(len(current_primitive['indices'])) + ' Vertices: ' + str(len(current_primitive['attributes']['POSITION']) // 3))

                # Process primitive faces having indices in several ranges.            
                if len(pending_indices) > 0:
                    pending_primitive = extract_primitive_pack(pending_primitive, pending_indices, use_tangents)
                    
                    pending_attributes = pending_primitive['attributes'] 

                    print_console('DEBUG', 'Creating temporary primitive for splitting')
                                
        else:
            #
            # No splitting needed.
            #
            result_primitives.append(primitive)
            
            print_console('DEBUG', 'Adding primitive without splitting. Indices: ' + str(len(primitive['indices'])) + ' Vertices: ' + str(len(primitive['attributes']['POSITION']) // 3))
            
    print_console('INFO', 'Primitives created: ' + str(len(result_primitives)))
    
    return result_primitives
