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

from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.io.com import gltf2_io_debug

class GlTF2Exporter():
    """
    The glTF exporter flattens a scene graph to a glTF serializable format.
    Any child properties are replaced with references where necessary
    """
    def __init__(self, copyright=None):
        asset = gltf2_io.Asset(
            copyright=copyright,
            extensions=None,
            extras=None,
            generator='Khronos Blender glTF 2.0 I/O (Exp)',
            min_version=None,
            version='2.0')

        self.gltf = gltf2_io.Gltf(
            accessors=[],
            animations=[],
            asset=asset,
            buffers=[],
            buffer_views=[],
            cameras=[],
            extensions={},
            extensions_required=[],
            extensions_used=[],
            extras=None,
            images=[],
            materials=[],
            meshes=[],
            nodes=[],
            samplers=[],
            scene=-1,
            scenes=[],
            skins=[],
            textures=[]
        )
        # mapping of all glTFChildOfRootProperty types to their corresponding root level arrays
        self.__childOfRootPropertyTypeLookup = {
            gltf2_io.Accessor: self.gltf.accessors,
            gltf2_io.Animation: self.gltf.animations,
            gltf2_io.Buffer: self.gltf.buffers,
            gltf2_io.BufferView: self.gltf.buffer_views,
            gltf2_io.Camera: self.gltf.cameras,
            gltf2_io.Image: self.gltf.images,
            gltf2_io.Material: self.gltf.materials,
            gltf2_io.Mesh: self.gltf.meshes,
            gltf2_io.Node: self.gltf.nodes,
            gltf2_io.Sampler: self.gltf.samplers,
            gltf2_io.Scene: self.gltf.scenes,
            gltf2_io.Skin: self.gltf.skins,
            gltf2_io.Texture: self.gltf.textures
        }

        self.__propertyTypeLookup = [
            gltf2_io.AccessorSparseIndices,
            gltf2_io.AccessorSparse,
            gltf2_io.AccessorSparseValues,
            gltf2_io.AnimationChannel,
            gltf2_io.AnimationChannelTarget,
            gltf2_io.AnimationSampler,
            gltf2_io.Asset,
            gltf2_io.CameraOrthographic,
            gltf2_io.CameraPerspective,
            gltf2_io.MeshPrimitive,
            gltf2_io.TextureInfo,
            gltf2_io.MaterialPBRMetallicRoughness,
            gltf2_io.MaterialNormalTextureInfoClass,
            gltf2_io.MaterialOcclusionTextureInfoClass
        ]

    def add_scene(self, scene):
        """
        Add a scene to the glTF. The scene should be built up with the generated glTF classes
        :param scene: gltf2_io.Scene type. Root node of the scene graph
        :return: nothing
        """
        if not isinstance(scene, gltf2_io.Scene):
            gltf2_io_debug.print_console("ERROR", "Tried to add non scene type to glTF")
            return

        for node in scene.nodes:
            self.__traverse(node)
        self.__traverse(scene)

    @staticmethod
    def __append_unique(gltf_list, obj):
        if obj in gltf_list:
            return gltf_list.index(obj)
        else:
            index = len(gltf_list)
            gltf_list.append(obj)
            return index

    def __traverse(self, node):
        """
        Recursively traverse a scene graph consisting of gltf compatible elements

        The tree is traversed downwards until a primitive is reached. Then any ChildOfRoot property
        is stored in the according list in the glTF and replaced with a index reference in the upper level.
        """
        def traverse_all_members(node):
            for member_name in [a for a in dir(node) if not a.startswith('__') and not callable(getattr(node, a))]:
                new_value = self.__traverse(getattr(node, member_name))
                setattr(node, member_name, new_value) # usually this is the same as before
            return node

        # traverse nodes of a child of root property type and add them to the glTF root
        if type(node) in self.__childOfRootPropertyTypeLookup:
            node = traverse_all_members(node)
            idx = self.__append_unique(self.__childOfRootPropertyTypeLookup[type(node)], node)
            # child of root properties are only present at root level --> replace with index in upper level
            return idx

        # traverse lists, such as children and replace them with indices
        if isinstance(node, list):
            for i in range(len(node)):
                node[i] = self.__traverse(node[i])
            return node

        # traverse into any other property
        if type(node) in self.__propertyTypeLookup:
            node = traverse_all_members(node)

        # do nothing for any type that does not match a glTF schema (primitives)
        return node
