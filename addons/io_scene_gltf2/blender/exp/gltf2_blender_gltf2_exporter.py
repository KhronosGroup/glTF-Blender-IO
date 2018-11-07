# Copyright 2018 The glTF-Blender-IO authors.
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
from io_scene_gltf2.io.exp import gltf2_io_binary_data
from io_scene_gltf2.io.exp import gltf2_io_image_data
from io_scene_gltf2.io.exp import gltf2_io_buffer


class GlTF2Exporter:
    """
    The glTF exporter flattens a scene graph to a glTF serializable format.

    Any child properties are replaced with references where necessary
    """

    def __init__(self, copyright=None):
        self.__finalized = False

        asset = gltf2_io.Asset(
            copyright=copyright,
            extensions=None,
            extras=None,
            generator='Khronos Blender glTF 2.0 I/O (Exp)',
            min_version=None,
            version='2.0')

        self.__gltf = gltf2_io.Gltf(
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

        self.__buffer = gltf2_io_buffer.Buffer()
        self.__images = []

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

    @property
    def glTF(self):
        if not self.__finalized:
            raise RuntimeError("glTF requested, but buffers are not finalized yet")
        return self.__gltf

    def finalize_buffer(self, output_path=None, buffer_name=None):
        """
        Finalize the glTF and write buffers.

        :param buffer_path:
        :return:
        """
        if self.__finalized:
            raise RuntimeError("Tried to finalize buffers for finalized glTF file")

        if output_path and buffer_name:
            with open(output_path + buffer_name, 'wb') as f:
                f.write(self.__buffer.to_bytes())
            uri = buffer_name
        else:
            uri = self.__buffer.to_embed_string()

        buffer = gltf2_io.Buffer(
            byte_length=self.__buffer.byte_length,
            extensions=None,
            extras=None,
            name=None,
            uri=uri
        )
        self.__gltf.buffers.append(buffer)

        self.__finalized = True

    def finalize_images(self, output_path):
        """
        Write all images.

        Due to a current limitation the output_path must be the same as that of the glTF file
        :param output_path:
        :return:
        """
        for image in self.__images:
            uri = output_path + image.name + ".png"
            with open(uri, 'wb') as f:
                f.write(image.to_png_data())

    def add_scene(self, scene: gltf2_io.Scene, active: bool = True):
        """
        Add a scene to the glTF.

        The scene should be built up with the generated glTF classes
        :param scene: gltf2_io.Scene type. Root node of the scene graph
        :param active: If true, sets the glTD.scene index to the added scene
        :return: nothing
        """
        if self.__finalized:
            raise RuntimeError("Tried to add scene to finalized glTF file")

        # for node in scene.nodes:
        #     self.__traverse(node)
        scene_num = self.__traverse(scene)
        if active:
            self.__gltf.scene = scene_num

    def add_animation(self, animation: gltf2_io.Animation):
        """
        Add an animation to the glTF.

        :param animation: glTF animation, with python style references (names)
        :return: nothing
        """
        if self.__finalized:
            raise RuntimeError("Tried to add animation to finalized glTF file")

        self.__traverse(animation)

    def __to_reference(self, property):
        """
        Append a child of root property to its respective list and return a reference into said list.

        If the property is not child of root, the property itself is returned.
        :param property: A property type object that should be converted to a reference
        :return: a reference or the object itself if it is not child or root
        """
        gltf_list = self.__childOfRootPropertyTypeLookup.get(type(property), None)
        if gltf_list is None:
            # The object is not of a child of root --> don't convert to reference
            return property

        return self.__append_unique_and_get_index(gltf_list, property)

    @staticmethod
    def __append_unique_and_get_index(target: list, obj):
        if obj in target:
            return target.index(obj)
        else:
            index = len(target)
            target.append(obj)
            return index

    def __add_image(self, image: gltf2_io_image_data.ImageData):
        self.__images.append(image)
        # TODO: we need to know the image url at this point already --> maybe add all options to the constructor of the
        # exporter
        # TODO: allow embedding of images (base64)
        return image.name + ".png"

    def __traverse(self, node):
        """
        Recursively traverse a scene graph consisting of gltf compatible elements.

        The tree is traversed downwards until a primitive is reached. Then any ChildOfRoot property
        is stored in the according list in the glTF and replaced with a index reference in the upper level.
        """
        def traverse_all_members(node):
            for member_name in [a for a in dir(node) if not a.startswith('__') and not callable(getattr(node, a))]:
                new_value = self.__traverse(getattr(node, member_name))
                setattr(node, member_name, new_value)  # usually this is the same as before
            return node

        # traverse nodes of a child of root property type and add them to the glTF root
        if type(node) in self.__childOfRootPropertyTypeLookup:
            node = traverse_all_members(node)
            idx = self.__to_reference(node)
            # child of root properties are only present at root level --> replace with index in upper level
            return idx

        # traverse lists, such as children and replace them with indices
        if isinstance(node, list):
            for i in range(len(node)):
                node[i] = self.__traverse(node[i])
            return node

        if isinstance(node, dict):
            for key in node.keys():
                node[key] = self.__traverse(node[key])
            return node

        # traverse into any other property
        if type(node) in self.__propertyTypeLookup:
            return traverse_all_members(node)

        # binary data needs to be moved to a buffer and referenced with a buffer view
        if isinstance(node, gltf2_io_binary_data.BinaryData):
            buffer_view = self.__buffer.add_and_get_view(node)
            return self.__to_reference(buffer_view)

        # image data needs to be saved to file
        if isinstance(node, gltf2_io_image_data.ImageData):
            return self.__add_image(node)

        # do nothing for any type that does not match a glTF schema (primitives)
        return node
