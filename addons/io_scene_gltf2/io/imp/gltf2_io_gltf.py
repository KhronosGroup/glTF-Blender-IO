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
from ..com.gltf2_io_gltf import *
import logging

print("Loading")

class glTFImporter():

    @staticmethod
    def load_glb(pygltf):
        header = struct.unpack_from('<I4s', pygltf.content)
        pygltf.version = header[1]

        offset = 12 # header size = 12

        # TODO check json type for chunk 0, and BIN type for next ones

        # json
        type, str_json, offset = glTFImporter.load_chunk(pygltf, offset)
        pygltf.json = json.loads(str_json.decode('utf-8'))

        # binary data
        chunk_cpt = 0
        while offset < len(pygltf.content):
            type, data, offset = glTFImporter.load_chunk(pygltf, offset)

            pygltf.buffers[chunk_cpt] = Buffer(chunk_cpt, pygltf.json['buffers'][chunk_cpt], pygltf)
            pygltf.buffers[chunk_cpt].data = data #TODO .length
            chunk_cpt += 1

        pygltf.content = None

    @staticmethod
    def load_chunk(pygltf, offset):
        chunk_header = struct.unpack_from('<I4s', pygltf.content, offset)
        data_length  = chunk_header[0]
        data_type    = chunk_header[1]
        data         = pygltf.content[offset + 8 : offset + 8 + data_length]

        return data_type, data, offset + 8 + data_length

    @staticmethod
    def load(pygltf):
        with open(pygltf.filename, 'rb') as f:
            pygltf.content = f.read()


        pygltf.is_glb_format = pygltf.content[:4] == b'glTF'

        if not pygltf.is_glb_format:
            pygltf.content = None
            with open(pygltf.filename, 'r') as f:
                content = f.read()
                pygltf.json = json.loads(content)

        else:
            # Parsing glb file
            pygltf.load_glb()

    @staticmethod
    def get_root_scene(pygltf):
        if 'scene' in pygltf.json.keys():
            return pygltf.json['scene'], pygltf.json['scenes'][pygltf.json['scene']]
        return 0, pygltf.json['scenes'][0]

    @staticmethod
    def read(pygltf):
        if 'asset' in pygltf.json.keys():
            pygltf.asset = PyAsset(pygltf.json['asset'], pygltf)
            pygltf.asset.read()
        else:
            return False, "asset is mandatory"

        check_version, txt = pygltf.asset.check_version()
        if not check_version:
            return False, txt

        idx, scene = glTFImporter.get_root_scene(pygltf)
        if not scene:
            return False, "Error reading root scene"

        if 'extensionsRequired' in pygltf.json.keys():
            for ext in pygltf.json['extensionsRequired']:
                if ext not in pygltf.extensions_managed:
                    return False, "Extension " + ext + " is not available on this addon version"

        if 'extensionsUsed' in pygltf.json.keys():
            for ext in pygltf.json['extensionsUsed']:
                if ext not in pygltf.extensions_managed:
                    pygltf.log.error("Extension " + ext + " is not available on this addon version")
                    # Non blocking error

        pygltf.scene = PyScene(idx, scene, pygltf)
        pygltf.scene.read()

        # manage all scenes (except root scene that is already managed)
        scene_idx = 0
        for scene_it in pygltf.json['scenes']:
            if scene_idx == idx:
                continue
            scene = Scene(scene_idx, pygltf.json['scenes'][scene_idx] , pygltf)
            scene.read()
            scene_idx += 1
            pygltf.other_scenes.append(scene)


        # manage animations
        if 'animations' in pygltf.json.keys():
            anim_idx = 0
            for anim in pygltf.json['animations']:
                animation = PyAnimation(anim_idx, pygltf.json['animations'][anim_idx], pygltf)
                animation.read()
                pygltf.animations[animation.index] = animation
                anim_idx += 1

        # Set bone type on all joints
        for node in pygltf.scene.nodes.values():
            is_joint, skin = glTFImporter.is_node_joint(pygltf, node.index)
            if is_joint:
                node.is_joint = True
                node.skin_id     = skin

        for scene in pygltf.other_scenes:
            for node in scene.nodes.values():
                is_joint, skin = glTFImporter.is_node_joint(pygltf, node.index)
                if is_joint:
                    node.is_joint = True
                    node.skin_id     = skin

        return True, None # Success

    @staticmethod
    def is_node_joint(pygltf, node_id):
        is_joint = False
        for skin in pygltf.skins.values():
            if node_id in skin.bones:
                return True, skin.index

        return is_joint, None

    @staticmethod
    def importer(filename, loglevel=logging.ERROR):
        pygltf = PyglTF(filename, loglevel=loglevel)
        glTFImporter.load(pygltf)
        success, txt = glTFImporter.read(pygltf)

        return success, pygltf, txt
