# Copyright 2018-2022 The glTF-Blender-IO authors.
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

from copy import deepcopy
import bpy

from ....io.com import gltf2_io
from ....io.com.gltf2_io_extensions import Extension
from ....io.exp.gltf2_io_user_extensions import export_user_extensions
from ....io.com.gltf2_io_debug import print_console
from ...com.gltf2_blender_extras import generate_extras
from ...exp import gltf2_blender_get
from ..gltf2_blender_gather_cache import cached, cached_by_key
from . import gltf2_blender_gather_materials_unlit
from . import gltf2_blender_gather_texture_info
from . import gltf2_blender_gather_materials_pbr_metallic_roughness
from .extensions.gltf2_blender_gather_materials_volume import export_volume
from .extensions.gltf2_blender_gather_materials_emission import export_emission_factor, \
    export_emission_texture, export_emission_strength_extension
from .extensions.gltf2_blender_gather_materials_sheen import export_sheen
from .extensions.gltf2_blender_gather_materials_specular import export_specular
from .extensions.gltf2_blender_gather_materials_transmission import export_transmission
from .extensions.gltf2_blender_gather_materials_clearcoat import export_clearcoat
from .extensions.gltf2_blender_gather_materials_ior import export_ior

@cached
def get_material_cache_key(blender_material, export_settings):
    # Use id of material
    # Do not use bpy.types that can be unhashable
    # Do not use material name, that can be not unique (when linked)
    return (
      (id(blender_material),),
    )

@cached_by_key(key=get_material_cache_key)
def gather_material(blender_material, export_settings):
    """
    Gather the material used by the blender primitive.

    :param blender_material: the blender material used in the glTF primitive
    :param export_settings:
    :return: a glTF material
    """
    if not __filter_material(blender_material, export_settings):
        return None, {}

    mat_unlit, uvmap_info, vc_info = __export_unlit(blender_material, export_settings)
    if mat_unlit is not None:
        export_user_extensions('gather_material_hook', export_settings, mat_unlit, blender_material)
        return mat_unlit, {"uv_info": uvmap_info, "vc_info": vc_info}

    orm_texture, default_sockets = __gather_orm_texture(blender_material, export_settings)

    emissive_factor = __gather_emissive_factor(blender_material, export_settings)
    emissive_texture, uvmap_info_emissive = __gather_emissive_texture(blender_material, export_settings)
    extensions, uvmap_info_extensions = __gather_extensions(blender_material, emissive_factor, export_settings)
    normal_texture, uvmap_info_normal = __gather_normal_texture(blender_material, export_settings)
    occlusion_texture, uvmap_info_occlusion = __gather_occlusion_texture(blender_material, orm_texture, default_sockets, export_settings)
    pbr_metallic_roughness, uvmap_info_pbr_metallic_roughness, vc_info = __gather_pbr_metallic_roughness(blender_material, orm_texture, export_settings)

    if any([i>1.0 for i in emissive_factor or []]) is True:
        # Strength is set on extension
        emission_strength = max(emissive_factor)
        emissive_factor = [f / emission_strength for f in emissive_factor]


    material = gltf2_io.Material(
        alpha_cutoff=__gather_alpha_cutoff(blender_material, export_settings),
        alpha_mode=__gather_alpha_mode(blender_material, export_settings),
        double_sided=__gather_double_sided(blender_material, extensions, export_settings),
        emissive_factor=emissive_factor,
        emissive_texture=emissive_texture,
        extensions=extensions,
        extras=__gather_extras(blender_material, export_settings),
        name=__gather_name(blender_material, export_settings),
        normal_texture=normal_texture,
        occlusion_texture=occlusion_texture,
        pbr_metallic_roughness=pbr_metallic_roughness
    )

    uvmap_infos = {}
    uvmap_infos.update(uvmap_info_emissive)
    uvmap_infos.update(uvmap_info_extensions)
    uvmap_infos.update(uvmap_info_normal)
    uvmap_infos.update(uvmap_info_occlusion)
    uvmap_infos.update(uvmap_info_pbr_metallic_roughness)


    # If emissive is set, from an emissive node (not PBR)
    # We need to set manually default values for
    # pbr_metallic_roughness.baseColor
    if material.emissive_factor is not None and gltf2_blender_get.get_node_socket(blender_material.node_tree, bpy.types.ShaderNodeBsdfPrincipled, "Base Color") is None:
        material.pbr_metallic_roughness = gltf2_blender_gather_materials_pbr_metallic_roughness.get_default_pbr_for_emissive_node()

    export_user_extensions('gather_material_hook', export_settings, material, blender_material)

    # Now we have exported the material itself, we need to store some additional data
    # This will be used when trying to export some KHR_animation_pointer

    #TODOPointer for baseColorFactor, we need to merge color + alpha

    if len(export_settings['current_paths']) > 0:
        export_settings['KHR_animation_pointer']['materials'][id(blender_material)] = {}
        export_settings['KHR_animation_pointer']['materials'][id(blender_material)]['paths'] = export_settings['current_paths'].copy()
        export_settings['KHR_animation_pointer']['materials'][id(blender_material)]['glTF_material'] = material

    return material, {"uv_info": uvmap_infos, "vc_info": vc_info}


def __get_new_material_texture_shared(base, node):
        if node is None:
            return
        if callable(node) is True:
            return
        if node.__str__().startswith('__'):
            return
        if type(node) in [gltf2_io.TextureInfo, gltf2_io.MaterialOcclusionTextureInfoClass, gltf2_io.MaterialNormalTextureInfoClass]:
            node.index = base.index
        else:
            if hasattr(node, '__dict__'):
                for attr, value in node.__dict__.items():
                    __get_new_material_texture_shared(getattr(base, attr), value)
            else:
                # For extensions (on a dict)
                if type(node).__name__ == 'dict':
                    for i in node.keys():
                        __get_new_material_texture_shared(base[i], node[i])

def __filter_material(blender_material, export_settings):
    return export_settings['gltf_materials']


def __gather_alpha_cutoff(blender_material, export_settings):
    if blender_material.blend_method == 'CLIP':
        return blender_material.alpha_threshold
    return None


def __gather_alpha_mode(blender_material, export_settings):
    if blender_material.blend_method == 'CLIP':
        return 'MASK'
    elif blender_material.blend_method in ['BLEND', 'HASHED']:
        return 'BLEND'
    return None


def __gather_double_sided(blender_material, extensions, export_settings):

    # If user create a volume extension, we force double sided to False
    if 'KHR_materials_volume' in extensions:
        return False

    if not blender_material.use_backface_culling:
        return True

    old_double_sided_socket = gltf2_blender_get.get_socket_old(blender_material, "DoubleSided")
    if old_double_sided_socket is not None and\
            not old_double_sided_socket.is_linked and\
            old_double_sided_socket.default_value > 0.5:
        return True
    return None


def __gather_emissive_factor(blender_material, export_settings):
    return export_emission_factor(blender_material, export_settings)

def __gather_emissive_texture(blender_material, export_settings):
    return export_emission_texture(blender_material, export_settings)


def __gather_extensions(blender_material, emissive_factor, export_settings):
    extensions = {}

    uvmap_infos = {}

    # KHR_materials_clearcoat
    clearcoat_extension, uvmap_info = export_clearcoat(blender_material, export_settings)
    if clearcoat_extension:
        extensions["KHR_materials_clearcoat"] = clearcoat_extension
        uvmap_infos.update(uvmap_infos)

    # KHR_materials_transmission

    transmission_extension, uvmap_info = export_transmission(blender_material, export_settings)
    if transmission_extension:
        extensions["KHR_materials_transmission"] = transmission_extension
        uvmap_infos.update(uvmap_infos)

    # KHR_materials_emissive_strength
    if any([i>1.0 for i in emissive_factor or []]):
        emissive_strength_extension = export_emission_strength_extension(emissive_factor, export_settings)
        if emissive_strength_extension:
            extensions["KHR_materials_emissive_strength"] = emissive_strength_extension

    # KHR_materials_volume

    volume_extension, uvmap_info  = export_volume(blender_material, export_settings)
    if volume_extension:
        extensions["KHR_materials_volume"] = volume_extension
        uvmap_infos.update(uvmap_info)

    # KHR_materials_specular
    specular_extension, uvmap_info = export_specular(blender_material, export_settings)
    if specular_extension:
        extensions["KHR_materials_specular"] = specular_extension
        uvmap_infos.update(uvmap_info)

    # KHR_materials_sheen
    sheen_extension, uvmap_info = export_sheen(blender_material, export_settings)
    if sheen_extension:
        extensions["KHR_materials_sheen"] = sheen_extension
        uvmap_infos.update(uvmap_info)

    # KHR_materials_ior
    # Keep this extension at the end, because we export it only if some others are exported
    ior_extension = export_ior(blender_material, extensions, export_settings)
    if ior_extension:
        extensions["KHR_materials_ior"] = ior_extension

    return extensions, uvmap_infos


def __gather_extras(blender_material, export_settings):
    if export_settings['gltf_extras']:
        return generate_extras(blender_material)
    return None


def __gather_name(blender_material, export_settings):
    return blender_material.name


def __gather_normal_texture(blender_material, export_settings):
    normal = gltf2_blender_get.get_socket(blender_material.node_tree, blender_material.use_nodes, "Normal")
    if normal is None:
        normal = gltf2_blender_get.get_socket_old(blender_material, "Normal")
    normal_texture, uvmap_info, _  = gltf2_blender_gather_texture_info.gather_material_normal_texture_info_class(
        normal,
        (normal,),
        export_settings)
    return normal_texture, {"normalTexture" : uvmap_info}


def __gather_orm_texture(blender_material, export_settings):
    # Check for the presence of Occlusion, Roughness, Metallic sharing a single image.
    # If not fully shared, return None, so the images will be cached and processed separately.

    occlusion = gltf2_blender_get.get_socket(blender_material.node_tree, blender_material.use_nodes, "Occlusion")
    if occlusion is None or not gltf2_blender_get.has_image_node_from_socket(occlusion):
        occlusion = gltf2_blender_get.get_socket_old(blender_material, "Occlusion")
        if occlusion is None or not gltf2_blender_get.has_image_node_from_socket(occlusion):
            return None, None

    metallic_socket = gltf2_blender_get.get_socket(blender_material.node_tree, blender_material.use_nodes, "Metallic")
    roughness_socket = gltf2_blender_get.get_socket(blender_material.node_tree, blender_material.use_nodes, "Roughness")

    hasMetal = metallic_socket is not None and gltf2_blender_get.has_image_node_from_socket(metallic_socket)
    hasRough = roughness_socket is not None and gltf2_blender_get.has_image_node_from_socket(roughness_socket)

    default_sockets = ()
    if not hasMetal and not hasRough:
        metallic_roughness = gltf2_blender_get.get_socket_old(blender_material, "MetallicRoughness")
        if metallic_roughness is None or not gltf2_blender_get.has_image_node_from_socket(metallic_roughness):
            return None, default_sockets
        result = (occlusion, metallic_roughness)
    elif not hasMetal:
        result = (occlusion, roughness_socket)
        default_sockets = (metallic_socket,)
    elif not hasRough:
        result = (occlusion, metallic_socket)
        default_sockets = (roughness_socket,)
    else:
        result = (occlusion, roughness_socket, metallic_socket)
        default_sockets = ()

    if not gltf2_blender_gather_texture_info.check_same_size_images(result):
        print_console("INFO",
            "Occlusion and metal-roughness texture will be exported separately "
            "(use same-sized images if you want them combined)")
        return None, ()

    # Double-check this will past the filter in texture_info
    info, _, _ = gltf2_blender_gather_texture_info.gather_texture_info(result[0], result, default_sockets, export_settings)
    if info is None:
        return None, ()

    return result, default_sockets

def __gather_occlusion_texture(blender_material, orm_texture, default_sockets, export_settings):
    occlusion = gltf2_blender_get.get_socket(blender_material.node_tree, blender_material.use_nodes, "Occlusion")
    if occlusion is None:
        occlusion = gltf2_blender_get.get_socket_old(blender_material, "Occlusion")
    occlusion_texture, uvmap_info, _ = gltf2_blender_gather_texture_info.gather_material_occlusion_texture_info_class(
        occlusion,
        orm_texture or (occlusion,),
        default_sockets,
        export_settings)
    return occlusion_texture, \
            {"occlusionTexture" : uvmap_info}


def __gather_pbr_metallic_roughness(blender_material, orm_texture, export_settings):
    return gltf2_blender_gather_materials_pbr_metallic_roughness.gather_material_pbr_metallic_roughness(
        blender_material,
        orm_texture,
        export_settings)

def __export_unlit(blender_material, export_settings):
    gltf2_unlit = gltf2_blender_gather_materials_unlit

    info = gltf2_unlit.detect_shadeless_material(blender_material, export_settings)
    if info is None:
        return None, {}, {"color": None, "alpha": None}

    base_color_texture, uvmap_info, vc_info = gltf2_unlit.gather_base_color_texture(info, export_settings)

    material = gltf2_io.Material(
        alpha_cutoff=__gather_alpha_cutoff(blender_material, export_settings),
        alpha_mode=__gather_alpha_mode(blender_material, export_settings),
        double_sided=__gather_double_sided(blender_material, {}, export_settings),
        extensions={"KHR_materials_unlit": Extension("KHR_materials_unlit", {}, required=False)},
        extras=__gather_extras(blender_material, export_settings),
        name=__gather_name(blender_material, export_settings),
        emissive_factor=None,
        emissive_texture=None,
        normal_texture=None,
        occlusion_texture=None,

        pbr_metallic_roughness=gltf2_io.MaterialPBRMetallicRoughness(
            base_color_factor=gltf2_unlit.gather_base_color_factor(info, export_settings),
            base_color_texture=base_color_texture,
            metallic_factor=0.0,
            roughness_factor=0.9,
            metallic_roughness_texture=None,
            extensions=None,
            extras=None,
        )
    )

    export_user_extensions('gather_material_unlit_hook', export_settings, material, blender_material)

    return material, uvmap_info, vc_info

def get_active_uvmap_index(blender_mesh):
    # retrieve active render UVMap
    active_uvmap_idx = 0
    for i in range(len(blender_mesh.uv_layers)):
        if blender_mesh.uv_layers[i].active_render is True:
            active_uvmap_idx = i
            break
    return active_uvmap_idx


def get_final_material(mesh, blender_material, attr_indices, base_material, uvmap_info, export_settings):

    # First, we need to calculate all index of UVMap

    indices = {}

    for m, v in uvmap_info.items():

        if not 'type' in v.keys():
            continue

        if v['type'] == 'Fixed':
            i = mesh.uv_layers.find(v['value'])
            if i >= 0:
                indices[m] = i
            else:
                # Using active index
                indices[m] = get_active_uvmap_index(mesh)
        elif v['type'] == 'Active':
            indices[m] = get_active_uvmap_index(mesh)
        elif v['type'] == "Attribute":
            indices[m] = attr_indices[v['value']]

    # Now we have all needed indices, let's create a set that can be used for caching, so containing all possible textures
    all_textures = get_all_textures()

    caching_indices = []
    for tex in all_textures:
        caching_indices.append(indices.get(tex, None))

    caching_indices = [i if i != 0 else None for i in caching_indices]
    caching_indices = tuple(caching_indices)

    material = __get_final_material_with_indices(blender_material, base_material, caching_indices, export_settings)

    return material


@cached
def caching_material_tex_indices(blender_material, material, caching_indices, export_settings):
    return (
      (id(blender_material),),
      (caching_indices,)
    )

@cached_by_key(key=caching_material_tex_indices)
def __get_final_material_with_indices(blender_material, base_material, caching_indices, export_settings):

    if base_material is None:
        return None

    if all([i is None for i in caching_indices]):
        return base_material

    material = deepcopy(base_material)
    __get_new_material_texture_shared(base_material, material)

    for tex, ind in zip(get_all_textures(), caching_indices):

        if ind is None:
            continue

        if tex == "emissiveTexture":
            material.emissive_texture.tex_coord = ind
        elif tex == "normalTexture":
            material.normal_texture.tex_coord = ind
        elif tex == "occlusionTexture":
            material.occlusion_texture.tex_coord = ind
        elif tex == "baseColorTexture":
            material.pbr_metallic_roughness.base_color_texture.tex_coord = ind
        elif tex == "metallicRoughnessTexture":
            material.pbr_metallic_roughness.metallic_roughness_texture.tex_coord = ind
        elif tex == "clearcoatTexture":
            material.extensions["KHR_materials_clearcoat"].extension['clearcoatTexture'].tex_coord = ind
        elif tex == "clearcoatRoughnessTexture":
            material.extensions["KHR_materials_clearcoat"].extension['clearcoatRoughnessTexture'].tex_coord = ind
        elif tex == "clearcoatNormalTexture":
            material.extensions["KHR_materials_clearcoat"].extension['clearcoatNormalTexture'].tex_coord = ind
        elif tex == "transmissionTexture":
            material.extensions["KHR_materials_transmission"].extension['transmissionTexture'].tex_coord = ind
        elif tex == "specularTexture":
            material.extensions["KHR_materials_specular"].extension['specularTexture'].tex_coord = ind
        elif tex == "specularColorTexture":
            material.extensions["KHR_materials_specular"].extension['specularColorTexture'].tex_coord = ind
        elif tex == "sheenColorTexture":
            material.extensions["KHR_materials_sheen"].extension['sheenColorTexture'].tex_coord = ind
        elif tex == "sheenRoughnessTexture":
            material.extensions["KHR_materials_sheen"].extension['sheenRoughnessTexture'].tex_coord = ind
        elif tex == "thicknessTexture":
            material.extensions["KHR_materials_volume"].extension['thicknessTexture'].tex_ccord = ind
        else:
            print_console("ERROR", "some Textures tex coord are not managed")

    return material


def get_material_from_idx(material_idx, materials, export_settings):
    mat = None
    if export_settings['gltf_materials'] == "EXPORT" and material_idx is not None:
        if materials:
            i = material_idx if material_idx < len(materials) else -1
            mat = materials[i]
    return mat

def get_base_material(material_idx, materials, export_settings):

    material = None
    material_info = {"uv_info": {}, "vc_info": {}}

    mat = get_material_from_idx(material_idx, materials, export_settings)
    if mat is not None:
        material, material_info = gather_material(
            mat,
            export_settings
        )
    return material, material_info

def get_all_textures():
    # Make sure to have all texture here, always in same order
    tab = []

    tab.append("emissiveTexture")
    tab.append("normalTexture")
    tab.append("occlusionTexture")
    tab.append("baseColorTexture")
    tab.append("metallicRoughnessTexture")
    tab.append("clearcoatTexture")
    tab.append("clearcoatRoughnessTexture")
    tab.append("clearcoatNormalTexture")
    tab.append("transmissionTexture")
    tab.append("specularTexture")
    tab.append("specularColorTexture")
    tab.append("sheenColorTexture")
    tab.append("sheenRoughnessTexture")
    tab.append("thicknessTexture")

    return tab

# #TODOPointer add cache
# def __get_blender_actions(blender_material, export_settings):

#     blender_actions = []
#     blender_tracks = {}
#     action_on_type = {}

#     if blender_material.animation_data is not None:
#         # Collect active action
#         if blender_material.animation_data.action is not None:
#             blender_actions.append(blender_material.animation_data.action)
#             blender_tracks[blender_material.animation_data.action.name] = None
#             action_on_type[blender_material.animation_data.action.name] = "MATERIAL"

#         # Collect associated strips from NLA tracks.
#         if export_settings['gltf_animation_mode'] == "ACTIONS":
#             for track in blender_material.animation_data.nla_tracks:
#                 # Multi-strip tracks do not export correctly yet (they need to be baked),
#                 # so skip them for now and only write single-strip tracks.
#                 non_muted_strips = [strip for strip in track.strips if strip.action is not None and strip.mute is False]
#                 if track.strips is None or len(non_muted_strips) != 1:
#                     continue
#                 for strip in non_muted_strips:
#                     blender_actions.append(strip.action)
#                     blender_tracks[strip.action.name] = track.name # Always set after possible active action -> None will be overwrite
#                     action_on_type[strip.action.name] = "MATERIAL"

#     if blender_material.use_nodes and blender_material.node_tree.animation_data is not None:
#         # Collect active action
#         if blender_material.node_tree.animation_data.action is not None:
#             blender_actions.append(blender_material.node_tree.animation_data.action)
#             blender_tracks[blender_material.node_tree.animation_data.action.name] = None
#             action_on_type[blender_material.node_tree.animation_data.action.name] = "NODETREE"

#         # Collect associated strips from NLA tracks.
#         if export_settings['gltf_animation_mode'] == "ACTIONS":
#             for track in blender_material.node_tree.animation_data.nla_tracks:
#                 # Multi-strip tracks do not export correctly yet (they need to be baked),
#                 # so skip them for now and only write single-strip tracks.
#                 non_muted_strips = [strip for strip in track.strips if strip.action is not None and strip.mute is False]
#                 if track.strips is None or len(non_muted_strips) != 1:
#                     continue
#                 for strip in non_muted_strips:
#                     blender_actions.append(strip.action)
#                     blender_tracks[strip.action.name] = track.name # Always set after possible active action -> None will be overwrite
#                     action_on_type[strip.action.name] = "NODETREE"

#     # Remove duplicate actions.
#     blender_actions = list(set(blender_actions))
#     # sort animations alphabetically (case insensitive) so they have a defined order and match Blender's Action list
#     blender_actions.sort(key = lambda a: a.name.lower())

#     return [(blender_action, blender_tracks[blender_action.name], action_on_type[blender_action.name]) for blender_action in blender_actions]

# def gather_animation_fcurves(
#         blender_material,
#         blender_action: bpy.types.Action,
#         export_settings
#         ):

#     print(">1")

#     name = __gather_name(blender_action, export_settings)

#     channels, to_be_sampled = __gather_channels_fcurves(blender_material, blender_action, export_settings)

#     animation = gltf2_io.Animation(
#         channels=channels,
#         extensions=None,
#         extras=__gather_extras_animation(blender_action, export_settings),
#         name=name,
#         samplers=[]
#     )

#     if not animation.channels:
#         return None, to_be_sampled

#     return animation, to_be_sampled

# def __gather_extras_animation(blender_action, export_settings):
#     if export_settings['gltf_extras']:
#         return generate_extras(blender_action)
#     return None

# #TODOPointer to cache ?
# def __gather_channels_fcurves(blender_material, blender_action, export_settings):

#     channels_to_perform, to_be_sampled = get_channel_groups(blender_material, blender_action, "MATERIAL", export_settings)

#     print(channels_to_perform)

#     # custom_range = None
#     # if blender_action.use_frame_range:
#     #     custom_range = (blender_action.frame_start, blender_action.frame_end)

#     # channels = []
#     # for chan in [chan for chan in channels_to_perform.values() if len(chan['properties']) != 0]:
#     #     for channel_group in chan['properties'].values():
#     #         channel = __gather_animation_fcurve_channel(blender_material, channel_group, custom_range, export_settings)
#     #         if channel is not None:
#     #             channels.append(channel)


#     # return channels, to_be_sampled

# def get_channel_groups(asset, blender_action: bpy.types.Action, asset_type, export_settings):
#     targets = {}


#     to_be_sampled = [] # (asset , type , prop ) : type can be material or nodetree

#     for fcurve in blender_action.fcurves:
#         type_ = None
#         # In some invalid files, channel hasn't any keyframes ... this channel need to be ignored
#         if len(fcurve.keyframe_points) == 0:
#             continue
#         try:
#             # example of target_property for material or nodetree TODOPointer
#             target_property = get_target_property_name(fcurve.data_path)
#         except:
#             gltf2_io_debug.print_console("WARNING", "Invalid animation fcurve name on action {}".format(blender_action.name))
#             continue
#         object_path = get_target_object_path(fcurve.data_path)

#         # find the material affected by this action
#         # material_path : blank for asset itself, nodes[...] for NODETREE
#         if not object_path:
#             target = asset
#             type_ = asset_type
#         else:
#             target = get_object_from_datapath(asset, object_path)
#             type_ = "NODETREE" if object_path.startswith("nodes.") else None


#         # group channels by target object and affected property of the target
#         target_data = targets.get(target, {})
#         target_data['type'] = type_
#         target_data['asset'] = asset

#         target_properties = target_data.get('properties', {})
#         channels = target_properties.get(target_property, [])
#         channels.append(fcurve)
#         target_properties[target_property] = channels
#         target_data['properties'] = target_properties
#         targets[target] = target_data


#     # Now that all curves are extracted,
#     #    - check that there is no normal + delta transforms
#     #    - check that each group can be exported not sampled
#     #    - be sure that shapekeys curves are correctly sorted

#     for obj, target_data in targets.items():
#         properties = target_data['properties'].keys()
#         properties = [get_target(prop) for prop in properties]

#         # Check if the property can be exported without sampling
#         new_properties = {}
#         for prop in target_data['properties'].keys():
#             # if needs_baking(asset, target_data['properties'][prop], export_settings) is True:
#             #     to_be_sampled.append((obj_uuid, target_data['type'], get_channel_from_target(get_target(prop)), target_data['bone'])) # bone can be None if not a bone :)
#             # else: #TODOPointer
#             new_properties[prop] = target_data['properties'][prop]

#         target_data['properties'] = new_properties

#         for prop in target_data['properties'].keys():
#             target_data['properties'][prop] = tuple(target_data['properties'][prop])

#     to_be_sampled = list(set(to_be_sampled))

#     return targets, to_be_sampled
