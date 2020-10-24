# Copyright 2020 The glTF-Blender-IO authors.
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

import uuid

class ExportVNode:
    def __init__(self, bnode):
        self.id = id(bnode.original)
        self.unique_id = uuid.uuid4()
        self.object = bnode.original # original
        self.children = []

    def add_child(self, id):
        self.children.append(id)

class ExportVTree:
    def __init__(self):
        self.nodes = {}
        self.roots = []

    def add_root(self, bnode):
        self.roots.append(id(bnode))

    def get_all_roots(self):
        return self.roots

    def add(self, node):
        self.nodes[node.id] = node

    def eval(self, bnode):
        vnode = ExportVNode(bnode)

        for child in bnode.original.children:
            vnode.add_child(id(child))

        if bnode.instance_type == 'COLLECTION' and bnode.instance_collection:
            for dupli_object in bnode.instance_collection.objects:
                # Check if we skip this now, or later when managing the tree #TODOHIER
                if dupli_object.parent is not None:
                    continue
                if dupli_object.type == "ARMATURE":
                    continue # There is probably a proxy
                vnode.add_child(id(dupli_object.original))

        self.add(vnode)
