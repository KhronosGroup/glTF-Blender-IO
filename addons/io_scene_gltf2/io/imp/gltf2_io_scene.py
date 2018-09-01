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
 """

from ..com.gltf2_io_scene import *

class SceneImporter():

    @staticmethod
    def read(pyscene):
        if 'name' in pyscene.json.keys():
            pyscene.name = pyscene.json['name']
            pyscene.gltf.log.info("Scene " + pyscene.json['name'])
        else:
            pyscene.name = None
            pyscene.gltf.log.info("Scene...")


        for node_idx in pyscene.json['nodes']:
            node = PyNode(node_idx, pyscene.gltf.json['nodes'][node_idx], pyscene.gltf, pyscene)
            node.read()
            pyscene.nodes[node_idx] = node

        for skin in pyscene.gltf.skins.values():
            if skin.root is not None and skin.root != skin.bones[0]:
                # skin.bones.insert(0, skin.root)
                pyscene.nodes[skin.root].is_joint = True
                pyscene.nodes[skin.root].skin_id = skin.index

        # manage root nodes
        parent_detector = {}
        for node in pyscene.nodes:
            for child in pyscene.nodes[node].children:
                parent_detector[child.index] = node

        for node in pyscene.nodes:
            if node not in parent_detector.keys():
                pyscene.root_nodes_idx.append(node)

    @staticmethod
    def importer(idx, scene_, pygltf):
        scene = PyScene(idx, scene_, pygltf)
        SceneImporter.read(scene)
        return scene
