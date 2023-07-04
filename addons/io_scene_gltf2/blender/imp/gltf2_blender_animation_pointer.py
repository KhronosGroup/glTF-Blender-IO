# Copyright 2018-2023 The glTF-Blender-IO authors.
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
from ...io.imp.gltf2_io_user_extensions import import_user_extensions
from ...io.imp.gltf2_io_binary import BinaryData
from ..exp.gltf2_blender_get import get_socket, get_socket_old #TODO move to COM
from .gltf2_blender_animation_utils import make_fcurve
from .gltf2_blender_light import BlenderLight


class BlenderPointerAnim():
    """Blender Pointer Animation."""
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("%s should not be instantiated" % cls)

    @staticmethod
    def anim(gltf, anim_idx, asset, asset_idx, asset_type, name=None):
        animation = gltf.data.animations[anim_idx]

        if asset_type in ["LIGHT"]:
            if anim_idx not in asset['animations'].keys():
                return
            tab = asset['animations']
        else:
            if anim_idx not in asset.animations.keys():
                return
            tab = asset.animations

        for channel_idx in tab[anim_idx]:
            channel = animation.channels[channel_idx]
            BlenderPointerAnim.do_channel(gltf, anim_idx, channel, asset, asset_idx, asset_type, name=name)

    @staticmethod
    def do_channel(gltf, anim_idx, channel, asset, asset_idx, asset_type, name=None):
        animation = gltf.data.animations[anim_idx]
        pointer_tab = channel.target.extensions["KHR_animation_pointer"]["pointer"].split("/")

        import_user_extensions('gather_import_animation_pointer_channel_before_hook', gltf, animation, channel)

        # For some asset_type, we need to check what is the real id_root
        if asset_type == "MATERIAL":
            if len(pointer_tab) == 4 and pointer_tab[1] == "materials" and \
                    pointer_tab[3] == "alphaCutoff":
                id_root = "MATERIAL"
            else:
                id_root = "NODETREE"
        elif asset_type == "MATERIAL_PBR":
            id_root = "NODETREE"
        else:
            id_root = asset_type

        action = BlenderPointerAnim.get_or_create_action(gltf, asset, asset_idx, animation.track_name, id_root, name=name)

        keys = BinaryData.get_data_from_accessor(gltf, animation.samplers[channel.sampler].input)
        values = BinaryData.get_data_from_accessor(gltf, animation.samplers[channel.sampler].output)

        if animation.samplers[channel.sampler].interpolation == "CUBICSPLINE":
            # TODO manage tangent?
            values = values[1::3]

        # Convert the curve from glTF to Blender.
        blender_path = None
        num_components = None
        group_name = ''
        ### Camera
        if len(pointer_tab) == 5 and pointer_tab[1] == "cameras" and \
            pointer_tab[3] in ["perspective"] and \
            pointer_tab[4] in ["yfov", "znear", "zfar"]:
            blender_path = {
                "yfov": "angle_y", #TODOPointer : need to convert, angle can't be animated
                "znear": "clip_start",
                "zfar": "clip_end"
            }.get(pointer_tab[4])
            num_components = 1

        if len(pointer_tab) == 5 and pointer_tab[1] == "cameras" and \
            pointer_tab[3] in ["orthographic"] and \
            pointer_tab[4] in ["ymag", "xmag"]:
            # TODOPointer need to calculate, and before, check if both are animated of not
            num_components = 1

        ### Light
        if len(pointer_tab) == 6 and pointer_tab[1] == "extensions" and \
            pointer_tab[2] == "KHR_lights_punctual" and \
            pointer_tab[3] == "lights" and \
            pointer_tab[5] in ["intensity", "color", "range"]:

            blender_path = {
                "color": "color",
                "intensity": "energy"
            }.get(pointer_tab[5])
            group_name = 'Color'
            num_components = 3 if blender_path == "color" else 1

            # TODO perf, using numpy
            if blender_path == "energy":
                old_values = values.copy()
                for idx, i in enumerate(old_values):
                    if asset['type'] in ["SPOT", "POINT"]:
                        values[idx] = [BlenderLight.calc_energy_pointlike(gltf, i[0])]
                    else:
                        values[idx] = [BlenderLight.calc_energy_directional(gltf, i[0])]

            #TODO range, not implemented (even not in static import)

        if len(pointer_tab) == 7 and pointer_tab[1] == "extensions" and \
            pointer_tab[2] == "KHR_lights_punctual" and \
            pointer_tab[3] == "lights" and \
            pointer_tab[5] == "spot" and \
            pointer_tab[6] in ["outerConeAngle", "innerConeAngle"]:

            if pointer_tab[6] == "outerConeAngle":
                blender_path = "spot_size"
                num_components = 1

            # TODOPointer innerConeAngle, need to calculate, and before, check if innerConeAngle are animated of not

        #### Materials
        if len(pointer_tab) == 4 and pointer_tab[1] == "materials" and \
            pointer_tab[3] in ["emissiveFactor", "alphaCutoff"]:

            if pointer_tab[3] == "emissiveFactor":
                emissive_socket = get_socket(asset.blender_nodetree, True, "Emissive")
                if emissive_socket.is_linked:
                    # We need to find the correct node value to animate (An Emissive Factor node)
                    mix_node = emissive_socket.links[0].from_node
                    if mix_node.type == "MIX":
                        blender_path = mix_node.inputs[7].path_from_id() + ".default_value"
                        num_components = 3
                    else:
                        print("Error, something is wrong, we didn't detect adding a Mix Node because of Pointers")
                else:
                    blender_path = emissive_socket.path_from_id() + ".default_value"
                    num_components = 3
            elif pointer_tab[3] == "alphaCutoff":
                blender_path = "alpha_threshold"
                num_components = 1

        if len(pointer_tab) == 5 and pointer_tab[1] == "materials" and \
            pointer_tab[3] == "normalTexture" and \
            pointer_tab[4] == "scale":

            normal_socket = get_socket(asset.blender_nodetree, True, "Normal")
            if normal_socket.is_linked:
                normal_node = normal_socket.links[0].from_node
                if normal_node.type == "NORMAL_MAP":
                    blender_path = normal_node.inputs[0].path_from_id() + ".default_value"
                    num_components = 1

        if len(pointer_tab) == 5 and pointer_tab[1] == "materials" and \
            pointer_tab[3] == "occlusionTexture" and \
            pointer_tab[4] == "strength":

            occlusion_socket = get_socket(asset.blender_nodetree, True, "Occlusion")
            if occlusion_socket is None:
                occlusion_socket = get_socket_old(asset.blender_mat, "Occlusion")
            if occlusion_socket.is_linked:
                mix_node = occlusion_socket.links[0].from_node
                if mix_node.type == "MATH":
                    blender_path = mix_node.inputs[1].path_from_id() + ".default_value"
                    num_components = 1
                else:
                    print("Error, something is wrong, we didn't detect adding a Mix Node because of Pointers")
            else:
                blender_path = occlusion_socket.path_from_id() + ".default_value"
                num_components = 1


        if len(pointer_tab) == 5 and pointer_tab[1] == "materials" and \
            pointer_tab[3] == "pbrMetallicRoughness" and \
            pointer_tab[4] in ["baseColorFactor", "roughnessFactor", "metallicFactor"]:

            if pointer_tab[4] == "baseColorFactor":
                base_color_socket = get_socket(asset.blender_nodetree, True, "Base Color")
                if base_color_socket.is_linked:
                    # We need to find the correct node value to animate (An Mix Factor node)
                    mix_node = base_color_socket.links[0].from_node
                    if mix_node.type == "MIX":
                        blender_path = mix_node.inputs[7].path_from_id() + ".default_value"
                        num_components = 3 # Do not use alpha here, will be managed later
                    else:
                        print("Error, something is wrong, we didn't detect adding a Mix Node because of Pointers")
                else:
                    blender_path = base_color_socket.path_from_id() + ".default_value"
                    num_components = 3 # Do not use alpha here, will be managed later

            if pointer_tab[4] == "roughnessFactor":
                roughness_socket = get_socket(asset.blender_nodetree, True, "Roughness")
                if roughness_socket.is_linked:
                    # We need to find the correct node value to animate (An Mix Factor node)
                    mix_node = roughness_socket.links[0].from_node
                    if mix_node.type == "MATH":
                        blender_path = mix_node.inputs[1].path_from_id() + ".default_value"
                        num_components = 1
                    else:
                        print("Error, something is wrong, we didn't detect adding a Mix Node because of Pointers")
                else:
                    blender_path = roughness_socket.path_from_id() + ".default_value"
                    num_components = 1

            if pointer_tab[4] == "metallicFactor":
                metallic_socket = get_socket(asset.blender_nodetree, True, "Metallic")
                if metallic_socket.is_linked:
                    # We need to find the correct node value to animate (An Mix Factor node)
                    mix_node = metallic_socket.links[0].from_node
                    if mix_node.type == "MATH":
                        blender_path = mix_node.inputs[1].path_from_id() + ".default_value"
                        num_components = 1
                    else:
                        print("Error, something is wrong, we didn't detect adding a Mix Node because of Pointers")
                else:
                    blender_path = metallic_socket.path_from_id() + ".default_value"
                    num_components = 1

        if len(pointer_tab) == 8 and pointer_tab[1] == "materials" and \
            pointer_tab[3] == "pbrMetallicRoughness" and \
            pointer_tab[4] == "baseColorFactor" and \
            pointer_tab[5] == "extensions" and \
            pointer_tab[6] == "KHR_texture_transform" and \
            pointer_tab[7] in ["scale", "offset"]:

            pass
            # blender_path = ""
            # num_components =

        if len(pointer_tab) == 6 and pointer_tab[1] == "materials" and \
            pointer_tab[3] == "extensions" and \
            pointer_tab[4] == "KHR_materials_emissive_strength" and \
            pointer_tab[5] == "emissiveStrength":

            pass
            # blender_path = ""
            # num_components =

        if len(pointer_tab) == 6 and pointer_tab[1] == "materials" and \
            pointer_tab[3] == "extensions" and \
            pointer_tab[4] == "KHR_materials_volume" and \
            pointer_tab[5] in ["thicknessFactor", "attenuationDistance", "attenuationColor"]:

            pass
            # blender_path = ""
            # num_components =

        if len(pointer_tab) == 6 and pointer_tab[1] == "materials" and \
            pointer_tab[3] == "extensions" and \
            pointer_tab[4] == "KHR_materials_ior" and \
            pointer_tab[5] == "ior":

            pass
            # blender_path = ""
            # num_components =

        if len(pointer_tab) == 6 and pointer_tab[1] == "materials" and \
            pointer_tab[3] == "extensions" and \
            pointer_tab[4] == "KHR_materials_transmission" and \
            pointer_tab[5] == "transmissionFactor":

            pass
            # blender_path = ""
            # num_components =


        if blender_path is None:
            return # Should not happen if all specification is managed

        fps = bpy.context.scene.render.fps

        coords = [0] * (2 * len(keys))
        coords[::2] = (key[0] * fps for key in keys)

        for i in range(0, num_components):
            coords[1::2] = (vals[i] for vals in values)
            make_fcurve(
                action,
                coords,
                data_path=blender_path,
                index=i,
                group_name=group_name,
                interpolation=animation.samplers[channel.sampler].interpolation,
            )

        # For baseColorFactor, we also need to add keyframes to alpha socket
        if len(pointer_tab) == 5 and pointer_tab[1] == "materials" and \
                pointer_tab[3] == "pbrMetallicRoughness" and \
                pointer_tab[4] == "baseColorFactor":

            alpha_socket = get_socket(asset.blender_nodetree, True, "Alpha")
            if alpha_socket.is_linked:
                # We need to find the correct node value to animate (An Mix Factor node)
                mix_node = alpha_socket.links[0].from_node
                if mix_node.type == "MATH":
                    blender_path = mix_node.inputs[1].path_from_id() + ".default_value"
                else:
                    print("Error, something is wrong, we didn't detect adding a Mix Node because of Pointers")
            else:
                blender_path = alpha_socket.path_from_id() + ".default_value"

            coords[1::2] = (vals[3] for vals in values)
            make_fcurve(
                action,
                coords,
                data_path=blender_path,
                index=0,
                group_name=group_name,
                interpolation=animation.samplers[channel.sampler].interpolation,
            )

    @staticmethod
    def get_or_create_action(gltf, asset, asset_idx, anim_name, asset_type, name=None):

        action = None
        if asset_type == "CAMERA":
            data_name = "camera_" + asset.name or "Camera%d" % asset_idx
            action = gltf.action_cache.get(data_name)
            id_root = "CAMERA"
            stash = asset.blender_object_data
        elif asset_type == "LIGHT":
            data_name = "light_" + asset['name'] or "Light%d" % asset_idx
            action = gltf.action_cache.get(data_name)
            id_root = "LIGHT"
            stash = asset['blender_object_data']
        elif asset_type == "MATERIAL":
            data_name = "material_" + asset.name or "Material%d" % asset_idx
            action = gltf.action_cache.get(data_name)
            id_root = "MATERIAL"
            stash = asset.blender_mat
        elif asset_type == "NODETREE":
            name_ = name if name is not None else asset.name
            data_name = "nodetree_" + name_ or "Nodetree%d" % asset_idx
            action = gltf.action_cache.get(data_name)
            id_root = "NODETREE"
            stash = asset.blender_nodetree

        if not action:
            name = anim_name + "_" + data_name
            action = bpy.data.actions.new(name)
            action.id_root = id_root
            gltf.needs_stash.append((stash, action))
            gltf.action_cache[data_name] = action

        return action
