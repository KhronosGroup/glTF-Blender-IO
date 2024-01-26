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
import numpy as np
from copy import deepcopy
from mathutils import Vector
from ...blender.com.gltf2_blender_data_path import get_sk_exported
from ...io.com.gltf2_io_debug import print_console
from ...io.com.gltf2_io_constants import ROUNDING_DIGIT
from ...io.exp.gltf2_io_user_extensions import export_user_extensions
from ...io.com import gltf2_io_constants
from ..com import gltf2_blender_conversion
from .material.gltf2_blender_gather_materials import get_base_material, get_material_from_idx, get_active_uvmap_index, get_new_material_texture_shared
from .material.gltf2_blender_gather_texture_info import gather_udim_texture_info
from . import gltf2_blender_gather_skins


def extract_primitives(materials, blender_mesh, uuid_for_skined_data, blender_vertex_groups, modifiers, export_settings):
    """Extract primitives from a mesh."""
    print_console('INFO', 'Extracting primitive: ' + blender_mesh.name)

    primitive_creator = PrimitiveCreator(materials, blender_mesh, uuid_for_skined_data, blender_vertex_groups, modifiers, export_settings)
    primitive_creator.prepare_data()
    primitive_creator.define_attributes()
    primitive_creator.create_dots_data_structure()
    primitive_creator.populate_dots_data()
    primitive_creator.primitive_split()
    primitive_creator.manage_material_info() # UVMap & Vertex Color
    if export_settings['gltf_shared_accessors'] is False:
        return primitive_creator.primitive_creation_not_shared(), primitive_creator.additional_materials, None
    else:
        return primitive_creator.primitive_creation_shared()

class PrimitiveCreator:
    def __init__(self, materials, blender_mesh, uuid_for_skined_data, blender_vertex_groups, modifiers, export_settings):
        self.blender_mesh = blender_mesh
        self.uuid_for_skined_data = uuid_for_skined_data
        self.blender_vertex_groups = blender_vertex_groups
        self.modifiers = modifiers
        self.materials = materials
        self.export_settings = export_settings

    @classmethod
    def apply_mat_to_all(cls, matrix, vectors):
        """Given matrix m and vectors [v1,v2,...], computes [m@v1,m@v2,...]"""
        # Linear part
        m = matrix.to_3x3() if len(matrix) == 4 else matrix
        res = np.matmul(vectors, np.array(m.transposed()))
        # Translation part
        if len(matrix) == 4:
            res += np.array(matrix.translation)
        return res

    @classmethod
    def normalize_vecs(cls, vectors):
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        np.divide(vectors, norms, out=vectors, where=norms != 0)

    @classmethod
    def zup2yup(cls, array):
        # x,y,z -> x,z,-y
        array[:, [1,2]] = array[:, [2,1]]  # x,z,y
        array[:, 2] *= -1  # x,z,-y

    def prepare_data(self):
        self.blender_object = None
        if self.uuid_for_skined_data:
            self.blender_object = self.export_settings['vtree'].nodes[self.uuid_for_skined_data].blender_object

        self.use_normals = self.export_settings['gltf_normals']

        self.use_tangents = False
        if self.use_normals and self.export_settings['gltf_tangents']:
            if self.blender_mesh.uv_layers.active and len(self.blender_mesh.uv_layers) > 0:
                try:
                    self.blender_mesh.calc_tangents()
                    self.use_tangents = True
                except Exception:
                    print_console('WARNING', 'Could not calculate tangents. Please try to triangulate the mesh first.')

        self.tex_coord_max = 0
        if self.export_settings['gltf_texcoords']:
            if self.blender_mesh.uv_layers.active:
                self.tex_coord_max = len(self.blender_mesh.uv_layers)

        self.use_morph_normals = self.use_normals and self.export_settings['gltf_morph_normal']
        self.use_morph_tangents = self.use_morph_normals and self.use_tangents and self.export_settings['gltf_morph_tangent']

        self.use_materials = self.export_settings['gltf_materials']

        self.blender_attributes = []

        # Check if we have to export skin
        self.armature = None
        self.skin = None
        if self.export_settings['gltf_skins']:
            if self.modifiers is not None:
                modifiers_dict = {m.type: m for m in self.modifiers}
                if "ARMATURE" in modifiers_dict:
                    modifier = modifiers_dict["ARMATURE"]
                    self.armature = modifier.object

            # Skin must be ignored if the object is parented to a bone of the armature
            # (This creates an infinite recursive error)
            # So ignoring skin in that case
            is_child_of_arma = (
                self.armature and
                self.blender_object and
                self.blender_object.parent_type == "BONE" and
                self.blender_object.parent.name == self.armature.name
            )
            if is_child_of_arma:
                self.armature = None

            if self.armature:
                self.skin = gltf2_blender_gather_skins.gather_skin(self.export_settings['vtree'].nodes[self.uuid_for_skined_data].armature, self.export_settings)
                if not self.skin:
                    self.armature = None

        self.key_blocks = []
        # List of SK that are going to be exported, actually
        if self.blender_mesh.shape_keys and self.export_settings['gltf_morph']:
            self.key_blocks = get_sk_exported(self.blender_mesh.shape_keys.key_blocks)

        # Fetch vert positions and bone data (joint,weights)

        self.locs = None
        self.morph_locs = None
        self.__get_positions()

        if self.skin:
            self.__get_bone_data()
            if self.need_neutral_bone is True:
                # Need to create a fake joint at root of armature
                # In order to assign not assigned vertices to it
                # But for now, this is not yet possible, we need to wait the armature node is created
                # Just store this, to be used later
                armature_uuid = self.export_settings['vtree'].nodes[self.uuid_for_skined_data].armature
                self.export_settings['vtree'].nodes[armature_uuid].need_neutral_bone = True

    def define_attributes(self):


        class KeepAttribute:
            def __init__(self, attr_name):
                self.attr_name = attr_name
                self.keep = attr_name.startswith("_")

        # Manage attributes
        for blender_attribute_index, blender_attribute in enumerate(self.blender_mesh.attributes):

            attr = {}
            attr['blender_attribute_index'] = blender_attribute_index
            attr['blender_name'] = blender_attribute.name
            attr['blender_domain'] = blender_attribute.domain
            attr['blender_data_type'] = blender_attribute.data_type

            # For now, we don't export edge data, because I need to find how to
            # get from edge data to dots data
            if attr['blender_domain'] == "EDGE":
                continue

            # Some type are not exportable (example : String)
            if gltf2_blender_conversion.get_component_type(blender_attribute.data_type) is None or \
                gltf2_blender_conversion.get_data_type(blender_attribute.data_type) is None:

                continue

            # Custom attributes
            # Keep only attributes that starts with _
            # As Blender create lots of attributes that are internal / not needed are as duplicated of standard glTF accessors (position, uv, material_index...)
            if self.export_settings['gltf_attributes'] is False:
                continue
            # Check if there is an extension that want to keep this attribute, or change the exported name
            keep_attribute = KeepAttribute(blender_attribute.name)

            export_user_extensions('gather_attribute_keep', self.export_settings, keep_attribute)

            if keep_attribute.keep is False:
                continue

            attr['gltf_attribute_name'] = keep_attribute.attr_name.upper()
            attr['get'] = self.get_function()

            # Seems we sometime can have name collision about attributes
            # Avoid crash and ignoring one of duplicated attribute name
            if attr['gltf_attribute_name'] in [a['gltf_attribute_name'] for a in self.blender_attributes]:
                print_console('WARNING', 'Attribute collision name: ' + blender_attribute.name + ", ignoring one of them")
                continue

            self.blender_attributes.append(attr)

        # Manage POSITION
        attr = {}
        attr['blender_data_type'] = 'FLOAT_VECTOR'
        attr['blender_domain'] = 'POINT'
        attr['gltf_attribute_name'] = 'POSITION'
        attr['set'] = self.set_function()
        attr['skip_getting_to_dots'] = True
        self.blender_attributes.append(attr)

        # Manage NORMALS
        if self.use_normals:
            attr = {}
            attr['blender_data_type'] = 'FLOAT_VECTOR'
            attr['blender_domain'] = 'CORNER'
            attr['gltf_attribute_name'] = 'NORMAL'
            attr['gltf_attribute_name_morph'] = 'MORPH_NORMAL_'
            attr['get'] = self.get_function()
            self.blender_attributes.append(attr)

        # Manage uvs TEX_COORD_x
        for tex_coord_i in range(self.tex_coord_max):
            attr = {}
            attr['blender_data_type'] = 'FLOAT2'
            attr['blender_domain'] = 'CORNER'
            attr['gltf_attribute_name'] = 'TEXCOORD_' + str(tex_coord_i)
            attr['get'] = self.get_function()
            self.blender_attributes.append(attr)

        # Manage TANGENT
        if self.use_tangents:
            attr = {}
            attr['blender_data_type'] = 'FLOAT_VECTOR_4'
            attr['blender_domain'] = 'CORNER'
            attr['gltf_attribute_name'] = 'TANGENT'
            attr['get'] = self.get_function()
            self.blender_attributes.append(attr)

        # Manage MORPH_POSITION_x
        for morph_i, vs in enumerate(self.morph_locs):
            attr = {}
            attr['blender_attribute_index'] = morph_i
            attr['blender_data_type'] = 'FLOAT_VECTOR'
            attr['blender_domain'] = 'POINT'
            attr['gltf_attribute_name'] = 'MORPH_POSITION_' + str(morph_i)
            attr['skip_getting_to_dots'] = True
            attr['set'] = self.set_function()
            self.blender_attributes.append(attr)

            # Manage MORPH_NORMAL_x
            if self.use_morph_normals:
                attr = {}
                attr['blender_attribute_index'] = morph_i
                attr['blender_data_type'] = 'FLOAT_VECTOR'
                attr['blender_domain'] = 'CORNER'
                attr['gltf_attribute_name'] = 'MORPH_NORMAL_' + str(morph_i)
                # No get function is set here, because data are set from NORMALS
                self.blender_attributes.append(attr)

                # Manage MORPH_TANGENT_x
                # This is a particular case, where we need to have the following data already calculated
                # - NORMAL
                # - MORPH_NORMAL
                # - TANGENT
                # So, the following needs to be AFTER the 3 others.
                if self.use_morph_tangents:
                    attr = {}
                    attr['blender_attribute_index'] = morph_i
                    attr['blender_data_type'] = 'FLOAT_VECTOR'
                    attr['blender_domain'] = 'CORNER'
                    attr['gltf_attribute_name'] = 'MORPH_TANGENT_' + str(morph_i)
                    attr['gltf_attribute_name_normal'] = "NORMAL"
                    attr['gltf_attribute_name_morph_normal'] = "MORPH_NORMAL_" + str(morph_i)
                    attr['gltf_attribute_name_tangent'] = "TANGENT"
                    attr['skip_getting_to_dots'] = True
                    attr['set'] = self.set_function()
                    self.blender_attributes.append(attr)

        for attr in self.blender_attributes:
            attr['len'] = gltf2_blender_conversion.get_data_length(attr['blender_data_type'])
            attr['type'] = gltf2_blender_conversion.get_numpy_type(attr['blender_data_type'])


        # Now we have all attribtues, we can change order if we want
        # Note that the glTF specification doesn't say anything about order
        # Attributes are defined only by name
        # But if user want it in a particular order, he can use this hook to perform it
        export_user_extensions('gather_attributes_change', self.export_settings, self.blender_attributes)

    def create_dots_data_structure(self):
        # Now that we get all attributes that are going to be exported, create numpy array that will store them
        dot_fields = [('vertex_index', np.uint32)]
        if self.export_settings['gltf_loose_edges']:
            dot_fields_edges = [('vertex_index', np.uint32)]
        if self.export_settings['gltf_loose_points']:
            dot_fields_points = [('vertex_index', np.uint32)]
        for attr in self.blender_attributes:
            if 'skip_getting_to_dots' in attr:
                continue
            for i in range(attr['len']):
                dot_fields.append((attr['gltf_attribute_name'] + str(i), attr['type']))
                if attr['blender_domain'] != 'POINT':
                    continue
                if self.export_settings['gltf_loose_edges']:
                    dot_fields_edges.append((attr['gltf_attribute_name'] + str(i), attr['type']))
                if self.export_settings['gltf_loose_points']:
                    dot_fields_points.append((attr['gltf_attribute_name'] + str(i), attr['type']))

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

        self.dots = np.empty(len(self.blender_mesh.loops), dtype=np.dtype(dot_fields))

        # Find loose edges
        if self.export_settings['gltf_loose_edges']:
            loose_edges = [e for e in self.blender_mesh.edges if e.is_loose]
            self.blender_idxs_edges = [vi for e in loose_edges for vi in e.vertices]
            self.blender_idxs_edges = np.array(self.blender_idxs_edges, dtype=np.uint32)

            self.dots_edges = np.empty(len(self.blender_idxs_edges), dtype=np.dtype(dot_fields_edges))
            self.dots_edges['vertex_index'] = self.blender_idxs_edges

        # Find loose points
        if self.export_settings['gltf_loose_points']:
            verts_in_edge = set(vi for e in self.blender_mesh.edges for vi in e.vertices)
            self.blender_idxs_points = [
                vi for vi, _ in enumerate(self.blender_mesh.vertices)
                if vi not in verts_in_edge
            ]
            self.blender_idxs_points = np.array(self.blender_idxs_points, dtype=np.uint32)

            self.dots_points = np.empty(len(self.blender_idxs_points), dtype=np.dtype(dot_fields_points))
            self.dots_points['vertex_index'] = self.blender_idxs_points


    def populate_dots_data(self):
        vidxs = np.empty(len(self.blender_mesh.loops))
        self.blender_mesh.loops.foreach_get('vertex_index', vidxs)
        self.dots['vertex_index'] = vidxs
        del vidxs

        for attr in self.blender_attributes:
            if 'skip_getting_to_dots' in attr:
                continue
            if 'get' not in attr:
                continue
            attr['get'](attr)

    def primitive_split(self):
        # Calculate triangles and sort them into primitives.

        try:
            self.blender_mesh.calc_loop_triangles()
            loop_indices = np.empty(len(self.blender_mesh.loop_triangles) * 3, dtype=np.uint32)
            self.blender_mesh.loop_triangles.foreach_get('loops', loop_indices)
        except:
            # For some not valid meshes, we can't get loops without errors
            # We already displayed a Warning message after validate() check, so here
            # we can return without a new one
            self.prim_indices = {}
            return

        self.prim_indices = {}  # maps material index to TRIANGLES-style indices into dots

        if self.use_materials == "NONE": # Only for None. For placeholder and export, keep primitives
            # Put all vertices into one primitive
            self.prim_indices[-1] = loop_indices

        else:
            # Bucket by material index.

            tri_material_idxs = np.empty(len(self.blender_mesh.loop_triangles), dtype=np.uint32)
            self.blender_mesh.loop_triangles.foreach_get('material_index', tri_material_idxs)
            loop_material_idxs = np.repeat(tri_material_idxs, 3)  # material index for every loop
            unique_material_idxs = np.unique(tri_material_idxs)
            del tri_material_idxs

            for material_idx in unique_material_idxs:
                self.prim_indices[material_idx] = loop_indices[loop_material_idxs == material_idx]

    def manage_material_info(self):
        # If user defined UVMap as a custom attribute, we need to add it/them in the dots structure and populate data
        # So we need to get, for each material, what are these custom attribute
        # No choice : We need to retrieve materials here. Anyway, this will be baked, and next call will be quick
        # We also need to shuffle Vertex Color data if needed

        new_prim_indices = {}
        self.additional_materials = [] # In case of UDIM

        self.uvmap_attribute_list = [] # Initialize here, in case we don't have any triangle primitive

        materials_use_vc = None
        warning_already_displayed = False
        for material_idx in self.prim_indices.keys():
            base_material, material_info = get_base_material(material_idx, self.materials, self.export_settings)

            # UVMaps
            self.uvmap_attribute_list = list(set([i['value'] for i in material_info["uv_info"].values() if 'type' in i.keys() and i['type'] == "Attribute" ]))

            additional_fields = []
            for attr in self.uvmap_attribute_list:
                if attr + str(0) not in self.dots.dtype.names: # In case user exports custom attributes, we may have it already
                    additional_fields.append((attr + str(0), gltf2_blender_conversion.get_numpy_type('FLOAT2')))
                    additional_fields.append((attr + str(1), gltf2_blender_conversion.get_numpy_type('FLOAT2')))

            if len(additional_fields) > 0:
                new_dt = np.dtype(self.dots.dtype.descr + additional_fields)
                dots = np.zeros(self.dots.shape, dtype=new_dt)
                for f in self.dots.dtype.names:
                    dots[f] = self.dots[f]

            # Now we need to get data and populate
            for attr in self.uvmap_attribute_list:
                if attr + str(0) not in self.dots.dtype.names: # In case user exports custom attributes, we may have it already
                    # Vector in custom Attributes are Vector3, but keeping only the first two data
                    data = np.empty(len(self.blender_mesh.loops) * 3, gltf2_blender_conversion.get_numpy_type('FLOAT2'))
                    self.blender_mesh.attributes[attr].data.foreach_get('vector', data)
                    data = data.reshape(-1, 3)
                    data = data[:,:2]
                    # Blender UV space -> glTF UV space
                    # u,v -> u,1-v
                    data[:, 1] *= -1
                    data[:, 1] += 1

                    dots[attr + '0'] = data[:, 0]
                    dots[attr + '1'] = data[:, 1]
                    del data

            if len(additional_fields) > 0:
                self.dots = dots

            # There are multiple case to take into account for VC

            # The simplier test is when no vertex color are used
            if material_info['vc_info']['color_type'] is None and material_info['vc_info']['alpha_type'] is None:
                # Nothing to do
                pass

            elif material_info['vc_info']['color_type'] is None and material_info['vc_info']['alpha_type'] is not None:
                print_console('WARNING', 'We are not managing this case (Vertex Color alpha without color)')

            else:
                vc_color_name = None
                vc_alpha_name = None
                if material_info['vc_info']['color_type'] == "name":
                    vc_color_name = material_info['vc_info']['color']
                elif material_info['vc_info']['color_type'] == "active":
                    # Get active (render) Vertex Color
                    if self.blender_mesh.color_attributes.render_color_index != -1:
                        vc_color_name = self.blender_mesh.color_attributes[self.blender_mesh.color_attributes.render_color_index].name

                if material_info['vc_info']['alpha_type'] == "name":
                    vc_alpha_name = material_info['vc_info']['alpha']
                elif material_info['vc_info']['alpha_type'] == "active":
                    # Get active (render) Vertex Color
                    if self.blender_mesh.color_attributes.render_color_index != -1:
                        vc_alpha_name = self.blender_mesh.color_attributes[self.blender_mesh.color_attributes.render_color_index].name

                if vc_color_name is not None:

                    vc_key = ""
                    vc_key += vc_color_name if vc_color_name is not None else ""
                    vc_key += vc_alpha_name if vc_alpha_name is not None else ""

                    if materials_use_vc is not None and materials_use_vc != vc_key:
                        if warning_already_displayed is False:
                            print_console('WARNING', 'glTF specification does not allow this case (multiple materials with different Vertex Color)')
                            warning_already_displayed = True
                        materials_use_vc = vc_key

                    elif materials_use_vc is None:
                        materials_use_vc = vc_key

                        # We need to check if we need to add alpha
                        add_alpha = vc_alpha_name is not None
                        mat = get_material_from_idx(material_idx, self.materials, self.export_settings)
                        add_alpha = mat is not None and add_alpha and not (mat.blend_method is None or mat.blend_method == 'OPAQUE')
                        # Manage Vertex Color (RGB and Alpha if needed)
                        self.__manage_color_attribute(vc_color_name, vc_alpha_name if add_alpha else None)
                    else:
                        pass # Using the same Vertex Color

            ##### UDIM #####

            if len(material_info['udim_info'].keys()) == 0:
                new_prim_indices[material_idx] = self.prim_indices[material_idx]
                self.additional_materials.append(None)
                continue

            # We have some UDIM for some texture of this material
            # We need to split the mesh into multiple primitives
            # We manage only case where all texture are using the same UVMap
            # And where UDIM have exactly the same number of tiles (TODO to check?)

            # So, retrieve all uvmaps used by this material
            all_uvmaps = {}
            for tex in material_info['udim_info'].keys():
                if material_info['uv_info'][tex]['type'] == "Active":
                    index_uvmap = get_active_uvmap_index(self.blender_mesh)
                    uvmap_name = "TEXCOORD_" + str(index_uvmap)
                elif material_info['uv_info'][tex]['type'] == "Fixed":
                    index_uvmap = self.blender_mesh.uv_layers.find(material_info['uv_info'][tex]['value'])
                    if index_uvmap < 0:
                        # Using active index
                        index_uvmap = get_active_uvmap_index(self.blender_mesh)
                    uvmap_name = "TEXCOORD_" + str(index_uvmap)
                else: #Attribute
                    uvmap_name = material_info['uv_info'][tex]['value']
                all_uvmaps[tex] = uvmap_name

            if len(set(all_uvmaps.values())) > 1:
                print_console('WARNING', 'We are not managing this case (multiple UVMap for UDIM)')
                new_prim_indices[material_idx] = self.prim_indices[material_idx]
                self.additional_materials.append(None)
                continue

            print_console('INFO', 'Splitting UDIM tiles into different primitives/materials')
            # Retrieve UDIM images
            tex = list(material_info['udim_info'].keys())[0]
            image = material_info['udim_info'][tex]['image']

            new_material_index = len(self.prim_indices.keys())

            # Get UVMap used for UDIM
            uvmap_name = all_uvmaps[list(all_uvmaps.keys())[0]]

            # Retrieve tiles number
            tiles = [t.number for t in image.tiles]
            u_tiles = max([int(str(t)[3:]) for t in tiles])
            v_tiles = max([int(str(t)[2:3]) for t in tiles]) + 1

            # We are now going to split the mesh into multiple primitives, based on tiles
            # We need to create a new primitive for each tile

            for u in range(u_tiles):
                for v in range(v_tiles):

                    if u != u_tiles - 1 and v != v_tiles - 1:
                        indices = np.where((self.dots[uvmap_name + '0'] >= u) & (self.dots[uvmap_name + '0'] < (u + 1)) & (self.dots[uvmap_name + '1'] <= (1-v) ) & (self.dots[uvmap_name + '1'] > 1-(v + 1)))[0]
                    elif u == u_tiles - 1 and v != v_tiles - 1:
                        indices = np.where((self.dots[uvmap_name + '0'] >= u) & (self.dots[uvmap_name + '0'] <= (u + 1)) & (self.dots[uvmap_name + '1'] <= (1-v) ) & (self.dots[uvmap_name + '1'] > 1-(v + 1)))[0]
                    elif u != u_tiles -1 and v == v_tiles - 1:
                        indices = np.where((self.dots[uvmap_name + '0'] >= u) & (self.dots[uvmap_name + '0'] < (u + 1)) & (self.dots[uvmap_name + '1'] <= (1-v) ) & (self.dots[uvmap_name + '1'] >= 1-(v + 1)))[0]
                    else:
                        indices = np.where((self.dots[uvmap_name + '0'] >= u) & (self.dots[uvmap_name + '0'] <= (u + 1)) & (self.dots[uvmap_name + '1'] <= (1-v) ) & (self.dots[uvmap_name + '1'] >= 1-(v + 1)))[0]

                    # Reset UVMap to 0-1 : reset to Blener UVMAP => slide to 0-1 => go to glTF UVMap
                    self.dots[uvmap_name + '1'][indices] -= 1
                    self.dots[uvmap_name + '1'][indices] *= -1
                    self.dots[uvmap_name + '0'][indices] -= u
                    self.dots[uvmap_name + '1'][indices] -= v
                    self.dots[uvmap_name + '1'][indices] *= -1
                    self.dots[uvmap_name + '1'][indices] += 1

                    # Now, get every triangle, and check that it belongs to this tile
                    # Assume that we can check only the first vertex of each triangle (=> No management of triangle on multiple tiles)
                    new_triangle_indices = []
                    for idx, i in enumerate(self.prim_indices[material_idx]):
                        if idx % 3 == 0 and i in indices:
                            new_triangle_indices.append(self.prim_indices[material_idx][idx])
                            new_triangle_indices.append(self.prim_indices[material_idx][idx+1])
                            new_triangle_indices.append(self.prim_indices[material_idx][idx+2])
                    new_prim_indices[new_material_index] = np.array(new_triangle_indices, dtype=np.uint32)
                    new_material_index += 1


                    # Now we have to create a new material for this tile
                    # This will be the existing material, but with new textures
                    # We need to duplicate the material, and add these new textures
                    new_material = deepcopy(base_material)
                    get_new_material_texture_shared(base_material, new_material)

                    for tex in material_info['udim_info'].keys():
                        new_tex = gather_udim_texture_info(
                            material_info['udim_info'][tex]['sockets'][0],
                            material_info['udim_info'][tex]['sockets'],
                            {
                                'tile': "10" + str(v) + str(u+1),
                                'image': material_info['udim_info'][tex]['image']
                            },
                            tex,
                            self.export_settings)

                        if tex == "baseColorTexture":
                            new_material.pbr_metallic_roughness.base_color_texture = new_tex
                        elif tex == "normalTexture":
                            new_material.normal_texture = new_tex
                        elif tex == "emissiveTexture":
                            new_material.emissive_texture = new_tex
                        elif tex == "metallicRoughnessTexture":
                            new_material.pbr_metallic_roughness.metallic_roughness_texture = new_tex
                        elif tex == "occlusionTexture":
                            new_material.occlusion_texture = new_tex
                        elif tex == "clearcoatTexture":
                            new_material.extensions["KHR_materials_clearcoat"].extension['clearcoatTexture'] = new_tex
                        elif tex == "clearcoatRoughnessTexture":
                            new_material.extensions["KHR_materials_clearcoat"].extension['clearcoatRoughnessTexture'] = new_tex
                        elif tex == "clearcoatNormalTexture":
                            new_material.extensions["KHR_materials_clearcoat"].extension['clearcoatNormalTexture'] = new_tex
                        elif tex == "sheenColorTexture":
                            new_material.extensions["KHR_materials_sheen"].extension['sheenColorTexture'] = new_tex
                        elif tex == "sheenRoughnessTexture":
                            new_material.extensions["KHR_materials_sheen"].extension['sheenRoughnessTexture'] = new_tex
                        elif tex == "transmissionTexture":
                            new_material.extensions["KHR_materials_transmission"].extension['transmissionTexture'] = new_tex
                        elif tex == "thicknessTexture":
                            new_material.extensions["KHR_materials_volume"].extension['thicknessTexture'] = new_tex
                        elif tex == "specularTexture":
                            new_material.extensions["KHR_materials_specular"].extension['specularTexture'] = new_tex
                        elif tex == "specularColorTexture":
                            new_material.extensions["KHR_materials_specular"].extension['specularColorTexture'] = new_tex
                        elif tex == "anisotropyTexture":
                            new_material.extensions["KHR_materials_anisotropy"].extension['anisotropyTexture'] = new_tex
                        else:
                            print_console('WARNING', 'We are not managing this case yet (UDIM for {})'.format(tex))

                    self.additional_materials.append((new_material, material_info, int(str(id(base_material)) + str(u) + str(v))))


        self.prim_indices = new_prim_indices

    def primitive_creation_shared(self):
        primitives = []
        self.dots, shared_dot_indices = np.unique(self.dots, return_inverse=True)

        self.blender_idxs = self.dots['vertex_index']

        self.attributes = {}

        next_texcoor_idx = self.tex_coord_max
        uvmap_attributes_index = {}
        for attr in self.uvmap_attribute_list:
            res = np.empty((len(self.dots), 2), dtype=gltf2_blender_conversion.get_numpy_type('FLOAT2'))
            for i in range(2):
                res[:, i] = self.dots[attr + str(i)]

            self.attributes["TEXCOORD_" + str(next_texcoor_idx)] = {}
            self.attributes["TEXCOORD_" + str(next_texcoor_idx)]["data"] = res
            self.attributes["TEXCOORD_" + str(next_texcoor_idx)]["component_type"] = gltf2_io_constants.ComponentType.Float
            self.attributes["TEXCOORD_" + str(next_texcoor_idx)]["data_type"] = gltf2_io_constants.DataType.Vec2
            uvmap_attributes_index[attr] = next_texcoor_idx
            next_texcoor_idx += 1

        for attr in self.blender_attributes:
            if 'set' in attr:
                attr['set'](attr)
            else:
                self.__set_regular_attribute(self.dots, attr)

        if self.skin:
            joints = [[] for _ in range(self.num_joint_sets)]
            weights = [[] for _ in range(self.num_joint_sets)]

            for vi in self.blender_idxs:
                bones = self.vert_bones[vi]
                for j in range(0, 4 * self.num_joint_sets):
                    if j < len(bones):
                        joint, weight = bones[j]
                    else:
                        joint, weight = 0, 0.0
                    joints[j//4].append(joint)
                    weights[j//4].append(weight)

            for i, (js, ws) in enumerate(zip(joints, weights)):
                self.attributes['JOINTS_%d' % i] = js
                self.attributes['WEIGHTS_%d' % i] = ws


        for material_idx, dot_indices in self.prim_indices.items():
            indices = shared_dot_indices[dot_indices]

            if len(indices) == 0:
                continue

            primitives.append({
                # No attribute here, as they are shared accross all primitives
                'indices': indices,
                'material': material_idx,
                'uvmap_attributes_index': uvmap_attributes_index
            })

        # Manage edges & points primitives.
        # One for edges, one for points
        # No material for them, so only one primitive for each
        has_triangle_primitive = len(primitives) != 0
        primitives.extend(self.primitive_creation_edges_and_points())

        print_console('INFO', 'Primitives created: %d' % len(primitives))

        return primitives, [None]*len(primitives), self.attributes if has_triangle_primitive else None

    def primitive_creation_not_shared(self):
        primitives = []

        for material_idx, dot_indices in self.prim_indices.items():
            # Extract just dots used by this primitive, deduplicate them, and
            # calculate indices into this deduplicated list.
            self.prim_dots = self.dots[dot_indices]
            self.prim_dots, indices = np.unique(self.prim_dots, return_inverse=True)

            if len(self.prim_dots) == 0:
                continue

            # Now just move all the data for prim_dots into attribute arrays

            self.attributes = {}

            self.blender_idxs = self.prim_dots['vertex_index']

            for attr in self.blender_attributes:
                if 'set' in attr:
                    attr['set'](attr)
                else: # Regular case
                    self.__set_regular_attribute(self.prim_dots, attr)

            next_texcoor_idx = self.tex_coord_max
            uvmap_attributes_index = {}
            for attr in self.uvmap_attribute_list:
                res = np.empty((len(self.prim_dots), 2), dtype=gltf2_blender_conversion.get_numpy_type('FLOAT2'))
                for i in range(2):
                    res[:, i] = self.prim_dots[attr + str(i)]

                self.attributes["TEXCOORD_" + str(next_texcoor_idx)] = {}
                self.attributes["TEXCOORD_" + str(next_texcoor_idx)]["data"] = res
                self.attributes["TEXCOORD_" + str(next_texcoor_idx)]["component_type"] = gltf2_io_constants.ComponentType.Float
                self.attributes["TEXCOORD_" + str(next_texcoor_idx)]["data_type"] = gltf2_io_constants.DataType.Vec2
                uvmap_attributes_index[attr] = next_texcoor_idx
                next_texcoor_idx += 1


            if self.skin:
                joints = [[] for _ in range(self.num_joint_sets)]
                weights = [[] for _ in range(self.num_joint_sets)]

                for vi in self.blender_idxs:
                    bones = self.vert_bones[vi]
                    for j in range(0, 4 * self.num_joint_sets):
                        if j < len(bones):
                            joint, weight = bones[j]
                        else:
                            joint, weight = 0, 0.0
                        joints[j//4].append(joint)
                        weights[j//4].append(weight)

                for i, (js, ws) in enumerate(zip(joints, weights)):
                    self.attributes['JOINTS_%d' % i] = js
                    self.attributes['WEIGHTS_%d' % i] = ws

            primitives.append({
                'attributes': self.attributes,
                'indices': indices,
                'material': material_idx,
                'uvmap_attributes_index': uvmap_attributes_index
            })

        # Manage edges & points primitives.
        # One for edges, one for points
        # No material for them, so only one primitive for each
        primitives.extend(self.primitive_creation_edges_and_points())

        print_console('INFO', 'Primitives created: %d' % len(primitives))

        return primitives

    def primitive_creation_edges_and_points(self):
        primitives_edges_points = []

        if self.export_settings['gltf_loose_edges']:

            if self.blender_idxs_edges.shape[0] > 0:
                # Export one glTF vert per unique Blender vert in a loose edge
                self.blender_idxs = self.blender_idxs_edges
                dots_edges, indices = np.unique(self.dots_edges, return_inverse=True)
                self.blender_idxs = np.unique(self.blender_idxs_edges)

                self.attributes_edges_points = {}

                for attr in self.blender_attributes:
                    if attr['blender_domain'] != 'POINT':
                        continue
                    if 'set' in attr:
                        attr['set'](attr, edges_points=True)
                    else:
                        res = np.empty((len(dots_edges), attr['len']), dtype=attr['type'])
                        for i in range(attr['len']):
                            res[:, i] = dots_edges[attr['gltf_attribute_name'] + str(i)]
                        self.attributes_edges_points[attr['gltf_attribute_name']] = {}
                        self.attributes_edges_points[attr['gltf_attribute_name']]["data"] = res
                        self.attributes_edges_points[attr['gltf_attribute_name']]["component_type"] = gltf2_blender_conversion.get_component_type(attr['blender_data_type'])
                        self.attributes_edges_points[attr['gltf_attribute_name']]["data_type"] = gltf2_blender_conversion.get_data_type(attr['blender_data_type'])


                if self.skin:
                    joints = [[] for _ in range(self.num_joint_sets)]
                    weights = [[] for _ in range(self.num_joint_sets)]

                    for vi in self.blender_idxs:
                        bones = self.vert_bones[vi]
                        for j in range(0, 4 * self.num_joint_sets):
                            if j < len(bones):
                                joint, weight = bones[j]
                            else:
                                joint, weight = 0, 0.0
                            joints[j//4].append(joint)
                            weights[j//4].append(weight)

                    for i, (js, ws) in enumerate(zip(joints, weights)):
                        self.attributes_edges_points['JOINTS_%d' % i] = js
                        self.attributes_edges_points['WEIGHTS_%d' % i] = ws

                primitives_edges_points.append({
                    'attributes': self.attributes_edges_points,
                    'indices': indices,
                    'mode': 1,  # LINES
                    'material': 0,
                    'uvmap_attributes_index': {}
                })
                self.additional_materials.append(None)

        if self.export_settings['gltf_loose_points']:

            if self.blender_idxs_points.shape[0] > 0:
                self.blender_idxs = self.blender_idxs_points

                self.attributes_edges_points = {}

                for attr in self.blender_attributes:
                    if attr['blender_domain'] != 'POINT':
                        continue
                    if 'set' in attr:
                        attr['set'](attr, edges_points=True)
                    else:
                        res = np.empty((len(self.blender_idxs), attr['len']), dtype=attr['type'])
                        for i in range(attr['len']):
                            res[:, i] = self.dots_points[attr['gltf_attribute_name'] + str(i)]
                        self.attributes_edges_points[attr['gltf_attribute_name']] = {}
                        self.attributes_edges_points[attr['gltf_attribute_name']]["data"] = res
                        self.attributes_edges_points[attr['gltf_attribute_name']]["component_type"] = gltf2_blender_conversion.get_component_type(attr['blender_data_type'])
                        self.attributes_edges_points[attr['gltf_attribute_name']]["data_type"] = gltf2_blender_conversion.get_data_type(attr['blender_data_type'])


                if self.skin:
                    joints = [[] for _ in range(self.num_joint_sets)]
                    weights = [[] for _ in range(self.num_joint_sets)]

                    for vi in self.blender_idxs:
                        bones = self.vert_bones[vi]
                        for j in range(0, 4 * self.num_joint_sets):
                            if j < len(bones):
                                joint, weight = bones[j]
                            else:
                                joint, weight = 0, 0.0
                            joints[j//4].append(joint)
                            weights[j//4].append(weight)

                    for i, (js, ws) in enumerate(zip(joints, weights)):
                        self.attributes_edges_points['JOINTS_%d' % i] = js
                        self.attributes_edges_points['WEIGHTS_%d' % i] = ws

                primitives_edges_points.append({
                    'attributes': self.attributes_edges_points,
                    'mode': 0,  # POINTS
                    'material': 0,
                    'uvmap_attributes_index': {}
                })
                self.additional_materials.append(None)

        return primitives_edges_points

################################## Get ##################################################

    def __get_positions(self):
        self.locs = np.empty(len(self.blender_mesh.vertices) * 3, dtype=np.float32)
        source = self.key_blocks[0].relative_key.data if self.key_blocks else self.blender_mesh.vertices
        source.foreach_get('co', self.locs)
        self.locs = self.locs.reshape(len(self.blender_mesh.vertices), 3)

        self.morph_locs = []
        for key_block in self.key_blocks:
            vs = np.empty(len(self.blender_mesh.vertices) * 3, dtype=np.float32)
            key_block.data.foreach_get('co', vs)
            vs = vs.reshape(len(self.blender_mesh.vertices), 3)
            self.morph_locs.append(vs)

        # Transform for skinning
        if self.armature and self.blender_object:
            # apply_matrix = armature.matrix_world.inverted_safe() @ blender_object.matrix_world
            # loc_transform = armature.matrix_world @ apply_matrix

            loc_transform = self.blender_object.matrix_world
            self.locs[:] = PrimitiveCreator.apply_mat_to_all(loc_transform, self.locs)
            for vs in self.morph_locs:
                vs[:] = PrimitiveCreator.apply_mat_to_all(loc_transform, vs)

        # glTF stores deltas in morph targets
        for vs in self.morph_locs:
            vs -= self.locs
            # Some invalid mesh can have NaN value in SK, so replace them by 0, avoid crash
            np.nan_to_num(vs, copy=False)

        if self.export_settings['gltf_yup']:
            PrimitiveCreator.zup2yup(self.locs)
            for vs in self.morph_locs:
                PrimitiveCreator.zup2yup(vs)

    def get_function(self):

        def getting_function(attr):
            if attr['gltf_attribute_name'].startswith("_"):
                self.__get_layer_attribute(attr)
            elif attr['gltf_attribute_name'].startswith("TEXCOORD_"):
                self.__get_uvs_attribute(int(attr['gltf_attribute_name'].split("_")[-1]), attr)
            elif attr['gltf_attribute_name'] == "NORMAL":
                self.__get_normal_attribute(attr)
            elif attr['gltf_attribute_name'] == "TANGENT":
                self.__get_tangent_attribute(attr)

        return getting_function


    def __manage_color_attribute(self, attr_name, attr_name_alpha):
        blender_color_idx = self.blender_mesh.color_attributes.find(attr_name)
        if blender_color_idx < 0:
            return None

        # Add COLOR_0 in dots data

        attr = self.blender_mesh.color_attributes[blender_color_idx]

        # Get data
        data_dots, data_dots_edges, data_dots_points = self.__get_color_attribute_data(attr)

        # Get data for alpha if needed
        if attr_name_alpha is not None and attr_name_alpha != attr_name:
            blender_alpha_idx = self.blender_mesh.color_attributes.find(attr_name_alpha)
            if blender_alpha_idx >= 0:
                attr_alpha = self.blender_mesh.color_attributes[blender_alpha_idx]
                data_dots_alpha, data_dots_edges_alpha, data_dots_points_alpha = self.__get_color_attribute_data(attr_alpha)
                # Merging data
                data_dots[:, 3] = data_dots_alpha[:, 3]
                if data_dots_edges is not None:
                    data_dots_edges[:, 3] = data_dots_edges_alpha[:, 3]
                if data_dots_points is not None:
                    data_dots_points[:, 3] = data_dots_points_alpha[:, 3]

        # Check if we need to get alpha (the 4th channel) here
        max_index = 4 if attr_name_alpha is not None else 3

        # Add this data to dots structure
        additional_fields = []
        for i in range(max_index):
            # Must calculate the type of the field : FLOAT_COLOR or BYTE_COLOR
            additional_fields.append(('COLOR_0' + str(i), gltf2_blender_conversion.get_numpy_type('FLOAT_COLOR' if max_index == 3 else 'BYTE_COLOR')))


        if self.export_settings['gltf_loose_edges']:
            additional_fields_edges = []
            for i in range(max_index):
                # Must calculate the type of the field : FLOAT_COLOR or BYTE_COLOR
                additional_fields_edges.append(('COLOR_0' + str(i), gltf2_blender_conversion.get_numpy_type('FLOAT_COLOR' if max_index == 3 else 'BYTE_COLOR')))

            new_dt = np.dtype(self.dots_edges.dtype.descr + additional_fields_edges)
            dots_edges = np.zeros(self.dots_edges.shape, dtype=new_dt)
            for f in self.dots_edges.dtype.names:
                dots_edges[f] = self.dots_edges[f]

            self.dots_edges = dots_edges

        if self.export_settings['gltf_loose_points']:
            additional_fields_points = []
            for i in range(max_index):
                # Must calculate the type of the field : FLOAT_COLOR or BYTE_COLOR
                additional_fields_points.append(('COLOR_0' + str(i), gltf2_blender_conversion.get_numpy_type('FLOAT_COLOR' if max_index == 3 else 'BYTE_COLOR')))

            new_dt = np.dtype(self.dots_points.dtype.descr + additional_fields_points)
            dots_points = np.zeros(self.dots_points.shape, dtype=new_dt)
            for f in self.dots_points.dtype.names:
                dots_points[f] = self.dots_points[f]

            self.dots_points = dots_points

        # Keep the existing custom attribute
        # Data will be exported twice, one for COLOR_O, one for the custom attribute
        new_dt = np.dtype(self.dots.dtype.descr + additional_fields)
        dots = np.zeros(self.dots.shape, dtype=new_dt)
        for f in self.dots.dtype.names:
            dots[f] = self.dots[f]

        self.dots = dots

        # colors are already linear, no need to switch color space
        for i in range(max_index):
            self.dots['COLOR_0' +str(i)] = data_dots[:, i]
            if self.export_settings['gltf_loose_edges'] and attr.domain == "POINT":
                self.dots_edges['COLOR_0' + str(i)] = data_dots_edges[:, i]
            if self.export_settings['gltf_loose_points'] and attr.domain == "POINT":
                self.dots_points['COLOR_0' + str(i)] = data_dots_points[:, i]

        # Add COLOR_0 in attribute list
        attr_color_0 = {}
        attr_color_0['blender_data_type'] = 'FLOAT_COLOR' if max_index == 3 else 'BYTE_COLOR'
        attr_color_0['blender_domain'] = attr.domain
        attr_color_0['gltf_attribute_name'] = 'COLOR_0'
        attr_color_0['len'] = max_index # 3 or 4, depending if we have alpha
        attr_color_0['type'] = gltf2_blender_conversion.get_numpy_type(attr_color_0['blender_data_type'])
        attr_color_0['component_type'] = gltf2_blender_conversion.get_component_type(attr_color_0['blender_data_type'])
        attr_color_0['data_type'] = gltf2_io_constants.DataType.Vec3 if max_index == 3 else gltf2_io_constants.DataType.Vec4

        self.blender_attributes.append(attr_color_0)

    def __get_color_attribute_data(self, attr):
        data_dots_edges = None
        data_dots_points = None

        if attr.domain == "POINT":
            colors = np.empty(len(self.blender_mesh.vertices) * 4, dtype=np.float32)
        elif attr.domain == "CORNER":
            colors = np.empty(len(self.blender_mesh.loops) * 4, dtype=np.float32)
        attr.data.foreach_get('color', colors)
        if attr.domain == "POINT":
            colors = colors.reshape(-1, 4)
            data_dots = colors[self.dots['vertex_index']]
            if self.export_settings['gltf_loose_edges']:
                data_dots_edges = colors[self.dots_edges['vertex_index']]
            if self.export_settings['gltf_loose_points']:
                data_dots_points = colors[self.dots_points['vertex_index']]

        elif attr.domain == "CORNER":
            colors = colors.reshape(-1, 4)
            data_dots = colors

        del colors

        return data_dots, data_dots_edges, data_dots_points

    def __get_layer_attribute(self, attr):
        if attr['blender_domain'] in ['CORNER']:
            data = np.empty(len(self.blender_mesh.loops) * attr['len'], dtype=attr['type'])
        elif attr['blender_domain'] in ['POINT']:
            data = np.empty(len(self.blender_mesh.vertices) * attr['len'], dtype=attr['type'])
        elif attr['blender_domain'] in ['EDGE']:
            data = np.empty(len(self.blender_mesh.edges) * attr['len'], dtype=attr['type'])
        elif attr['blender_domain'] in ['FACE']:
            data = np.empty(len(self.blender_mesh.polygons) * attr['len'], dtype=attr['type'])
        else:
            print_console("ERROR", "domain not known")

        if attr['blender_data_type'] == "BYTE_COLOR":
            self.blender_mesh.attributes[attr['blender_attribute_index']].data.foreach_get('color', data)
            data = data.reshape(-1, attr['len'])
        elif attr['blender_data_type'] == "INT8":
            self.blender_mesh.attributes[attr['blender_attribute_index']].data.foreach_get('value', data)
            data = data.reshape(-1, attr['len'])
        elif attr['blender_data_type'] == "FLOAT2":
            self.blender_mesh.attributes[attr['blender_attribute_index']].data.foreach_get('vector', data)
            data = data.reshape(-1, attr['len'])
        elif attr['blender_data_type'] == "BOOLEAN":
            self.blender_mesh.attributes[attr['blender_attribute_index']].data.foreach_get('value', data)
            data = data.reshape(-1, attr['len'])
        elif attr['blender_data_type'] == "STRING":
            self.blender_mesh.attributes[attr['blender_attribute_index']].data.foreach_get('value', data)
            data = data.reshape(-1, attr['len'])
        elif attr['blender_data_type'] == "FLOAT_COLOR":
            self.blender_mesh.attributes[attr['blender_attribute_index']].data.foreach_get('color', data)
            data = data.reshape(-1, attr['len'])
        elif attr['blender_data_type'] == "FLOAT_VECTOR":
            self.blender_mesh.attributes[attr['blender_attribute_index']].data.foreach_get('vector', data)
            data = data.reshape(-1, attr['len'])
        elif attr['blender_data_type'] == "FLOAT_VECTOR_4": # Specific case for tangent
            pass
        elif attr['blender_data_type'] == "INT":
            self.blender_mesh.attributes[attr['blender_attribute_index']].data.foreach_get('value', data)
            data = data.reshape(-1, attr['len'])
        elif attr['blender_data_type'] == "FLOAT":
            self.blender_mesh.attributes[attr['blender_attribute_index']].data.foreach_get('value', data)
            data = data.reshape(-1, attr['len'])
        else:
            print_console('ERROR',"blender type not found " +  attr['blender_data_type'])

        if attr['blender_domain'] in ['CORNER']:
            for i in range(attr['len']):
                self.dots[attr['gltf_attribute_name'] + str(i)] = data[:, i]
        elif attr['blender_domain'] in ['POINT']:
            if attr['len'] > 1:
                data = data.reshape(-1, attr['len'])
            data_dots = data[self.dots['vertex_index']]
            if self.export_settings['gltf_loose_edges']:
                data_dots_edges = data[self.dots_edges['vertex_index']]
            if self.export_settings['gltf_loose_points']:
                data_dots_points = data[self.dots_points['vertex_index']]
            for i in range(attr['len']):
                self.dots[attr['gltf_attribute_name'] + str(i)] = data_dots[:, i]
                if self.export_settings['gltf_loose_edges']:
                    self.dots_edges[attr['gltf_attribute_name'] + str(i)] = data_dots_edges[:, i]
                if self.export_settings['gltf_loose_points']:
                    self.dots_points[attr['gltf_attribute_name'] + str(i)] = data_dots_points[:, i]
        elif attr['blender_domain'] in ['EDGE']:
            # No edge attribute exports
            pass
        elif attr['blender_domain'] in ['FACE']:
            if attr['len'] > 1:
                data = data.reshape(-1, attr['len'])
            # data contains face attribute, and is len(faces) long
            # We need to dispatch these len(faces) attribute in each dots lines
            data_attr = np.empty(self.dots.shape[0] * attr['len'], dtype=attr['type'])
            data_attr = data_attr.reshape(-1, attr['len'])
            for idx, poly in enumerate(self.blender_mesh.polygons):
                data_attr[list(poly.loop_indices)] = data[idx]
            data_attr = data_attr.reshape(-1, attr['len'])
            for i in range(attr['len']):
                self.dots[attr['gltf_attribute_name'] + str(i)] = data_attr[:, i]

        else:
            print_console("ERROR", "domain not known")

    def __get_uvs_attribute(self, blender_uv_idx, attr):
        layer = self.blender_mesh.uv_layers[blender_uv_idx]
        uvs = np.empty(len(self.blender_mesh.loops) * 2, dtype=np.float32)
        layer.data.foreach_get('uv', uvs)
        uvs = uvs.reshape(len(self.blender_mesh.loops), 2)

        # Blender UV space -> glTF UV space
        # u,v -> u,1-v
        uvs[:, 1] *= -1
        uvs[:, 1] += 1

        self.dots[attr['gltf_attribute_name'] + '0'] = uvs[:, 0]
        self.dots[attr['gltf_attribute_name'] + '1'] = uvs[:, 1]
        del uvs

    def __get_normals_from_shape_keys(self, key_blocks):
        """
        Access to shape key normals through ShapeKey.normals_split_get() is slow because it returns a tuple. As a
        workaround, a temporary copy of the mesh is made and then each shape key's normals can be extracted from the
        mesh by copying the shape key's coordinates into the mesh's 'position' attribute, updating the mesh's normals
        and finally extracting the normals from the mesh's `corner_normals` property.
        """
        if len(self.blender_mesh.vertices) == 0:
            # Add a zero-length normals array for each shape key.
            for _ in range(len(key_blocks)):
                ns = np.empty((0, 3), dtype=np.float32)
                self.morph_normals.append(ns)
            return

        # Rather than creating a copy of `self.blender_mesh`, which would also copy the shape keys, create a
        # temporary mesh owned by the Object with Object.to_mesh() because that only copies the mesh.
        # Creating a copy avoids modifying the mesh that is being exported.
        if self.blender_object and self.blender_object.data == self.blender_mesh:
            tmp_object = None
            tmp_mesh = self.blender_object.to_mesh()
        else:
            # Create a temporary object with the mesh as its data.
            tmp_object = bpy.data.objects.new("", self.blender_mesh)
            tmp_mesh = tmp_object.to_mesh()

        # Re-usable storage array for shape key coordinates.
        coordinates_storage = np.empty(len(self.blender_mesh.vertices) * 3, dtype=np.float32)

        def put_shape_key_normals_into(shape_key, normals_array):
            # Workaround for slow access to shape key normals through ShapeKey.normals_split_get():
            # Copy the shape key coordinates into the position attribute.
            shape_key.points.foreach_get('co', coordinates_storage)
            tmp_mesh.attributes['position'].data.foreach_set('vector', coordinates_storage)
            # Force normals to be recalculated.
            tmp_mesh.update()
            # Extract corner normals from the mesh.
            tmp_mesh.corner_normals.foreach_get('vector', normals_array)

        # Set self.normals from the normals of the relative key of the first shape key.
        base_key = key_blocks[0].relative_key
        put_shape_key_normals_into(base_key, self.normals)

        # Get and append the normals for the shape keys.
        for key_block in key_blocks:
            if key_block == base_key:
                # The shape key's normals were already retrieved and set into `self.normals`, so copy `self.normals`.
                ns = self.normals.copy()
            else:
                ns = np.empty_like(self.normals)
                put_shape_key_normals_into(key_block, ns)
            ns = ns.reshape(len(self.blender_mesh.loops), 3)
            ns = np.round(ns, ROUNDING_DIGIT)
            self.morph_normals.append(ns)

        # Clean up temporary data.
        if tmp_object is None:
            # Clear the temporary mesh created by `self.blender_object.to_mesh()`.
            self.blender_object.to_mesh_clear()
        else:
            # Remove the temporary Object.
            bpy.data.objects.remove(tmp_object, do_unlink=False, do_id_user=False, do_ui_user=False)

    def __get_normals(self):
        """Get normal for each loop."""
        key_blocks = self.key_blocks if self.use_morph_normals else []
        self.normals = np.empty(len(self.blender_mesh.loops) * 3, dtype=np.float32)
        self.morph_normals = []
        if key_blocks:
            self.__get_normals_from_shape_keys(key_blocks)
        else:
            self.blender_mesh.loops.foreach_get('normal', self.normals)

        self.normals = self.normals.reshape(len(self.blender_mesh.loops), 3)

        self.normals = np.round(self.normals, ROUNDING_DIGIT)
        # Force normalization of normals in case some normals are not (why ?)
        PrimitiveCreator.normalize_vecs(self.normals)

        # Transform for skinning
        if self.armature and self.blender_object:
            apply_matrix = (self.armature.matrix_world.inverted_safe() @ self.blender_object.matrix_world)
            apply_matrix = apply_matrix.to_3x3().inverted_safe().transposed()
            normal_transform = self.armature.matrix_world.to_3x3() @ apply_matrix

            self.normals[:] = PrimitiveCreator.apply_mat_to_all(normal_transform, self.normals)
            PrimitiveCreator.normalize_vecs(self.normals)
            for ns in self.morph_normals:
                ns[:] = PrimitiveCreator.apply_mat_to_all(normal_transform, ns)
                PrimitiveCreator.normalize_vecs(ns)

        for ns in [self.normals, *self.morph_normals]:
            # Replace zero normals with the unit UP vector.
            # Seems to happen sometimes with degenerate tris?
            is_zero = ~ns.any(axis=1)
            ns[is_zero, 2] = 1

        # glTF stores deltas in morph targets
        for ns in self.morph_normals:
            ns -= self.normals

        if self.export_settings['gltf_yup']:
            PrimitiveCreator.zup2yup(self.normals)
            for ns in self.morph_normals:
                PrimitiveCreator.zup2yup(ns)

    def __get_normal_attribute(self, attr):
        self.__get_normals()
        self.dots[attr['gltf_attribute_name'] + "0"] = self.normals[:, 0]
        self.dots[attr['gltf_attribute_name'] + "1"] = self.normals[:, 1]
        self.dots[attr['gltf_attribute_name'] + "2"] = self.normals[:, 2]

        if self.use_morph_normals:
            for morph_i, ns in enumerate(self.morph_normals):
                self.dots[attr['gltf_attribute_name_morph'] + str(morph_i) + "0"] = ns[:, 0]
                self.dots[attr['gltf_attribute_name_morph'] + str(morph_i) + "1"] = ns[:, 1]
                self.dots[attr['gltf_attribute_name_morph'] + str(morph_i) + "2"] = ns[:, 2]
            del self.normals
            del self.morph_normals

    def __get_tangent_attribute(self, attr):
        self.__get_tangents()
        self.dots[attr['gltf_attribute_name'] + "0"] = self.tangents[:, 0]
        self.dots[attr['gltf_attribute_name'] + "1"] = self.tangents[:, 1]
        self.dots[attr['gltf_attribute_name'] + "2"] = self.tangents[:, 2]
        del self.tangents
        self.__get_bitangent_signs()
        self.dots[attr['gltf_attribute_name'] + "3"] = self.signs
        del self.signs

    def __get_tangents(self):
        """Get an array of the tangent for each loop."""
        self.tangents = np.empty(len(self.blender_mesh.loops) * 3, dtype=np.float32)
        self.blender_mesh.loops.foreach_get('tangent', self.tangents)
        self.tangents = self.tangents.reshape(len(self.blender_mesh.loops), 3)
        self.tangents = np.round(self.tangents, ROUNDING_DIGIT)

        # Transform for skinning
        if self.armature and self.blender_object:
            apply_matrix = self.armature.matrix_world.inverted_safe() @ self.blender_object.matrix_world
            tangent_transform = apply_matrix.to_quaternion().to_matrix()
            self.tangents = PrimitiveCreator.apply_mat_to_all(tangent_transform, self.tangents)
            PrimitiveCreator.normalize_vecs(self.tangents)
            self.tangents = np.round(self.tangents, ROUNDING_DIGIT)

        if self.export_settings['gltf_yup']:
            PrimitiveCreator.zup2yup(self.tangents)


    def __get_bitangent_signs(self):
        self.signs = np.empty(len(self.blender_mesh.loops), dtype=np.float32)
        self.blender_mesh.loops.foreach_get('bitangent_sign', self.signs)

        # Transform for skinning
        if self.armature and self.blender_object:
            # Bitangent signs should flip when handedness changes
            # TODO: confirm
            apply_matrix = self.armature.matrix_world.inverted_safe() @ self.blender_object.matrix_world
            tangent_transform = apply_matrix.to_quaternion().to_matrix()
            flipped = tangent_transform.determinant() < 0
            if flipped:
                self.signs *= -1

        # No change for Zup -> Yup


    def __get_bone_data(self):

        self.need_neutral_bone = False
        min_influence = 0.0001

        joint_name_to_index = {joint.name: index for index, joint in enumerate(self.skin.joints)}
        group_to_joint = [joint_name_to_index.get(g.name) for g in self.blender_vertex_groups]

        # List of (joint, weight) pairs for each vert
        self.vert_bones = []
        max_num_influences = 0

        for vertex in self.blender_mesh.vertices:
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
                bones = ((len(self.skin.joints), 1.0),)  # Assign to a joint that will be created later
                self.need_neutral_bone = True
            self.vert_bones.append(bones)
            if len(bones) > max_num_influences:
                max_num_influences = len(bones)

        # How many joint sets do we need? 1 set = 4 influences
        self.num_joint_sets = (max_num_influences + 3) // 4

##################################### Set ###################################
    def set_function(self):

        def setting_function(attr, edges_points=False):
            if attr['gltf_attribute_name'] == "POSITION":
                self.__set_positions_attribute(attr, edges_points=edges_points)
            elif attr['gltf_attribute_name'].startswith("MORPH_POSITION_"):
                self.__set_morph_locs_attribute(attr, edges_points=edges_points)
            elif attr['gltf_attribute_name'].startswith("MORPH_TANGENT_"):
                self.__set_morph_tangent_attribute(attr, edges_points=edges_points)

        return setting_function

    def __set_positions_attribute(self, attr, edges_points=False):
        if edges_points is False:
            self.attributes[attr['gltf_attribute_name']] = {}
            self.attributes[attr['gltf_attribute_name']]["data"] = self.locs[self.blender_idxs]
            self.attributes[attr['gltf_attribute_name']]["data_type"] = gltf2_io_constants.DataType.Vec3
            self.attributes[attr['gltf_attribute_name']]["component_type"] = gltf2_io_constants.ComponentType.Float
        else:
            self.attributes_edges_points[attr['gltf_attribute_name']] = {}
            self.attributes_edges_points[attr['gltf_attribute_name']]["data"] = self.locs[self.blender_idxs]
            self.attributes_edges_points[attr['gltf_attribute_name']]["data_type"] = gltf2_io_constants.DataType.Vec3
            self.attributes_edges_points[attr['gltf_attribute_name']]["component_type"] = gltf2_io_constants.ComponentType.Float


    def __set_morph_locs_attribute(self, attr, edges_points=False):
        if edges_points is False:
            self.attributes[attr['gltf_attribute_name']] = {}
            self.attributes[attr['gltf_attribute_name']]["data"] = self.morph_locs[attr['blender_attribute_index']][self.blender_idxs]
        else:
            self.attributes_edges_points[attr['gltf_attribute_name']] = {}
            self.attributes_edges_points[attr['gltf_attribute_name']]["data"] = self.morph_locs[attr['blender_attribute_index']][self.blender_idxs]

    def __set_morph_tangent_attribute(self, attr, edges_points=False):
        # Morph tangent are after these 3 others, so, they are already calculated
        self.normals = self.attributes[attr['gltf_attribute_name_normal']]["data"]
        self.morph_normals = self.attributes[attr['gltf_attribute_name_morph_normal']]["data"]
        self.tangents = self.attributes[attr['gltf_attribute_name_tangent']]["data"]

        self.__calc_morph_tangents()
        if edges_points is False:
            self.attributes[attr['gltf_attribute_name']] = {}
            self.attributes[attr['gltf_attribute_name']]["data"] = self.morph_tangents
        else:
            self.attributes_edges_points[attr['gltf_attribute_name']] = {}
            self.attributes_edges_points[attr['gltf_attribute_name']]["data"] = self.morph_tangents

    def __calc_morph_tangents(self):
        # TODO: check if this works
        self.morph_tangents = np.empty((len(self.normals), 3), dtype=np.float32)

        for i in range(len(self.normals)):
            n = Vector(self.normals[i])
            morph_n = n + Vector(self.morph_normals[i])  # convert back to non-delta
            t = Vector(self.tangents[i, :3])

            rotation = morph_n.rotation_difference(n)

            t_morph = Vector(t)
            t_morph.rotate(rotation)
            self.morph_tangents[i] = t_morph - t  # back to delta

    def __set_regular_attribute(self, dots, attr):
            res = np.empty((len(dots), attr['len']), dtype=attr['type'])
            for i in range(attr['len']):
                res[:, i] = dots[attr['gltf_attribute_name'] + str(i)]
            self.attributes[attr['gltf_attribute_name']] = {}
            self.attributes[attr['gltf_attribute_name']]["data"] = res
            if attr['gltf_attribute_name'] == "NORMAL":
                self.attributes[attr['gltf_attribute_name']]["component_type"] = gltf2_io_constants.ComponentType.Float
                self.attributes[attr['gltf_attribute_name']]["data_type"] = gltf2_io_constants.DataType.Vec3
            elif attr['gltf_attribute_name'] == "TANGENT":
                self.attributes[attr['gltf_attribute_name']]["component_type"] = gltf2_io_constants.ComponentType.Float
                self.attributes[attr['gltf_attribute_name']]["data_type"] = gltf2_io_constants.DataType.Vec4
            elif attr['gltf_attribute_name'].startswith('TEXCOORD_'):
                self.attributes[attr['gltf_attribute_name']]["component_type"] = gltf2_io_constants.ComponentType.Float
                self.attributes[attr['gltf_attribute_name']]["data_type"] = gltf2_io_constants.DataType.Vec2
            elif attr['gltf_attribute_name'].startswith('COLOR_'):
                # This is already managed, we only have to copy
                self.attributes[attr['gltf_attribute_name']]["component_type"] = attr['component_type']
                self.attributes[attr['gltf_attribute_name']]["data_type"] = attr['data_type']
            else:
                self.attributes[attr['gltf_attribute_name']]["component_type"] = gltf2_blender_conversion.get_component_type(attr['blender_data_type'])
                self.attributes[attr['gltf_attribute_name']]["data_type"] = gltf2_blender_conversion.get_data_type(attr['blender_data_type'])
