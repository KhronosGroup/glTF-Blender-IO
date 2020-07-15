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
import numpy as np

from ...io.imp.gltf2_io_binary import BinaryData
from ..com.gltf2_blender_extras import set_extras
from .gltf2_blender_material import BlenderMaterial


class BlenderMesh():
    """Blender Mesh."""
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("%s should not be instantiated" % cls)

    @staticmethod
    def create(gltf, mesh_idx, skin_idx):
        """Mesh creation."""
        return create_mesh(gltf, mesh_idx, skin_idx)


# Maximum number of TEXCOORD_n/COLOR_n sets to import
UV_MAX = 8
COLOR_MAX = 8


def create_mesh(gltf, mesh_idx, skin_idx):
    pymesh = gltf.data.meshes[mesh_idx]
    name = pymesh.name or 'Mesh_%d' % mesh_idx
    mesh = bpy.data.meshes.new(name)

    # Temporarily parent the mesh to an object.
    # This is used to set skin weights and shapekeys.
    tmp_ob = None
    try:
        tmp_ob = bpy.data.objects.new('##gltf-import:tmp-object##', mesh)
        do_primitives(gltf, mesh_idx, skin_idx, mesh, tmp_ob)

    finally:
        if tmp_ob:
            bpy.data.objects.remove(tmp_ob)

    return mesh


def do_primitives(gltf, mesh_idx, skin_idx, mesh, ob):
    """Put all primitive data into the mesh."""
    pymesh = gltf.data.meshes[mesh_idx]

    # Scan the primitives to find out what we need to create

    has_normals = False
    num_uvs = 0
    num_cols = 0
    num_joint_sets = 0
    for prim in pymesh.primitives:
        if 'POSITION' not in prim.attributes:
            continue

        if gltf.import_settings['import_shading'] == "NORMALS":
            if 'NORMAL' in prim.attributes:
                has_normals = True

        if skin_idx is not None:
            i = 0
            while ('JOINTS_%d' % i) in prim.attributes and \
                    ('WEIGHTS_%d' % i) in prim.attributes:
                i += 1
            num_joint_sets = max(i, num_joint_sets)

        i = 0
        while i < UV_MAX and ('TEXCOORD_%d' % i) in prim.attributes: i += 1
        num_uvs = max(i, num_uvs)

        i = 0
        while i < COLOR_MAX and ('COLOR_%d' % i) in prim.attributes: i += 1
        num_cols = max(i, num_cols)

    num_shapekeys = 0
    for morph_i, _ in enumerate(pymesh.primitives[0].targets or []):
        if pymesh.shapekey_names[morph_i] is not None:
            num_shapekeys += 1

    # -------------
    # We'll process all the primitives gathering arrays to feed into the
    # various foreach_set function that create the mesh data.

    num_faces = 0  # total number of faces
    vert_locs = np.empty(dtype=np.float32, shape=(0,3))  # coordinate for each vert
    vert_normals = np.empty(dtype=np.float32, shape=(0,3))  # normal for each vert
    edge_vidxs = np.array([], dtype=np.uint32)  # vertex_index for each loose edge
    loop_vidxs = np.array([], dtype=np.uint32)  # vertex_index for each loop
    loop_uvs = [
        np.empty(dtype=np.float32, shape=(0,2))  # UV for each loop for each layer
        for _ in range(num_uvs)
    ]
    loop_cols = [
        np.empty(dtype=np.float32, shape=(0,4))  # color for each loop for each layer
        for _ in range(num_cols)
    ]
    vert_joints = [
        np.empty(dtype=np.uint32, shape=(0,4))  # 4 joints for each vert for each set
        for _ in range(num_joint_sets)
    ]
    vert_weights = [
        np.empty(dtype=np.float32, shape=(0,4))  # 4 weights for each vert for each set
        for _ in range(num_joint_sets)
    ]
    sk_vert_locs = [
        np.empty(dtype=np.float32, shape=(0,3))  # coordinate for each vert for each shapekey
        for _ in range(num_shapekeys)
    ]

    for prim in pymesh.primitives:
        prim.num_faces = 0

        if 'POSITION' not in prim.attributes:
            continue

        vert_index_base = len(vert_locs)

        if prim.indices is not None:
            indices = BinaryData.decode_accessor(gltf, prim.indices)
            indices = indices.reshape(len(indices))
        else:
            num_verts = gltf.data.accessors[prim.attributes['POSITION']].count
            indices = np.arange(0, num_verts, dtype=np.uint32)

        mode = 4 if prim.mode is None else prim.mode
        points, edges, tris = points_edges_tris(mode, indices)
        if points is not None:
            indices = points
        elif edges is not None:
            indices = edges
        else:
            indices = tris

        # We'll add one vert to the arrays for each index used in indices
        unique_indices, inv_indices = np.unique(indices, return_inverse=True)

        vs = BinaryData.decode_accessor(gltf, prim.attributes['POSITION'], cache=True)
        vert_locs = np.concatenate((vert_locs, vs[unique_indices]))

        if has_normals:
            if 'NORMAL' in prim.attributes:
                ns = BinaryData.decode_accessor(gltf, prim.attributes['NORMAL'], cache=True)
                ns = ns[unique_indices]
            else:
                ns = np.zeros((len(unique_indices), 3), dtype=np.float32)
            vert_normals = np.concatenate((vert_normals, ns))

        for i in range(num_joint_sets):
            if ('JOINTS_%d' % i) in prim.attributes and ('WEIGHTS_%d' % i) in prim.attributes:
                js = BinaryData.decode_accessor(gltf, prim.attributes['JOINTS_%d' % i], cache=True)
                ws = BinaryData.decode_accessor(gltf, prim.attributes['WEIGHTS_%d' % i], cache=True)
                js = js[unique_indices]
                ws = ws[unique_indices]
            else:
                js = np.zeros((len(unique_indices), 4), dtype=np.uint32)
                ws = np.zeros((len(unique_indices), 4), dtype=np.float32)
            vert_joints[i] = np.concatenate((vert_joints[i], js))
            vert_weights[i] = np.concatenate((vert_weights[i], ws))

        for morph_i, target in enumerate(prim.targets or []):
            if pymesh.shapekey_names[morph_i] is None:
                continue
            morph_vs = BinaryData.decode_accessor(gltf, target['POSITION'], cache=True)
            morph_vs = morph_vs[unique_indices]
            sk_vert_locs[morph_i] = np.concatenate((sk_vert_locs[morph_i], morph_vs))

        if edges is not None:
            edge_vidxs = np.concatenate((edge_vidxs, inv_indices + vert_index_base))

        if tris is not None:
            prim.num_faces = len(indices) // 3
            num_faces += prim.num_faces

            loop_vidxs = np.concatenate((loop_vidxs, inv_indices + vert_index_base))

            for uv_i in range(num_uvs):
                if ('TEXCOORD_%d' % uv_i) in prim.attributes:
                    uvs = BinaryData.decode_accessor(gltf, prim.attributes['TEXCOORD_%d' % uv_i], cache=True)
                    uvs = uvs[indices]
                else:
                    uvs = np.zeros((len(indices), 3), dtype=np.float32)
                loop_uvs[uv_i] = np.concatenate((loop_uvs[uv_i], uvs))

            for col_i in range(num_cols):
                if ('COLOR_%d' % col_i) in prim.attributes:
                    cols = BinaryData.decode_accessor(gltf, prim.attributes['COLOR_%d' % col_i], cache=True)
                    cols = cols[indices]
                    if cols.shape[1] == 3:
                        cols = colors_rgb_to_rgba(cols)
                else:
                    cols = np.ones((len(indices), 4), dtype=np.float32)
                loop_cols[col_i] = np.concatenate((loop_cols[col_i], cols))

    # Accessors are cached in case they are shared between primitives; clear
    # the cache now that all prims are done.
    gltf.decode_accessor_cache = {}

    # ---------------
    # Convert all the arrays glTF -> Blender

    # Change from relative to absolute positions for morph locs
    for sk_locs in sk_vert_locs:
        sk_locs += vert_locs

    if gltf.yup2zup:
        locs_yup_to_zup(vert_locs)
        locs_yup_to_zup(vert_normals)
        for sk_locs in sk_vert_locs:
            locs_yup_to_zup(sk_locs)

    if num_joint_sets:
        skin_into_bind_pose(
            gltf, skin_idx, vert_joints, vert_weights,
            locs=[vert_locs] + sk_vert_locs,
            vert_normals=vert_normals,
        )

    for uvs in loop_uvs:
        uvs_gltf_to_blender(uvs)

    for cols in loop_cols:
        colors_linear_to_srgb(cols[:, :-1])

    # ---------------
    # Start creating things

    mesh.vertices.add(len(vert_locs))
    mesh.vertices.foreach_set('co', squish(vert_locs))

    mesh.loops.add(len(loop_vidxs))
    mesh.loops.foreach_set('vertex_index', loop_vidxs)

    mesh.edges.add(len(edge_vidxs) // 2)
    mesh.edges.foreach_set('vertices', edge_vidxs)

    mesh.polygons.add(num_faces)

    # All polys are tris
    loop_starts = np.arange(0, 3 * num_faces, step=3)
    loop_totals = np.full(num_faces, 3)
    mesh.polygons.foreach_set('loop_start', loop_starts)
    mesh.polygons.foreach_set('loop_total', loop_totals)

    for uv_i in range(num_uvs):
        name = 'UVMap' if uv_i == 0 else 'UVMap.%03d' % uv_i
        layer = mesh.uv_layers.new(name=name)
        layer.data.foreach_set('uv', squish(loop_uvs[uv_i]))

    for col_i in range(num_cols):
        name = 'Col' if col_i == 0 else 'Col.%03d' % col_i
        layer = mesh.vertex_colors.new(name=name)

        layer.data.foreach_set('color', squish(loop_cols[col_i]))

    # Skinning
    # TODO: this is slow :/
    if num_joint_sets:
        pyskin = gltf.data.skins[skin_idx]
        for _ in pyskin.joints:
            # ob is a temp object, so don't worry about the name.
            ob.vertex_groups.new(name='X')

        for i in range(num_joint_sets):
            js = vert_joints[i].tolist()  # tolist() is faster
            ws = vert_weights[i].tolist()
            for vi in range(len(vert_locs)):
                for k in range(4):
                    joint = js[vi][k]
                    weight = ws[vi][k]
                    if weight == 0.0: continue
                    ob.vertex_groups[joint].add((vi,), weight, 'REPLACE')

    # Shapekeys
    if num_shapekeys:
        ob.shape_key_add(name='Basis')
        mesh.shape_keys.name = mesh.name

        sk_i = 0
        for sk_name in pymesh.shapekey_names:
            if sk_name is None:
                continue

            ob.shape_key_add(name=sk_name)
            key_block = mesh.shape_keys.key_blocks[sk_name]
            key_block.data.foreach_set('co', squish(sk_vert_locs[sk_i]))

            sk_i += 1

    # ----
    # Assign materials to faces

    # Initialize to no-material, ie. an index guaranteed to be OOB for the
    # material slots. A mesh obviously can't have more materials than it has
    # primitives...
    oob_material_idx = len(pymesh.primitives)
    material_indices = np.full(num_faces, oob_material_idx)

    f = 0
    for prim in pymesh.primitives:
        if prim.material is not None:
            # Get the material
            pymaterial = gltf.data.materials[prim.material]
            vertex_color = 'COLOR_0' if 'COLOR_0' in prim.attributes else None
            if vertex_color not in pymaterial.blender_material:
                BlenderMaterial.create(gltf, prim.material, vertex_color)
            material_name = pymaterial.blender_material[vertex_color]

            # Put material in slot (if not there)
            if material_name not in mesh.materials:
                mesh.materials.append(bpy.data.materials[material_name])
            material_index = mesh.materials.find(material_name)

            material_indices[f:f + prim.num_faces].fill(material_index)

        f += prim.num_faces

    mesh.polygons.foreach_set('material_index', material_indices)

    # ----
    # Normals

    # Set poly smoothing
    # TODO: numpyify?
    smooths = []  # use_smooth for each poly
    f = 0
    for prim in pymesh.primitives:
        if gltf.import_settings['import_shading'] == "FLAT" or \
                'NORMAL' not in prim.attributes:
            smooths += [False] * prim.num_faces

        elif gltf.import_settings['import_shading'] == "SMOOTH":
            smooths += [True] * prim.num_faces

        elif gltf.import_settings['import_shading'] == "NORMALS":
            for fi in range(f, f + prim.num_faces):
                # Make the face flat if the face's normal is
                # equal to all of its loops' normals.
                poly_normal = mesh.polygons[fi].normal
                smooths.append(
                    poly_normal.dot(vert_normals[loop_vidxs[3*fi + 0]]) <= 0.9999999 or
                    poly_normal.dot(vert_normals[loop_vidxs[3*fi + 1]]) <= 0.9999999 or
                    poly_normal.dot(vert_normals[loop_vidxs[3*fi + 2]]) <= 0.9999999
                )

        f += prim.num_faces

    mesh.polygons.foreach_set('use_smooth', smooths)

    mesh.validate()
    has_loose_edges = len(edge_vidxs) != 0  # need to calc_loose_edges for them to show up
    mesh.update(calc_edges_loose=has_loose_edges)

    if has_normals:
        mesh.create_normals_split()
        mesh.normals_split_custom_set_from_vertices(vert_normals)
        mesh.use_auto_smooth = True


def points_edges_tris(mode, indices):
    points = None
    edges = None
    tris = None

    if mode == 0:
        # POINTS
        points = indices

    elif mode == 1:
        # LINES
        #   1   3
        #  /   /
        # 0   2
        edges = indices

    elif mode == 2:
        # LINE LOOP
        #   1---2
        #  /     \
        # 0-------3
        # in:  0123
        # out: 01122330
        edges = np.empty(2 * len(indices), dtype=np.uint32)
        edges[[0, -1]] = indices[[0, 0]]  # 0______0
        edges[1:-1] = np.repeat(indices[1:], 2)  # 01122330

    elif mode == 3:
        # LINE STRIP
        #   1---2
        #  /     \
        # 0       3
        # in:  0123
        # out: 011223
        edges = np.empty(2 * len(indices) - 2, dtype=np.uint32)
        edges[[0, -1]] = indices[[0, -1]]  # 0____3
        edges[1:-1] = np.repeat(indices[1:-1], 2)  # 011223

    elif mode == 4:
        # TRIANGLES
        #   2     3
        #  / \   / \
        # 0---1 4---5
        tris = indices

    elif mode == 5:
        # TRIANGLE STRIP
        # 0---2---4
        #  \ / \ /
        #   1---3
        # TODO: numpyify
        def alternate(i, xs):
            even = i % 2 == 0
            return xs if even else (xs[0], xs[2], xs[1])
        tris = np.array([
            alternate(i, (indices[i], indices[i + 1], indices[i + 2]))
            for i in range(0, len(indices) - 2)
        ])
        tris = squish(tris)

    elif mode == 6:
        # TRIANGLE FAN
        #   3---2
        #  / \ / \
        # 4---0---1
        # TODO: numpyify
        tris = np.array([
            (indices[0], indices[i], indices[i + 1])
            for i in range(1, len(indices) - 1)
        ])
        tris = squish(tris)

    else:
        raise Exception('primitive mode unimplemented: %d' % mode)

    return points, edges, tris


def squish(array):
    """Squish nD array into 1D array (required by foreach_set)."""
    return array.reshape(array.size)


def colors_rgb_to_rgba(rgb):
    rgba = np.ones((len(rgb), 4), dtype=np.float32)
    rgba[:, :3] = rgb
    return rgba


def colors_linear_to_srgb(color):
    assert color.shape[1] == 3  # only change RGB, not A

    not_small = color >= 0.0031308
    small_result = np.where(color < 0.0, 0.0, color * 12.92)
    large_result = 1.055 * np.power(color, 1.0 / 2.4, where=not_small) - 0.055
    color[:] = np.where(not_small, large_result, small_result)


def locs_yup_to_zup(vecs):
    # x,y,z -> x,-z,y
    vecs[:, [1,2]] = vecs[:, [2,1]]
    vecs[:, 1] *= -1


def uvs_gltf_to_blender(uvs):
    # u,v -> u,1-v
    uvs[:, 1] *= -1
    uvs[:, 1] += 1


def skin_into_bind_pose(gltf, skin_idx, vert_joints, vert_weights, locs, vert_normals):
    # Skin each position/normal using the bind pose.
    # Skinning equation: vert' = sum_(j,w) w * joint_mat[j] * vert
    # where the sum is over all (joint,weight) pairs.

    # Calculate joint matrices
    joint_mats = []
    pyskin = gltf.data.skins[skin_idx]
    if pyskin.inverse_bind_matrices is not None:
        inv_binds = BinaryData.get_data_from_accessor(gltf, pyskin.inverse_bind_matrices)
        inv_binds = [gltf.matrix_gltf_to_blender(m) for m in inv_binds]
    else:
        inv_binds = [Matrix.Identity(4) for i in range(len(pyskin.joints))]
    bind_mats = [gltf.vnodes[joint].bind_arma_mat for joint in pyskin.joints]
    joint_mats = [bind_mat @ inv_bind for bind_mat, inv_bind in zip(bind_mats, inv_binds)]

    # TODO: check if joint_mats are all (approximately) 1, and skip skinning

    joint_mats = np.array(joint_mats, dtype=np.float32)

    # Compute the skinning matrices for every vert
    num_verts = len(locs[0])
    skinning_mats = np.zeros((num_verts, 4, 4), dtype=np.float32)
    weight_sums = np.zeros(num_verts, dtype=np.float32)
    for js, ws in zip(vert_joints, vert_weights):
        for i in range(4):
            skinning_mats += ws[:, i].reshape(len(ws), 1, 1) * joint_mats[js[:, i]]
            weight_sums += ws[:, i]
    # Normalize weights to one; necessary for old files / quantized weights
    skinning_mats /= weight_sums.reshape(num_verts, 1, 1)

    skinning_mats_3x3 = skinning_mats[:, :3, :3]
    skinning_trans = skinning_mats[:, :3, 3]

    for vs in locs:
        vs[:] = mul_mats_vecs(skinning_mats_3x3, vs)
        vs[:] += skinning_trans

    if len(vert_normals) != 0:
        vert_normals[:] = mul_mats_vecs(skinning_mats_3x3, vert_normals)
        # Don't translate normals!


def mul_mats_vecs(mats, vecs):
    """Given [m1,m2,...] and [v1,v2,...], returns [m1@v1,m2@v2,...]. 3D only."""
    return np.matmul(mats, vecs.reshape(len(vecs), 3, 1)).reshape(len(vecs), 3)
