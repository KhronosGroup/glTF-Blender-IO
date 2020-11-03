# Copyright 2018-2019 The glTF-Blender-IO authors.
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
from io_scene_gltf2.blender.exp import gltf2_blender_gather_material_normal_texture_info_class
from io_scene_gltf2.blender.exp import gltf2_blender_gather_material_occlusion_texture_info_class
from io_scene_gltf2.blender.exp import gltf2_blender_search_node_tree

from io_scene_gltf2.blender.exp import gltf2_blender_gather_materials_pbr_metallic_roughness
from ..com.gltf2_blender_extras import generate_extras
from io_scene_gltf2.blender.exp import gltf2_blender_get
from io_scene_gltf2.io.exp.gltf2_io_user_extensions import export_user_extensions
from io_scene_gltf2.io.com.gltf2_io_debug import print_console


@cached
def gather_material(blender_material, mesh_double_sided, export_settings):
    """
    Gather the material used by the blender primitive.

    :param blender_material: the blender material used in the glTF primitive
    :param export_settings:
    :return: a glTF material
    """
    if not __filter_material(blender_material, export_settings):
        return None

    orm_texture = __gather_orm_texture(blender_material, export_settings)

    material = gltf2_io.Material(
        alpha_cutoff=__gather_alpha_cutoff(blender_material, export_settings),
        alpha_mode=__gather_alpha_mode(blender_material, export_settings),
        double_sided=__gather_double_sided(blender_material, mesh_double_sided, export_settings),
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
    elif blender_material.blend_method == 'BLEND':
        return 'BLEND'
    return None


def __gather_double_sided(blender_material, mesh_double_sided, export_settings):
    if mesh_double_sided:
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
        if emissive_socket.is_linked:
            # In glTF, the default emissiveFactor is all zeros, so if an emission texture is connected,
            # we have to manually set it to all ones.
            return [1.0, 1.0, 1.0]
        else:
            return list(emissive_socket.default_value)[0:3]
    return None


def __gather_emissive_texture(blender_material, export_settings):
    emissive = gltf2_blender_get.get_socket(blender_material, "Emissive")
    if emissive is None:
        emissive = gltf2_blender_get.get_socket_old(blender_material, "Emissive")
    return gltf2_blender_gather_texture_info.gather_texture_info((emissive,), export_settings)


def __gather_extensions(blender_material, export_settings):
    extensions = {}

    # KHR_materials_unlit

    if gltf2_blender_get.get_socket(blender_material, "Background") is not None:
        extensions["KHR_materials_unlit"] = Extension("KHR_materials_unlit", {}, False)

    # KHR_materials_clearcoat

    clearcoat_extension = __gather_clearcoat_extension(blender_material, export_settings)
    if clearcoat_extension:
        extensions["KHR_materials_clearcoat"] = clearcoat_extension

    # KHR_materials_specular and KHR_materials_ior
    ior_extension, specular_extension = __gather_ior_and_specular_extensions(blender_material, export_settings)
    if ior_extension:
        extensions["KHR_materials_ior"] = ior_extension
    if specular_extension:
        extensions["KHR_materials_specular"] = specular_extension

    # TODO KHR_materials_pbrSpecularGlossiness

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
    return gltf2_blender_gather_material_normal_texture_info_class.gather_material_normal_texture_info_class(
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
    info = gltf2_blender_gather_texture_info.gather_texture_info(result, export_settings)
    if info is None:
        return None

    return result

def __gather_occlusion_texture(blender_material, orm_texture, export_settings):
    if orm_texture is not None:
        return gltf2_blender_gather_material_occlusion_texture_info_class.gather_material_occlusion_texture_info_class(
            orm_texture,
            export_settings)
    occlusion = gltf2_blender_get.get_socket(blender_material, "Occlusion")
    if occlusion is None:
        occlusion = gltf2_blender_get.get_socket_old(blender_material, "Occlusion")
    return gltf2_blender_gather_material_occlusion_texture_info_class.gather_material_occlusion_texture_info_class(
        (occlusion,),
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
        combined_texture = gltf2_blender_gather_texture_info.gather_texture_info(clearcoat_roughness_slots, export_settings)
        if has_clearcoat_texture:
            clearcoat_extension['clearcoatTexture'] = combined_texture
        if has_clearcoat_roughness_texture:
            clearcoat_extension['clearcoatRoughnessTexture'] = combined_texture

    if __has_image_node_from_socket(clearcoat_normal_socket):
        clearcoat_extension['clearcoatNormalTexture'] = gltf2_blender_gather_material_normal_texture_info_class.gather_material_normal_texture_info_class(
            (clearcoat_normal_socket,),
            export_settings
        )

    return Extension('KHR_materials_clearcoat', clearcoat_extension, False)

def __gather_ior_and_specular_extensions(blender_material, export_settings):
    lerp = lambda a, b, v: (1-v)*a + v*b
    luminance = lambda c: 0.3 * c[0] + 0.6 * c[1] + 0.1 * c[2]

    specular_ext_enabled = False
    ior_ext_enabled = False

    specular_extension = {}
    ior_extension = {}

    specular_socket = gltf2_blender_get.get_socket(blender_material, 'Specular')
    specular_tint_socket = gltf2_blender_get.get_socket(blender_material, 'Specular Tint')
    base_color_socket = gltf2_blender_get.get_socket(blender_material, 'Base Color')
    transmission_socket = gltf2_blender_get.get_socket(blender_material, 'Transmission')
    ior_socket = gltf2_blender_get.get_socket(blender_material, 'IOR')

    specular_not_linked = isinstance(specular_socket, bpy.types.NodeSocket) and not specular_socket.is_linked
    specular_tint_not_linked = isinstance(specular_tint_socket, bpy.types.NodeSocket) and not specular_tint_socket.is_linked
    base_color_not_linked = isinstance(base_color_socket, bpy.types.NodeSocket) and not base_color_socket.is_linked
    transmission_not_linked = isinstance(transmission_socket, bpy.types.NodeSocket) and not transmission_socket.is_linked
    ior_not_linked = isinstance(ior_socket, bpy.types.NodeSocket) and not ior_socket.is_linked

    specular = specular_socket.default_value if specular_not_linked else None
    specular_tint = specular_tint_socket.default_value if specular_tint_not_linked else None
    transmission = transmission_socket.default_value if transmission_not_linked else None
    ior = ior_socket.default_value if ior_not_linked else 1.0   # textures not supported

    no_texture = (specular_not_linked and specular_tint_not_linked and
        (specular_tint == 0.0 or (specular_tint != 0.0 and base_color_not_linked)))

    has_transmission = (transmission_not_linked and transmission > 0) or not transmission_not_linked
    if has_transmission:
        ior_ext_enabled = True
        ior_extension['ior'] = ior
    else:
        # If there is no transmission/refraction, we are free to choose
        # any value for glTF's IOR. Therefore, if specular is overshooting,
        # we increase the IOR and adjust specular color accordingly in the
        # next step.
        if specular_not_linked and specular > 0.5:
            ior_ext_enabled = True
            ior_extension['ior'] = 1.788789

    if no_texture:
        if specular != 0.5 or specular_tint != 0.0:
            specular_ext_enabled = True
            base_color = base_color_socket.default_value[0:3] if base_color_not_linked else [0, 0, 0]
            normalized_base_color = [bc / luminance(base_color) if luminance(base_color) > 0 else 0 for bc in base_color]
            specular_color = [min(lerp(1, bc, specular_tint), 1) for bc in normalized_base_color]

            # The IOR dictates the maximal reflection strength, therefore we need to clamp
            # reflection strenth of non-transmissive (aka plastic) fraction (if any)
            plastic = [min(1/((ior - 1) / (ior + 1))**2 * 0.08 * specular * sc, 1) for sc in specular_color]
            glass = specular_color
            specular_extension['specularColorFactor'] = [lerp(plastic[c], glass[c], transmission) for c in range(0,3)]
    else:
        sockets = (specular_socket, specular_tint_socket, base_color_socket, transmission_socket, ior_socket)
        info = gltf2_blender_gather_texture_info.gather_texture_info(sockets, export_settings)
        if info is None:
            return None, None

        specular_ext_enabled = True
        specular_extension['specularColorTexture'] = info

    ior_extension = Extension('KHR_materials_ior', ior_extension, False) if ior_ext_enabled else None
    specular_extension = Extension('KHR_materials_specular', specular_extension, False) if specular_ext_enabled else None
        
    return ior_extension, specular_extension
