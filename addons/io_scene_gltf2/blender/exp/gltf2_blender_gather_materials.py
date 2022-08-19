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

from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached, cached_by_key
from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.blender.exp import gltf2_blender_gather_materials_unlit
from io_scene_gltf2.blender.exp import gltf2_blender_gather_texture_info, gltf2_blender_export_keys
from io_scene_gltf2.blender.exp import gltf2_blender_gather_materials_pbr_metallic_roughness
from ..com.gltf2_blender_extras import generate_extras
from io_scene_gltf2.io.exp.gltf2_io_user_extensions import export_user_extensions
from io_scene_gltf2.io.com.gltf2_io_debug import print_console
from io_scene_gltf2.blender.exp.gltf2_blender_gather_materials_volume import export_volume
from io_scene_gltf2.blender.exp.gltf2_blender_gather_materials_emission import export_emission_factor, \
    export_emission_texture, export_emission_strength_extension
from io_scene_gltf2.blender.exp.gltf2_blender_gather_materials_sheen import export_sheen
from io_scene_gltf2.blender.exp.gltf2_blender_gather_materials_specular import export_specular
from io_scene_gltf2.blender.exp.gltf2_blender_gather_materials_transmission import export_transmission
from io_scene_gltf2.blender.exp.gltf2_blender_gather_materials_clearcoat import export_clearcoat
from io_scene_gltf2.blender.exp.gltf2_blender_gather_materials_ior import export_ior
from io_scene_gltf2.io.com.gltf2_io_extensions import Extension
from io_scene_gltf2.blender.exp.gltf2_blender_search_node_tree import \
    has_image_node_from_socket, \
    get_socket_from_gltf_material_node, \
    get_socket, \
    get_node_socket

@cached
def get_material_cache_key(blender_material, active_uvmap_index, export_settings):
    # Use id of material
    # Do not use bpy.types that can be unhashable
    # Do not use material name, that can be not unique (when linked)
    return (
      (id(blender_material),),
      (active_uvmap_index,)
    )

@cached_by_key(key=get_material_cache_key)
def gather_material(blender_material, active_uvmap_index, export_settings):
    """
    Gather the material used by the blender primitive.

    :param blender_material: the blender material used in the glTF primitive
    :param export_settings:
    :return: a glTF material
    """
    if not __filter_material(blender_material, export_settings):
        return None

    print("##################", blender_material.name)
    mat_unlit = __export_unlit(blender_material, active_uvmap_index, export_settings)
    if mat_unlit is not None:
        export_user_extensions('gather_material_hook', export_settings, mat_unlit, blender_material)
        return mat_unlit

    orm_texture = __gather_orm_texture(blender_material, export_settings)

    emissive_factor = __gather_emissive_factor(blender_material, export_settings)
    emissive_texture, uvmap_actives_emissive_texture = __gather_emissive_texture(blender_material, export_settings)
    extensions, uvmap_actives_extensions = __gather_extensions(blender_material, emissive_factor, export_settings)
    normal_texture, uvmap_actives_normal_texture = __gather_normal_texture(blender_material, export_settings)
    occlusion_texture, uvmap_actives_occlusion_texture = __gather_occlusion_texture(blender_material, orm_texture, export_settings)
    pbr_metallic_roughness, uvmap_actives_pbr_metallic_roughness = __gather_pbr_metallic_roughness(blender_material, orm_texture, export_settings)

    if any([i>1.0 for i in emissive_factor or []]) is True:
        # Strength is set on extension
        emission_strength = max(emissive_factor)
        emissive_factor = [f / emission_strength for f in emissive_factor]


    base_material = gltf2_io.Material(
        alpha_cutoff=__gather_alpha_cutoff(blender_material, export_settings),
        alpha_mode=__gather_alpha_mode(blender_material, export_settings),
        double_sided=__gather_double_sided(blender_material, export_settings),
        emissive_factor=emissive_factor,
        emissive_texture=emissive_texture,
        extensions=extensions,
        extras=__gather_extras(blender_material, export_settings),
        name=__gather_name(blender_material, export_settings),
        normal_texture=normal_texture,
        occlusion_texture=occlusion_texture,
        pbr_metallic_roughness=pbr_metallic_roughness
    )


    # merge all uvmap_actives
    uvmap_actives = []
    if uvmap_actives_emissive_texture:
        uvmap_actives.extend(uvmap_actives_emissive_texture)
    if uvmap_actives_extensions:
        uvmap_actives.extend(uvmap_actives_extensions)
    if uvmap_actives_normal_texture:
        uvmap_actives.extend(uvmap_actives_normal_texture)
    if uvmap_actives_occlusion_texture:
        uvmap_actives.extend(uvmap_actives_occlusion_texture)
    if uvmap_actives_pbr_metallic_roughness:
        uvmap_actives.extend(uvmap_actives_pbr_metallic_roughness)

    # Because some part of material are shared (eg pbr_metallic_roughness), we must copy the material
    # Texture must be shared, but not TextureInfo
    material = deepcopy(base_material)
    __get_new_material_texture_shared(base_material, material)

    active_uvmap_index = active_uvmap_index if active_uvmap_index != 0 else None

    for tex in uvmap_actives:
        if tex == "emissiveTexture":
            material.emissive_texture.tex_coord = active_uvmap_index
        elif tex == "normalTexture":
            material.normal_texture.tex_coord = active_uvmap_index
        elif tex == "occlusionTexture":
            material.occlusion_texture.tex_coord = active_uvmap_index
        elif tex == "baseColorTexture":
            material.pbr_metallic_roughness.base_color_texture.tex_coord = active_uvmap_index
        elif tex == "metallicRoughnessTexture":
            material.pbr_metallic_roughness.metallic_roughness_texture.tex_coord = active_uvmap_index
        elif tex == "clearcoatTexture":
            material.extensions["KHR_materials_clearcoat"].extension['clearcoatTexture'].tex_coord = active_uvmap_index
        elif tex == "clearcoatRoughnessTexture":
            material.extensions["KHR_materials_clearcoat"].extension['clearcoatRoughnessTexture'].tex_coord = active_uvmap_index
        elif tex == "clearcoatNormalTexture": #TODO not tested yet
            material.extensions["KHR_materials_clearcoat"].extension['clearcoatNormalTexture'].tex_coord = active_uvmap_index
        elif tex == "transmissionTexture": #TODO not tested yet
            material.extensions["KHR_materials_transmission"].extension['transmissionTexture'].tex_coord = active_uvmap_index
        elif tex == "specularTexture":
            material.extensions["KHR_materials_specular"].extension['specularTexture'].tex_coord = active_uvmap_index
        elif tex == "specularColorTexture":
            material.extensions["KHR_materials_specular"].extension['specularColorTexture'].tex_coord = active_uvmap_index
        elif tex == "sheenColorTexture":
            material.extensions["KHR_materials_sheen"].extension['sheenColorTexture'].tex_coord = active_uvmap_index
        elif tex == "sheenRoughnessTexture":
            material.extensions["KHR_materials_sheen"].extension['sheenRoughnessTexture'].tex_coord = active_uvmap_index

    # If material is not using active UVMap, we need to return the same material,
    # Even if multiples meshes are using different active UVMap
    if len(uvmap_actives) == 0 and active_uvmap_index != -1:
        material = gather_material(blender_material, -1, export_settings)


    # If emissive is set, from an emissive node (not PBR)
    # We need to set manually default values for
    # pbr_metallic_roughness.baseColor
    if material.emissive_factor is not None and get_node_socket(blender_material, bpy.types.ShaderNodeBsdfPrincipled, "Base Color").socket is None:
        material.pbr_metallic_roughness = gltf2_blender_gather_materials_pbr_metallic_roughness.get_default_pbr_for_emissive_node()

    export_user_extensions('gather_material_hook', export_settings, material, blender_material)

    return material

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
    return export_settings[gltf2_blender_export_keys.MATERIALS]


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


def __gather_double_sided(blender_material, export_settings):
    if not blender_material.use_backface_culling:
        return True
    return None


def __gather_emissive_factor(blender_material, export_settings):
    return export_emission_factor(blender_material, export_settings)

def __gather_emissive_texture(blender_material, export_settings):
    return export_emission_texture(blender_material, export_settings)


def __gather_extensions(blender_material, emissive_factor, export_settings):
    extensions = {}

    # KHR_materials_clearcoat
    actives_uvmaps = []

    clearcoat_extension, use_actives_uvmap_clearcoat = export_clearcoat(blender_material, export_settings)
    if clearcoat_extension:
        extensions["KHR_materials_clearcoat"] = clearcoat_extension
        actives_uvmaps.extend(use_actives_uvmap_clearcoat)

    # KHR_materials_transmission

    transmission_extension, use_actives_uvmap_transmission = export_transmission(blender_material, export_settings)
    if transmission_extension:
        extensions["KHR_materials_transmission"] = transmission_extension
        actives_uvmaps.extend(use_actives_uvmap_transmission)

    # KHR_materials_emissive_strength
    if any([i>1.0 for i in emissive_factor or []]):
        emissive_strength_extension = export_emission_strength_extension(emissive_factor, export_settings)
        if emissive_strength_extension:
            extensions["KHR_materials_emissive_strength"] = emissive_strength_extension

    # KHR_materials_volume

    volume_extension, use_actives_uvmap_volume_thickness  = export_volume(blender_material, export_settings)
    if volume_extension:
        extensions["KHR_materials_volume"] = volume_extension
        actives_uvmaps.extend(use_actives_uvmap_volume_thickness)

    # KHR_materials_specular
    specular_extension, use_actives_uvmap_specular = export_specular(blender_material, export_settings)
    if specular_extension:
        extensions["KHR_materials_specular"] = specular_extension
        actives_uvmaps.extend(use_actives_uvmap_specular)

    # KHR_materials_sheen
    sheen_extension, use_actives_uvmap_sheen = export_sheen(blender_material, export_settings)
    if sheen_extension:
        extensions["KHR_materials_sheen"] = sheen_extension
        actives_uvmaps.extend(use_actives_uvmap_sheen)   

    # KHR_materials_ior
    # Keep this extension at the end, because we export it only if some others are exported
    ior_extension = export_ior(blender_material, extensions, export_settings)
    if ior_extension:
        extensions["KHR_materials_ior"] = ior_extension

    return extensions, actives_uvmaps if extensions else None


def __gather_extras(blender_material, export_settings):
    if export_settings['gltf_extras']:
        return generate_extras(blender_material)
    return None


def __gather_name(blender_material, export_settings):
    return blender_material.name


def __gather_normal_texture(blender_material, export_settings):
    normal = get_socket(blender_material, "Normal")
    normal_texture, use_active_uvmap_normal, _ = gltf2_blender_gather_texture_info.gather_material_normal_texture_info_class(
        normal,
        (normal,),
        export_settings)
    return normal_texture, ["normalTexture"] if use_active_uvmap_normal else None


def __gather_orm_texture(blender_material, export_settings):
    # Check for the presence of Occlusion, Roughness, Metallic sharing a single image.
    # If not fully shared, return None, so the images will be cached and processed separately.

    occlusion = get_socket(blender_material, "Occlusion")
    if occlusion.socket is None or not has_image_node_from_socket(occlusion, export_settings):
        occlusion = get_socket_from_gltf_material_node(blender_material, "Occlusion")
        if occlusion.socket is None or not has_image_node_from_socket(occlusion, export_settings):
            return None

    metallic_socket = get_socket(blender_material, "Metallic")
    roughness_socket = get_socket(blender_material, "Roughness")

    hasMetal = metallic_socket.socket is not None and has_image_node_from_socket(metallic_socket, export_settings)
    hasRough = roughness_socket.socket is not None and has_image_node_from_socket(roughness_socket, export_settings)

    if not hasMetal and not hasRough:
        return None
    elif not hasMetal:
        result = (occlusion, roughness_socket)
    elif not hasRough:
        result = (occlusion, metallic_socket)
    else:
        result = (occlusion, roughness_socket, metallic_socket)

    if not gltf2_blender_gather_texture_info.check_same_size_images(result, export_settings):
        print_console("INFO",
            "Occlusion and metal-roughness texture will be exported separately "
            "(use same-sized images if you want them combined)")
        return None

    # Double-check this will past the filter in texture_info
    info, info_use_active_uvmap, _ = gltf2_blender_gather_texture_info.gather_texture_info(result[0], result, export_settings)
    if info is None:
        return None

    return result

def __gather_occlusion_texture(blender_material, orm_texture, export_settings):
    occlusion = get_socket(blender_material, "Occlusion")
    if occlusion.socket is None:
        occlusion = get_socket_from_gltf_material_node(blender_material, "Occlusion")
    occlusion_texture, use_active_uvmap_occlusion, _ = gltf2_blender_gather_texture_info.gather_material_occlusion_texture_info_class(
        occlusion,
        orm_texture or (occlusion,),
        export_settings)
    return occlusion_texture, ["occlusionTexture"] if use_active_uvmap_occlusion else None


def __gather_pbr_metallic_roughness(blender_material, orm_texture, export_settings):
    return gltf2_blender_gather_materials_pbr_metallic_roughness.gather_material_pbr_metallic_roughness(
        blender_material,
        orm_texture,
        export_settings)

def __export_unlit(blender_material, active_uvmap_index, export_settings):
    gltf2_unlit = gltf2_blender_gather_materials_unlit

    info = gltf2_unlit.detect_shadeless_material(blender_material, export_settings)
    if info is None:
        return None

    base_color_texture, use_active_uvmap = gltf2_unlit.gather_base_color_texture(info, export_settings)

    base_material = gltf2_io.Material(
        alpha_cutoff=__gather_alpha_cutoff(blender_material, export_settings),
        alpha_mode=__gather_alpha_mode(blender_material, export_settings),
        double_sided=__gather_double_sided(blender_material, export_settings),
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

    if use_active_uvmap is not None:
        # Because some part of material are shared (eg pbr_metallic_roughness), we must copy the material
        # Texture must be shared, but not TextureInfo
        material = deepcopy(base_material)
        __get_new_material_texture_shared(base_material, material)
        material.pbr_metallic_roughness.base_color_texture.tex_coord = active_uvmap_index
    elif use_active_uvmap is None and active_uvmap_index != -1:
        # If material is not using active UVMap, we need to return the same material,
        # Even if multiples meshes are using different active UVMap
        material = gather_material(blender_material, -1, export_settings)
    else:
        material = base_material

    export_user_extensions('gather_material_unlit_hook', export_settings, material, blender_material)

    return material
