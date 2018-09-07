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
    def __init__(self):
        self.__gltf = gltf2_io.Gltf(
            accessors=[],
            animations=[],
            asset=None,
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
            gltf2_io.Accessor: self.__gltf.accessors,
            gltf2_io.Animation: self.__gltf.animations,
            gltf2_io.Buffer: self.__gltf.buffers,
            gltf2_io.BufferView: self.__gltf.buffer_views,
            gltf2_io.Camera: self.__gltf.cameras,
            gltf2_io.Image: self.__gltf.images,
            gltf2_io.Material: self.__gltf.materials,
            gltf2_io.Mesh: self.__gltf.meshes,
            gltf2_io.Node: self.__gltf.nodes,
            gltf2_io.Sampler: self.__gltf.samplers,
            gltf2_io.Scene: self.__gltf.scenes,
            gltf2_io.Skin: self.__gltf.skins,
            gltf2_io.Texture: self.__gltf.textures
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

        # traverse nodes of a child of root property type and add them to the glTF root
        if type(node) in self.__childOfRootPropertyTypeLookup:
            traverse_all_members(node)
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
            traverse_all_members(node)

        # do nothing for any type that does not match a glTF schema (primitives)
        return node
