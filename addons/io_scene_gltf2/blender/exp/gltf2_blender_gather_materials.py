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

from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached
from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.io.com.gltf2_io_extensions import Extension
from io_scene_gltf2.blender.exp import gltf2_blender_gather_texture_info, gltf2_blender_export_keys
from io_scene_gltf2.blender.exp import gltf2_blender_search_node_tree

from io_scene_gltf2.blender.exp import gltf2_blender_gather_materials_pbr_metallic_roughness
from io_scene_gltf2.blender.exp import gltf2_blender_gather_materials_unlit
from ..com.gltf2_blender_extras import generate_extras
from io_scene_gltf2.blender.exp import gltf2_blender_get
from io_scene_gltf2.io.exp.gltf2_io_user_extensions import export_user_extensions
from io_scene_gltf2.io.com.gltf2_io_debug import print_console


@cached
def gather_material(blender_material, export_settings):
    """
    Gather the material used by the blender primitive.

    :param blender_material: the blender material used in the glTF primitive
    :param export_settings:
    :return: a glTF material
    """
    if not __filter_material(blender_material, export_settings):
        return None

    mat_unlit = __gather_material_unlit(blender_material, export_settings)
    if mat_unlit is not None:
        return mat_unlit

    orm_texture = __gather_orm_texture(blender_material, export_settings)

    material = gltf2_io.Material(
        alpha_cutoff=__gather_alpha_cutoff(blender_material, export_settings),
        alpha_mode=__gather_alpha_mode(blender_material, export_settings),
        double_sided=__gather_double_sided(blender_material, export_settings),
        emissive_factor=__gather_emissive_factor(blender_material, export_settings),
        emissive_texture=__gather_emissive_texture(blender_material, export_settings),
        extensions=__gather_extensions(blender_material, export_settings),
        extras=__gather_extras(blender_material, export_settings),
        name=__gather_name(blender_material, export_settings),
        normal_texture=__gather_normal_texture(blender_material, export_settings),
        occlusion_texture=__gather_occlusion_texture(blender_material, orm_texture, export_settings),
        pbr_metallic_roughness=__gather_pbr_metallic_roughness(blender_material, orm_texture, export_settings)
    )

    export_user_extensions('gather_material_hook', export_settings, material, blender_material)

    return material
    # material = blender_primitive['material']
    #
    #     if get_material_requires_texcoords(glTF, material) and not export_settings['gltf_texcoords']:
    #         material = -1
    #
    #     if get_material_requires_normals(glTF, material) and not export_settings['gltf_normals']:
    #         material = -1
    #
    #     # Meshes/primitives without material are allowed.
    #     if material >= 0:
    #         primitive.material = material
    #     else:
    #         print_console('WARNING', 'Material ' + internal_primitive[
    #             'material'] + ' not found. Please assign glTF 2.0 material or enable Blinn-Phong material in export.')


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

    old_double_sided_socket = gltf2_blender_get.get_socket_old(blender_material, "DoubleSided")
    if old_double_sided_socket is not None and\
            not old_double_sided_socket.is_linked and\
            old_double_sided_socket.default_value > 0.5:
        return True
    return None


def __gather_emissive_factor(blender_material, export_settings):
    emissive_socket = gltf2_blender_get.get_socket(blender_material, "Emissive")
    if emissive_socket is None:
        emissive_socket = gltf2_blender_get.get_socket_old(blender_material, "EmissiveFactor")
    if isinstance(emissive_socket, bpy.types.NodeSocket):
        factor = gltf2_blender_get.get_factor_from_socket(emissive_socket, kind='RGB')

        if factor is None and emissive_socket.is_linked:
            # In glTF, the default emissiveFactor is all zeros, so if an emission texture is connected,
            # we have to manually set it to all ones.
            factor = [1.0, 1.0, 1.0]

        if factor is None: factor = [0.0, 0.0, 0.0]

        # Handle Emission Strength
        strength_socket = None
        if emissive_socket.node.type == 'EMISSION':
            strength_socket = emissive_socket.node.inputs['Strength']
        elif 'Emission Strength' in emissive_socket.node.inputs:
            strength_socket = emissive_socket.node.inputs['Emission Strength']
        strength = (
            gltf2_blender_get.get_const_from_socket(strength_socket, kind='VALUE')
            if strength_socket is not None
            else None
        )
        if strength is not None:
            factor = [f * strength for f in factor]

        # Clamp to range [0,1]
        factor = [min(1.0, f) for f in factor]

        if factor == [0, 0, 0]: factor = None

        return factor

    return None


def __gather_emissive_texture(blender_material, export_settings):
    emissive = gltf2_blender_get.get_socket(blender_material, "Emissive")
    if emissive is None:
        emissive = gltf2_blender_get.get_socket_old(blender_material, "Emissive")
    return gltf2_blender_gather_texture_info.gather_texture_info(emissive, (emissive,), export_settings)


def __gather_extensions(blender_material, export_settings):
    extensions = {}

    # KHR_materials_clearcoat

    clearcoat_extension = __gather_clearcoat_extension(blender_material, export_settings)
    if clearcoat_extension:
        extensions["KHR_materials_clearcoat"] = clearcoat_extension

    # KHR_materials_transmission

    transmission_extension = __gather_transmission_extension(blender_material, export_settings)
    if transmission_extension:
        extensions["KHR_materials_transmission"] = transmission_extension

    return extensions if extensions else None


def __gather_extras(blender_material, export_settings):
    if export_settings['gltf_extras']:
        return generate_extras(blender_material)
    return None


def __gather_name(blender_material, export_settings):
    return blender_material.name


def __gather_normal_texture(blender_material, export_settings):
    normal = gltf2_blender_get.get_socket(blender_material, "Normal")
    if normal is None:
        normal = gltf2_blender_get.get_socket_old(blender_material, "Normal")
    return gltf2_blender_gather_texture_info.gather_material_normal_texture_info_class(
        normal,
        (normal,),
        export_settings)


def __gather_orm_texture(blender_material, export_settings):
    # Check for the presence of Occlusion, Roughness, Metallic sharing a single image.
    # If not fully shared, return None, so the images will be cached and processed separately.

    occlusion = gltf2_blender_get.get_socket(blender_material, "Occlusion")
    if occlusion is None or not __has_image_node_from_socket(occlusion):
        occlusion = gltf2_blender_get.get_socket_old(blender_material, "Occlusion")
        if occlusion is None or not __has_image_node_from_socket(occlusion):
            return None

    metallic_socket = gltf2_blender_get.get_socket(blender_material, "Metallic")
    roughness_socket = gltf2_blender_get.get_socket(blender_material, "Roughness")

    hasMetal = metallic_socket is not None and __has_image_node_from_socket(metallic_socket)
    hasRough = roughness_socket is not None and __has_image_node_from_socket(roughness_socket)

    if not hasMetal and not hasRough:
        metallic_roughness = gltf2_blender_get.get_socket_old(blender_material, "MetallicRoughness")
        if metallic_roughness is None or not __has_image_node_from_socket(metallic_roughness):
            return None
        result = (occlusion, metallic_roughness)
    elif not hasMetal:
        result = (occlusion, roughness_socket)
    elif not hasRough:
        result = (occlusion, metallic_socket)
    else:
        result = (occlusion, roughness_socket, metallic_socket)

    if not gltf2_blender_gather_texture_info.check_same_size_images(result):
        print_console("INFO",
            "Occlusion and metal-roughness texture will be exported separately "
            "(use same-sized images if you want them combined)")
        return None

    # Double-check this will past the filter in texture_info
    info = gltf2_blender_gather_texture_info.gather_texture_info(result[0], result, export_settings)
    if info is None:
        return None

    return result

def __gather_occlusion_texture(blender_material, orm_texture, export_settings):
    occlusion = gltf2_blender_get.get_socket(blender_material, "Occlusion")
    if occlusion is None:
        occlusion = gltf2_blender_get.get_socket_old(blender_material, "Occlusion")
    return gltf2_blender_gather_texture_info.gather_material_occlusion_texture_info_class(
        occlusion,
        orm_texture or (occlusion,),
        export_settings)


def __gather_pbr_metallic_roughness(blender_material, orm_texture, export_settings):
    return gltf2_blender_gather_materials_pbr_metallic_roughness.gather_material_pbr_metallic_roughness(
        blender_material,
        orm_texture,
        export_settings)

def __has_image_node_from_socket(socket):
    result = gltf2_blender_search_node_tree.from_socket(
        socket,
        gltf2_blender_search_node_tree.FilterByType(bpy.types.ShaderNodeTexImage))
    if not result:
        return False
    return True

def __gather_clearcoat_extension(blender_material, export_settings):
    clearcoat_enabled = False
    has_clearcoat_texture = False
    has_clearcoat_roughness_texture = False

    clearcoat_extension = {}
    clearcoat_roughness_slots = ()

    clearcoat_socket = gltf2_blender_get.get_socket(blender_material, 'Clearcoat')
    clearcoat_roughness_socket = gltf2_blender_get.get_socket(blender_material, 'Clearcoat Roughness')
    clearcoat_normal_socket = gltf2_blender_get.get_socket(blender_material, 'Clearcoat Normal')

    if isinstance(clearcoat_socket, bpy.types.NodeSocket) and not clearcoat_socket.is_linked:
        clearcoat_extension['clearcoatFactor'] = clearcoat_socket.default_value
        clearcoat_enabled = clearcoat_extension['clearcoatFactor'] > 0
    elif __has_image_node_from_socket(clearcoat_socket):
        clearcoat_extension['clearcoatFactor'] = 1
        has_clearcoat_texture = True
        clearcoat_enabled = True

    if not clearcoat_enabled:
        return None

    if isinstance(clearcoat_roughness_socket, bpy.types.NodeSocket) and not clearcoat_roughness_socket.is_linked:
        clearcoat_extension['clearcoatRoughnessFactor'] = clearcoat_roughness_socket.default_value
    elif __has_image_node_from_socket(clearcoat_roughness_socket):
        clearcoat_extension['clearcoatRoughnessFactor'] = 1
        has_clearcoat_roughness_texture = True

    # Pack clearcoat (R) and clearcoatRoughness (G) channels.
    if has_clearcoat_texture and has_clearcoat_roughness_texture:
        clearcoat_roughness_slots = (clearcoat_socket, clearcoat_roughness_socket,)
    elif has_clearcoat_texture:
        clearcoat_roughness_slots = (clearcoat_socket,)
    elif has_clearcoat_roughness_texture:
        clearcoat_roughness_slots = (clearcoat_roughness_socket,)

    if len(clearcoat_roughness_slots) > 0:
        if has_clearcoat_texture:
            clearcoat_extension['clearcoatTexture'] = gltf2_blender_gather_texture_info.gather_texture_info(
                clearcoat_socket,
                clearcoat_roughness_slots,
                export_settings,
            )
        if has_clearcoat_roughness_texture:
            clearcoat_extension['clearcoatRoughnessTexture'] = gltf2_blender_gather_texture_info.gather_texture_info(
                clearcoat_roughness_socket,
                clearcoat_roughness_slots,
                export_settings,
            )

    if __has_image_node_from_socket(clearcoat_normal_socket):
        clearcoat_extension['clearcoatNormalTexture'] = gltf2_blender_gather_texture_info.gather_material_normal_texture_info_class(
            clearcoat_normal_socket,
            (clearcoat_normal_socket,),
            export_settings
        )

    return Extension('KHR_materials_clearcoat', clearcoat_extension, False)

def __gather_transmission_extension(blender_material, export_settings):
    transmission_enabled = False
    has_transmission_texture = False

    transmission_extension = {}
    transmission_slots = ()

    transmission_socket = gltf2_blender_get.get_socket(blender_material, 'Transmission')

    if isinstance(transmission_socket, bpy.types.NodeSocket) and not transmission_socket.is_linked:
        transmission_extension['transmissionFactor'] = transmission_socket.default_value
        transmission_enabled = transmission_extension['transmissionFactor'] > 0
    elif __has_image_node_from_socket(transmission_socket):
        transmission_extension['transmissionFactor'] = 1
        has_transmission_texture = True
        transmission_enabled = True

    if not transmission_enabled:
        return None

    # Pack transmission channel (R).
    if has_transmission_texture:
        transmission_slots = (transmission_socket,)

    if len(transmission_slots) > 0:
        combined_texture = gltf2_blender_gather_texture_info.gather_texture_info(
            transmission_socket,
            transmission_slots,
            export_settings,
        )
        if has_transmission_texture:
            transmission_extension['transmissionTexture'] = combined_texture

    return Extension('KHR_materials_transmission', transmission_extension, False)


def __gather_material_unlit(blender_material, export_settings):
    gltf2_unlit = gltf2_blender_gather_materials_unlit

    info = gltf2_unlit.detect_shadeless_material(blender_material, export_settings)
    if info is None:
        return None

    material = gltf2_io.Material(
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
            base_color_texture=gltf2_unlit.gather_base_color_texture(info, export_settings),
            metallic_factor=0.0,
            roughness_factor=0.9,
            metallic_roughness_texture=None,
            extensions=None,
            extras=None,
        )
    )

    export_user_extensions('gather_material_unlit_hook', export_settings, material, blender_material)

    return material
