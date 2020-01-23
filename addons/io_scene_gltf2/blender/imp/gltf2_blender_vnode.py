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
from mathutils import Vector, Quaternion, Matrix

def compute_vnodes(gltf):
    """Computes the tree of virtual nodes.
    Copies the glTF nodes into a tree of VNodes, then performs a series of
    passes to transform it into a form that we can import into Blender.
    """
    init_vnodes(gltf)
    mark_bones_and_armas(gltf)
    move_skinned_meshes(gltf)
    fixup_multitype_nodes(gltf)
    correct_cameras_and_lights(gltf)
    calc_bone_matrices(gltf)


class VNode:
    """A "virtual" node.
    These are what eventually get turned into nodes
    in the Blender scene.
    """
    # Types
    Object = 0
    Bone = 1
    DummyRoot = 2

    def __init__(self):
        self.name = ''
        self.children = []
        self.parent = None
        self.type = VNode.Object
        self.is_arma = False
        self.trs = (
            Vector((0, 0, 0)),
            Quaternion((1, 0, 0, 0)),
            Vector((1, 1, 1)),
        )
        # Indices of the glTF node where the mesh, etc. came from.
        # (They can get moved around.)
        self.mesh_node_idx = None
        self.camera_node_idx = None
        self.light_node_idx = None


def init_vnodes(gltf):
    # Map of all VNodes. The keys are arbitrary IDs.
    # Nodes coming from glTF use the index into gltf.data.nodes for an ID.
    gltf.vnodes = {}

    for i, pynode in enumerate(gltf.data.nodes or []):
        vnode = VNode()
        gltf.vnodes[i] = vnode
        vnode.name = pynode.name or 'Node_%d' % i
        vnode.children = list(pynode.children or [])
        vnode.trs = get_node_trs(gltf, pynode)
        if pynode.mesh is not None:
            vnode.mesh_node_idx = i
        if pynode.camera is not None:
            vnode.camera_node_idx = i
        if 'KHR_lights_punctual' in (pynode.extensions or {}):
            vnode.light_node_idx = i

    for id in gltf.vnodes:
        for child in gltf.vnodes[id].children:
            assert gltf.vnodes[child].parent is None
            gltf.vnodes[child].parent = id

    # Inserting a root node will simplify things.
    roots = [id for id in gltf.vnodes if gltf.vnodes[id].parent is None]
    gltf.vnodes['root'] = VNode()
    gltf.vnodes['root'].type = VNode.DummyRoot
    gltf.vnodes['root'].name = 'Root'
    gltf.vnodes['root'].children = roots
    for root in roots:
        gltf.vnodes[root].parent = 'root'

def get_node_trs(gltf, pynode):
    if pynode.matrix is not None:
        m = gltf.matrix_gltf_to_blender(pynode.matrix)
        return m.decompose()

    t = gltf.loc_gltf_to_blender(pynode.translation or [0, 0, 0])
    r = gltf.quaternion_gltf_to_blender(pynode.rotation or [0, 0, 0, 1])
    s = gltf.scale_gltf_to_blender(pynode.scale or [1, 1, 1])
    return t, r, s


def mark_bones_and_armas(gltf):
    """
    Mark nodes as armatures so that every node that is used as joint is a
    descendant of an armature. Mark everything between an armature and a
    joint as a bone.
    """
    for skin in gltf.data.skins or []:
        descendants = list(skin.joints)
        if skin.skeleton is not None:
            descendants.append(skin.skeleton)
        arma_id = deepest_common_ancestor(gltf, descendants)

        if arma_id in skin.joints:
            arma_id = gltf.vnodes[arma_id].parent

        if gltf.vnodes[arma_id].type != VNode.Bone:
            gltf.vnodes[arma_id].type = VNode.Object
            gltf.vnodes[arma_id].is_arma = True
            gltf.vnodes[arma_id].arma_name = skin.name or 'Armature'

        for joint in skin.joints:
            while joint != arma_id:
                gltf.vnodes[joint].type = VNode.Bone
                gltf.vnodes[joint].is_arma = False
                joint = gltf.vnodes[joint].parent

    # Mark the armature each bone is a descendant of.

    def visit(vnode_id, cur_arma):  # Depth-first walk
        vnode = gltf.vnodes[vnode_id]

        if vnode.is_arma:
            cur_arma = vnode_id
        elif vnode.type == VNode.Bone:
            vnode.bone_arma = cur_arma
        else:
            cur_arma = None

        for child in vnode.children:
            visit(child, cur_arma)

    visit('root', cur_arma=None)

def deepest_common_ancestor(gltf, vnode_ids):
    """Find the deepest (improper) ancestor of a set of vnodes."""
    path_to_ancestor = []  # path to deepest ancestor so far
    for vnode_id in vnode_ids:
        path = path_from_root(gltf, vnode_id)
        if not path_to_ancestor:
            path_to_ancestor = path
        else:
            path_to_ancestor = longest_common_prefix(path, path_to_ancestor)
    return path_to_ancestor[-1]

def path_from_root(gltf, vnode_id):
    """Returns the ids of all vnodes from the root to vnode_id."""
    path = []
    while vnode_id is not None:
        path.append(vnode_id)
        vnode_id = gltf.vnodes[vnode_id].parent
    path.reverse()
    return path

def longest_common_prefix(list1, list2):
    i = 0
    while i != min(len(list1), len(list2)):
        if list1[i] != list2[i]:
            break
        i += 1
    return list1[:i]


def move_skinned_meshes(gltf):
    """
    In glTF, where in the node hierarchy a skinned mesh is instantiated has
    no effect on its world space position: only the world transforms of the
    joints in its skin affect it.

    To do this in Blender:
     * Move a skinned mesh to become a child of the armature that affects it
     * When we do mesh creation, we will also need to put all the verts in
       their rest pose (ie. the pose the edit bones are in)
    """
    # TODO: this leaves behind empty "husk" nodes where the skinned meshes
    #       used to be, which is ugly.
    ids = list(gltf.vnodes.keys())
    for id in ids:
        vnode = gltf.vnodes[id]

        if vnode.mesh_node_idx is None:
            continue

        mesh = gltf.data.nodes[vnode.mesh_node_idx].mesh
        skin = gltf.data.nodes[vnode.mesh_node_idx].skin
        if skin is None:
            continue

        pyskin = gltf.data.skins[skin]
        arma = gltf.vnodes[pyskin.joints[0]].bone_arma

        new_id = str(id) + '.skinned'
        gltf.vnodes[new_id] = VNode()
        gltf.vnodes[new_id].name = gltf.data.meshes[mesh].name or 'Mesh_%d' % mesh
        gltf.vnodes[new_id].parent = arma
        gltf.vnodes[arma].children.append(new_id)

        gltf.vnodes[new_id].mesh_node_idx = vnode.mesh_node_idx
        vnode.mesh_node_idx = None


def fixup_multitype_nodes(gltf):
    """
    Blender only lets each object have one of: an armature, a mesh, a
    camera, a light. Also bones cannot have any of these either. Find any
    nodes like this and move the mesh/camera/light onto new children.
    """
    ids = list(gltf.vnodes.keys())
    for id in ids:
        vnode = gltf.vnodes[id]

        needs_move = False

        if vnode.is_arma or vnode.type == VNode.Bone:
            needs_move = True

        if vnode.mesh_node_idx is not None:
            if needs_move:
                new_id = str(id) + '.mesh'
                gltf.vnodes[new_id] = VNode()
                gltf.vnodes[new_id].name = vnode.name + ' Mesh'
                gltf.vnodes[new_id].mesh_node_idx = vnode.mesh_node_idx
                gltf.vnodes[new_id].parent = id
                vnode.children.append(new_id)
                vnode.mesh_node_idx = None
            needs_move = True

        if vnode.camera_node_idx is not None:
            if needs_move:
                new_id = str(id) + '.camera'
                gltf.vnodes[new_id] = VNode()
                gltf.vnodes[new_id].name = vnode.name + ' Camera'
                gltf.vnodes[new_id].camera_node_idx = vnode.camera_node_idx
                gltf.vnodes[new_id].parent = id
                vnode.children.append(new_id)
                vnode.camera_node_idx = None
            needs_move = True

        if vnode.light_node_idx is not None:
            if needs_move:
                new_id = str(id) + '.light'
                gltf.vnodes[new_id] = VNode()
                gltf.vnodes[new_id].name = vnode.name + ' Light'
                gltf.vnodes[new_id].light_node_idx = vnode.light_node_idx
                gltf.vnodes[new_id].parent = id
                vnode.children.append(new_id)
                vnode.light_node_idx = None
            needs_move = True


def correct_cameras_and_lights(gltf):
    """
    Depending on the coordinate change, lights and cameras might need to be
    rotated to match Blender conventions for which axes they point along.
    """
    if gltf.camera_correction is None:
        return

    trs = (Vector((0, 0, 0)), gltf.camera_correction, Vector((1, 1, 1)))

    ids = list(gltf.vnodes.keys())
    for id in ids:
        vnode = gltf.vnodes[id]

        # Move the camera/light onto a new child and set its rotation
        # TODO: "hard apply" the rotation without creating a new node
        #       (like we'll need to do for bones)

        if vnode.camera_node_idx is not None:
            new_id = str(id) + '.camera-correction'
            gltf.vnodes[new_id] = VNode()
            gltf.vnodes[new_id].name = vnode.name + ' Correction'
            gltf.vnodes[new_id].trs = trs
            gltf.vnodes[new_id].camera_node_idx = vnode.camera_node_idx
            gltf.vnodes[new_id].parent = id
            vnode.children.append(new_id)
            vnode.camera_node_idx = None

        if vnode.light_node_idx is not None:
            new_id = str(id) + '.light-correction'
            gltf.vnodes[new_id] = VNode()
            gltf.vnodes[new_id].name = vnode.name + ' Correction'
            gltf.vnodes[new_id].trs = trs
            gltf.vnodes[new_id].light_node_idx = vnode.light_node_idx
            gltf.vnodes[new_id].parent = id
            vnode.children.append(new_id)
            vnode.light_node_idx = None


def calc_bone_matrices(gltf):
    """
    Calculate bone_arma_mat, the transformation from bone space to armature
    space for the edit bone, for each bone.
    """
    def visit(vnode_id):  # Depth-first walk
        vnode = gltf.vnodes[vnode_id]
        if vnode.type == VNode.Bone:
            if gltf.vnodes[vnode.parent].type == VNode.Bone:
                parent_arma_mat = gltf.vnodes[vnode.parent].bone_arma_mat
            else:
                parent_arma_mat = Matrix.Identity(4)

            t, r, _ = vnode.trs
            if bpy.app.version < (2, 80, 0):
                local_to_parent = Matrix.Translation(t) * Quaternion(r).to_matrix().to_4x4()
                vnode.bone_arma_mat = parent_arma_mat * local_to_parent
            else:
                local_to_parent = Matrix.Translation(t) @ Quaternion(r).to_matrix().to_4x4()
                vnode.bone_arma_mat = parent_arma_mat @ local_to_parent

        for child in vnode.children:
            visit(child)

    visit('root')


# TODO: add pass to rotate/resize bones so they look pretty
