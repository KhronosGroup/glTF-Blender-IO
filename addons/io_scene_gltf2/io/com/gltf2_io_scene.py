"""
 * ***** BEGIN GPL LICENSE BLOCK *****
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License
 * as published by the Free Software Foundation; either version 2
 * of the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software Foundation,
 * Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
 *
 * Contributor(s): Julien Duroure.
 *
 * ***** END GPL LICENSE BLOCK *****
 * This development is done in strong collaboration with Airbus Defence & Space
 """

from ...blender.imp.node import * #SPLIT_TODO

class PyScene():
    def __init__(self, index, json, gltf):
        self.json = json   # Scene json
        self.gltf = gltf # Reference to global glTF instance
        self.nodes = {}
        self.root_nodes_idx = []

    def read(self):
        if 'name' in self.json.keys():
            self.name = self.json['name']
            self.gltf.log.info("Scene " + self.json['name'])
        else:
            self.name = None
            self.gltf.log.info("Scene...")


        for node_idx in self.json['nodes']:
            node = Node(node_idx, self.gltf.json['nodes'][node_idx], self.gltf, self)
            node.read()
            node.debug_missing()
            self.nodes[node_idx] = node

        for skin in self.gltf.skins.values():
            if skin.root is not None and skin.root != skin.bones[0]:
                # skin.bones.insert(0, skin.root)
                self.nodes[skin.root].is_joint = True
                self.nodes[skin.root].skin_id = skin.index

        # manage root nodes
        parent_detector = {}
        for node in self.nodes:
            for child in self.nodes[node].children:
                parent_detector[child.index] = node

        for node in self.nodes:
            if node not in parent_detector.keys():
                self.root_nodes_idx.append(node)
