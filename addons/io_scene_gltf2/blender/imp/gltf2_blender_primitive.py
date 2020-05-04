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
from mathutils import Vector, Matrix

from ...io.imp.gltf2_io_binary import BinaryData
from ...io.com.gltf2_io_color_management import color_linear_to_srgb
from ...io.com import gltf2_io_debug


MAX_NUM_COLOR_SETS = 8
MAX_NUM_TEXCOORD_SETS = 8

class BlenderPrimitive():
    """Blender Primitive."""
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("%s should not be instantiated" % cls)

    @staticmethod
    def get_layer(bme_layers, name):
        if name not in bme_layers:
            return bme_layers.new(name)
        return bme_layers[name]

    @staticmethod
    def add_primitive_to_bmesh(gltf, bme, pymesh, pyprimitive, skin_idx, material_index):
        attributes = pyprimitive.attributes

        if 'POSITION' not in attributes:
            pyprimitive.num_faces = 0
            return

        positions = BinaryData.get_data_from_accessor(gltf, attributes['POSITION'], cache=True)

        if pyprimitive.indices is not None:
            # Not using cache, this is not useful for indices
            indices = BinaryData.get_data_from_accessor(gltf, pyprimitive.indices)
            indices = [i[0] for i in indices]
        else:
            indices = list(range(len(positions)))

        bme_verts = bme.verts
        bme_edges = bme.edges
        bme_faces = bme.faces

        # Gather up the joints/weights (multiple sets allow >4 influences)
        joint_sets = []
        weight_sets = []
        set_num = 0
        while 'JOINTS_%d' % set_num in attributes and 'WEIGHTS_%d' % set_num in attributes:
            joint_data = BinaryData.get_data_from_accessor(gltf, attributes['JOINTS_%d' % set_num], cache=True)
            weight_data = BinaryData.get_data_from_accessor(gltf, attributes['WEIGHTS_%d' % set_num], cache=True)

            joint_sets.append(joint_data)
            weight_sets.append(weight_data)

            set_num += 1

        # For skinned meshes, we will need to calculate the position of the
        # verts in the bind pose, ie. the pose the edit bones are in.
        if skin_idx is not None:
            pyskin = gltf.data.skins[skin_idx]
            if pyskin.inverse_bind_matrices is not None:
                inv_binds = BinaryData.get_data_from_accessor(gltf, pyskin.inverse_bind_matrices)
                inv_binds = [gltf.matrix_gltf_to_blender(m) for m in inv_binds]
            else:
                inv_binds = [Matrix.Identity(4) for i in range(len(pyskin.joints))]
            bind_mats = [gltf.vnodes[joint].bind_arma_mat for joint in pyskin.joints]
            joint_mats = [bind_mat @ inv_bind for bind_mat, inv_bind in zip(bind_mats, inv_binds)]

            def skin_vert(pos, pidx):
                out = Vector((0, 0, 0))
                # Spec says weights should already sum to 1 but some models
                # don't do it (ex. CesiumMan), so normalize.
                weight_sum = 0
                for joint_set, weight_set in zip(joint_sets, weight_sets):
                    for j in range(0, 4):
                        weight = weight_set[pidx][j]
                        if weight != 0.0:
                            weight_sum += weight
                            joint = joint_set[pidx][j]
                            out += weight * (joint_mats[joint] @ pos)
                out /= weight_sum
                return out

            def skin_normal(norm, pidx):
                # TODO: not sure this is right
                norm = Vector([norm[0], norm[1], norm[2], 0])
                out = Vector((0, 0, 0, 0))
                weight_sum = 0
                for joint_set, weight_set in zip(joint_sets, weight_sets):
                    for j in range(0, 4):
                        weight = weight_set[pidx][j]
                        if weight != 0.0:
                            weight_sum += weight
                            joint = joint_set[pidx][j]
                            out += weight * (joint_mats[joint] @ norm)
                out /= weight_sum
                out = out.to_3d().normalized()
                return out

        # Every vertex has an index into the primitive's attribute arrays and a
        #  *different* index into the BMesh's list of verts. Call the first one the
        #  pidx and the second the bidx. Need to keep them straight!

        # The pidx of all the vertices that are actually used by the primitive (only
        # indices that appear in the pyprimitive.indices list are actually used)
        used_pidxs = set(indices)
        # Contains a pair (bidx, pidx) for every vertex in the primitive
        vert_idxs = []
        # pidx_to_bidx[pidx] will be the bidx of the vertex with that pidx (or -1 if
        # unused)
        pidx_to_bidx = [-1] * len(positions)
        bidx = len(bme_verts)
        if bpy.app.debug:
            used_pidxs = list(used_pidxs)
            used_pidxs.sort()
        for pidx in used_pidxs:
            pos = gltf.loc_gltf_to_blender(positions[pidx])
            if skin_idx is not None:
                pos = skin_vert(pos, pidx)

            bme_verts.new(pos)
            vert_idxs.append((bidx, pidx))
            pidx_to_bidx[pidx] = bidx
            bidx += 1
        bme_verts.ensure_lookup_table()

        # Add edges/faces to bmesh
        mode = 4 if pyprimitive.mode is None else pyprimitive.mode
        edges, faces = BlenderPrimitive.edges_and_faces(mode, indices)
        # NOTE: edges and vertices are in terms of pidxs!
        for edge in edges:
            try:
                bme_edges.new((
                    bme_verts[pidx_to_bidx[edge[0]]],
                    bme_verts[pidx_to_bidx[edge[1]]],
                ))
            except ValueError:
                # Ignores duplicate/degenerate edges
                pass
        pyprimitive.num_faces = 0
        for face in faces:
            try:
                face = bme_faces.new((
                    bme_verts[pidx_to_bidx[face[0]]],
                    bme_verts[pidx_to_bidx[face[1]]],
                    bme_verts[pidx_to_bidx[face[2]]],
                ))

                if material_index is not None:
                    face.material_index = material_index

                pyprimitive.num_faces += 1

            except ValueError:
                # Ignores duplicate/degenerate faces
                pass

        # Set normals
        if 'NORMAL' in attributes:
            normals = BinaryData.get_data_from_accessor(gltf, attributes['NORMAL'], cache=True)

            if skin_idx is None:
                for bidx, pidx in vert_idxs:
                    bme_verts[bidx].normal = gltf.normal_gltf_to_blender(normals[pidx])
            else:
                for bidx, pidx in vert_idxs:
                    normal = gltf.normal_gltf_to_blender(normals[pidx])
                    bme_verts[bidx].normal = skin_normal(normal, pidx)

        # Set vertex colors. Add them in the order COLOR_0, COLOR_1, etc.
        set_num = 0
        while 'COLOR_%d' % set_num in attributes:
            if set_num >= MAX_NUM_COLOR_SETS:
                gltf2_io_debug.print_console("WARNING",
                    "too many color sets; COLOR_%d will be ignored" % set_num
                )
                break

            layer_name = 'Col' if set_num == 0 else 'Col.%03d' % set_num
            layer = BlenderPrimitive.get_layer(bme.loops.layers.color, layer_name)

            colors = BinaryData.get_data_from_accessor(gltf, attributes['COLOR_%d' % set_num], cache=True)
            is_rgba = len(colors[0]) == 4

            for bidx, pidx in vert_idxs:
                color = colors[pidx]
                col = (
                    color_linear_to_srgb(color[0]),
                    color_linear_to_srgb(color[1]),
                    color_linear_to_srgb(color[2]),
                    color[3] if is_rgba else 1.0,
                )
                for loop in bme_verts[bidx].link_loops:
                    loop[layer] = col

            set_num += 1

        # Set texcoords
        set_num = 0
        while 'TEXCOORD_%d' % set_num in attributes:
            if set_num >= MAX_NUM_TEXCOORD_SETS:
                gltf2_io_debug.print_console("WARNING",
                    "too many UV sets; TEXCOORD_%d will be ignored" % set_num
                )
                break

            layer_name = 'UVMap' if set_num == 0 else 'UVMap.%03d' % set_num
            layer = BlenderPrimitive.get_layer(bme.loops.layers.uv, layer_name)

            uvs = BinaryData.get_data_from_accessor(gltf, attributes['TEXCOORD_%d' % set_num], cache=True)

            for bidx, pidx in vert_idxs:
                # UV transform
                u, v = uvs[pidx]
                uv = (u, 1 - v)

                for loop in bme_verts[bidx].link_loops:
                    loop[layer].uv = uv

            set_num += 1

        # Set joints/weights for skinning
        if joint_sets:
            layer = BlenderPrimitive.get_layer(bme.verts.layers.deform, 'Vertex Weights')

            for joint_set, weight_set in zip(joint_sets, weight_sets):
                for bidx, pidx in vert_idxs:
                    for j in range(0, 4):
                        weight = weight_set[pidx][j]
                        if weight != 0.0:
                            joint = joint_set[pidx][j]
                            bme_verts[bidx][layer][joint] = weight

        # Set morph target positions (no normals/tangents)
        for sk, target in enumerate(pyprimitive.targets or []):
            if pymesh.shapekey_names[sk] is None:
                continue

            layer_name = pymesh.shapekey_names[sk]
            layer = BlenderPrimitive.get_layer(bme.verts.layers.shape, layer_name)

            morph_positions = BinaryData.get_data_from_accessor(gltf, target['POSITION'], cache=True)

            if skin_idx is None:
                for bidx, pidx in vert_idxs:
                    bme_verts[bidx][layer] = (
                        gltf.loc_gltf_to_blender(positions[pidx]) +
                        gltf.loc_gltf_to_blender(morph_positions[pidx])
                    )
            else:
                for bidx, pidx in vert_idxs:
                    pos = (
                        gltf.loc_gltf_to_blender(positions[pidx]) +
                        gltf.loc_gltf_to_blender(morph_positions[pidx])
                    )
                    bme_verts[bidx][layer] = skin_vert(pos, pidx)

    @staticmethod
    def edges_and_faces(mode, indices):
        """Converts the indices in a particular primitive mode into standard lists of
        edges (pairs of indices) and faces (tuples of CCW indices).
        """
        es = []
        fs = []

        if mode == 0:
            # POINTS
            pass
        elif mode == 1:
            # LINES
            #   1   3
            #  /   /
            # 0   2
            es = [
                (indices[i], indices[i + 1])
                for i in range(0, len(indices), 2)
            ]
        elif mode == 2:
            # LINE LOOP
            #   1---2
            #  /     \
            # 0-------3
            es = [
                (indices[i], indices[i + 1])
                for i in range(0, len(indices) - 1)
            ]
            es.append((indices[-1], indices[0]))
        elif mode == 3:
            # LINE STRIP
            #   1---2
            #  /     \
            # 0       3
            es = [
                (indices[i], indices[i + 1])
                for i in range(0, len(indices) - 1)
            ]
        elif mode == 4:
            # TRIANGLES
            #   2     3
            #  / \   / \
            # 0---1 4---5
            fs = [
                (indices[i], indices[i + 1], indices[i + 2])
                for i in range(0, len(indices), 3)
            ]
        elif mode == 5:
            # TRIANGLE STRIP
            # 0---2---4
            #  \ / \ /
            #   1---3
            def alternate(i, xs):
                even = i % 2 == 0
                return xs if even else (xs[0], xs[2], xs[1])
            fs = [
                alternate(i, (indices[i], indices[i + 1], indices[i + 2]))
                for i in range(0, len(indices) - 2)
            ]
        elif mode == 6:
            # TRIANGLE FAN
            #   3---2
            #  / \ / \
            # 4---0---1
            fs = [
                (indices[0], indices[i], indices[i + 1])
                for i in range(1, len(indices) - 1)
            ]
        else:
            raise Exception('primitive mode unimplemented: %d' % mode)

        return es, fs
