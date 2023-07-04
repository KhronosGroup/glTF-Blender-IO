# Copyright 2018-2021 The glTF-Blender-IO authors.
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
from .gltf2_blender_animation_node import BlenderNodeAnim
from .gltf2_blender_animation_weight import BlenderWeightAnim
from .gltf2_blender_animation_pointer import BlenderPointerAnim
from .gltf2_blender_animation_utils import simulate_stash, restore_animation_on_object
from .gltf2_blender_vnode import VNode

class BlenderAnimation():
    """Dispatch Animation to node or morph weights animation, or via KHR_animation_pointer"""
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("%s should not be instantiated" % cls)

    @staticmethod
    def anim(gltf, anim_idx):
        """Create actions/tracks for one animation."""
        # Caches the action for each object (keyed by object name)
        gltf.action_cache = {}
        # Things we need to stash when we're done.
        gltf.needs_stash = []

        import_user_extensions('gather_import_animation_before_hook', gltf, anim_idx)

        for vnode_id in gltf.vnodes:
            if isinstance(vnode_id, int):
                BlenderNodeAnim.anim(gltf, anim_idx, vnode_id)
            BlenderWeightAnim.anim(gltf, anim_idx, vnode_id)

        if gltf.data.extensions_used is not None and "KHR_animation_pointer" in gltf.data.extensions_used:
            for cam_idx, cam in enumerate(gltf.data.cameras if gltf.data.cameras else []):
                if len(cam.animations) == 0:
                    continue
                BlenderPointerAnim.anim(gltf, anim_idx, cam, cam_idx, 'CAMERA')

            if gltf.data.extensions is not None and "KHR_lights_punctual" in gltf.data.extensions:
                for light_idx, light in enumerate(gltf.data.extensions["KHR_lights_punctual"]["lights"]):
                    if len(light["animations"]) == 0:
                        continue
                    BlenderPointerAnim.anim(gltf, anim_idx, light, light_idx, 'LIGHT')

            for mat_idx, mat in enumerate(gltf.data.materials if gltf.data.materials else []):
                if len(mat.animations) != 0:
                    BlenderPointerAnim.anim(gltf, anim_idx, mat, mat_idx, 'MATERIAL')
                if mat.normal_texture is not None and len(mat.normal_texture.animations) != 0:
                    BlenderPointerAnim.anim(gltf, anim_idx, mat.normal_texture, mat_idx, 'MATERIAL_PBR', name=mat.name)
                if mat.pbr_metallic_roughness is not None and len(mat.pbr_metallic_roughness.animations) != 0:
                    BlenderPointerAnim.anim(gltf, anim_idx, mat.pbr_metallic_roughness, mat_idx, 'MATERIAL_PBR', name=mat.name)


        # Push all actions onto NLA tracks with this animation's name
        track_name = gltf.data.animations[anim_idx].track_name
        for (obj, action) in gltf.needs_stash:
            simulate_stash(obj, track_name, action)

        import_user_extensions('gather_import_animation_after_hook', gltf, anim_idx, track_name)

        if hasattr(bpy.data.scenes[0], 'gltf2_animation_tracks') is False:
            return

        if track_name not in [track.name for track in bpy.data.scenes[0].gltf2_animation_tracks]:
            new_ = bpy.data.scenes[0].gltf2_animation_tracks.add()
            new_.name = track_name
        # reverse order, as animation are created in reverse order (because of NLA adding tracks are reverted)
        bpy.data.scenes[0].gltf2_animation_tracks.move(len(bpy.data.scenes[0].gltf2_animation_tracks)-1, 0)

    @staticmethod
    def restore_animation(gltf, animation_name):
        """Restores the actions for an animation by its track name."""
        for vnode_id in gltf.vnodes:
            vnode = gltf.vnodes[vnode_id]
            if vnode.type == VNode.Bone:
                obj = gltf.vnodes[vnode.bone_arma].blender_object
            elif vnode.type == VNode.Object:
                obj = vnode.blender_object
            else:
                continue

            restore_animation_on_object(obj, animation_name)
            if obj.data and hasattr(obj.data, 'shape_keys'):
                restore_animation_on_object(obj.data.shape_keys, animation_name)

        if gltf.data.extensions_used is not None and "KHR_animation_pointer" in gltf.data.extensions_used:
            for cam in gltf.data.cameras:
                restore_animation_on_object(cam.blender_object_data, animation_name)

            if "KHR_lights_punctual" in gltf.data.extensions:
                for light in gltf.data.extensions['KHR_lights_punctual']['lights']:
                    restore_animation_on_object(light['blender_object_data'], animation_name)

            for mat in gltf.data.materials:
                restore_animation_on_object(mat.blender_nodetree, animation_name)
                restore_animation_on_object(mat.blender_mat, animation_name)
