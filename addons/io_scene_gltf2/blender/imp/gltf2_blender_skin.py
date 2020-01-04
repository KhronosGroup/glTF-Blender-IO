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

class BlenderSkin():
    """Blender Skinning / Armature."""
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("%s should not be instantiated" % cls)

    @staticmethod
    def create_vertex_groups(gltf):
        """Create vertex groups for all skinned meshes."""
        for vnode in gltf.vnodes.values():
            if vnode.mesh_node_idx is None:
                continue
            pynode = gltf.data.nodes[vnode.mesh_node_idx]
            if pynode.skin is None:
                continue
            pyskin = gltf.data.skins[pynode.skin]

            obj = vnode.blender_object
            for node_idx in pyskin.joints:
                bone = gltf.vnodes[node_idx]
                obj.vertex_groups.new(name=bone.blender_bone_name)

    @staticmethod
    def create_armature_modifiers(gltf):
        """Create Armature modifiers for all skinned meshes."""
        for vnode in gltf.vnodes.values():
            if vnode.mesh_node_idx is None:
                continue
            pynode = gltf.data.nodes[vnode.mesh_node_idx]
            if pynode.skin is None:
                continue
            pyskin = gltf.data.skins[pynode.skin]

            first_bone = gltf.vnodes[pyskin.joints[0]]
            arma = gltf.vnodes[first_bone.bone_arma]

            obj = vnode.blender_object
            mod = obj.modifiers.new(name="Armature", type="ARMATURE")
            mod.object = arma.blender_object
