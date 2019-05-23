# Copyright 2018 The glTF-Blender-IO authors.
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
from os import path
import tempfile

from io_scene_gltf2.blender.exp.gltf2_blender_gather_cache import cached
from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.io.com import gltf2_io_constants
from io_scene_gltf2.io.com import gltf2_io_debug

from io_scene_gltf2.io.com.gltf2_io_extensions import Extension

from io_scene_gltf2.io.exp import gltf2_io_binary_data
from io_scene_gltf2.io.exp import gltf2_io_image_data

from io_scene_gltf2.blender.exp import gltf2_blender_gather_texture_info, gltf2_blender_export_keys
from io_scene_gltf2.blender.exp import gltf2_blender_gather_material_normal_texture_info_class
from io_scene_gltf2.blender.exp import gltf2_blender_gather_material_occlusion_texture_info_class
from io_scene_gltf2.blender.exp import gltf2_blender_search_node_tree

from io_scene_gltf2.blender.exp import gltf2_blender_gather_materials_pbr_metallic_roughness
from io_scene_gltf2.blender.exp import gltf2_blender_generate_extras
from io_scene_gltf2.blender.exp import gltf2_blender_get


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
    if bpy.app.version < (2, 80, 0):
        return None
    else:
        if blender_material.blend_method == 'CLIP':
            return blender_material.alpha_threshold
    return None


def __gather_alpha_mode(blender_material, export_settings):
    if bpy.app.version < (2, 80, 0):
        return None
    else:
        if blender_material.blend_method == 'CLIP':
            return 'MASK'
        elif blender_material.blend_method == 'BLEND':
            return 'BLEND'
    return None


def __gather_double_sided(blender_material, mesh_double_sided, export_settings):
    if mesh_double_sided:
        return True

    old_double_sided_socket = gltf2_blender_get.get_socket_or_texture_slot_old(blender_material, "DoubleSided")
    if old_double_sided_socket is not None and\
            not old_double_sided_socket.is_linked and\
            old_double_sided_socket.default_value > 0.5:
        return True
    return None


def __gather_emissive_factor(blender_material, export_settings):
    emissive_socket = gltf2_blender_get.get_socket_or_texture_slot(blender_material, "Emissive")
    if emissive_socket is None:
        emissive_socket = gltf2_blender_get.get_socket_or_texture_slot_old(blender_material, "EmissiveFactor")
    if isinstance(emissive_socket, bpy.types.NodeSocket):
        if emissive_socket.is_linked:
            # In glTF, the default emissiveFactor is all zeros, so if an emission texture is connected,
            # we have to manually set it to all ones.
            return [1.0, 1.0, 1.0]
        else:
            return list(emissive_socket.default_value)[0:3]
    return None


def __gather_emissive_texture(blender_material, export_settings):
    emissive = gltf2_blender_get.get_socket_or_texture_slot(blender_material, "Emissive")
    if emissive is None:
        emissive = gltf2_blender_get.get_socket_or_texture_slot_old(blender_material, "Emissive")
    return gltf2_blender_gather_texture_info.gather_texture_info((emissive,), export_settings)


def tmp_encode_movie(image: bpy.types.Image):
    """
    Reads the image bytes from disk back.
    """
    path=image.filepath_from_user()
    with open(path, "rb") as f:
        encoded_image = f.read()

    return encoded_image

def __gather_extensions(blender_material, export_settings):
    extensions = {}

    if bpy.app.version < (2, 80, 0):
        if blender_material.use_shadeless:
            extensions["KHR_materials_unlit"] = Extension("KHR_materials_unlit", {}, False)
    else:
        if gltf2_blender_get.get_socket_or_texture_slot(blender_material, "Background") is not None:
            extensions["KHR_materials_unlit"] = Extension("KHR_materials_unlit", {}, False)

    if blender_material.get("useVideoTextureExtension", False) == "True":
        image_name = blender_material.get("videoTextureExtension_ImageName")
        if image_name is not None:
            data = tmp_encode_movie(bpy.data.images[image_name])
            mime_type="video/mp4"
            image_base_name = path.splitext(image_name)[0]

            # Create an image, either in a buffer view or in a seperate file
            image = gltf2_io.Image(
                buffer_view=__gather_buffer_view(data, export_settings),
                extensions=None,
                extras=None,
                mime_type=mime_type,
                name=image_base_name,
                uri=__gather_uri(data, image_base_name, mime_type, export_settings)
            )

            extension = dict(image=image)
            extensions["SVRF_video_texture"] = Extension("SVRF_video_texture", extension, False)

    # TODO specular glossiness extension

    return extensions if extensions else None

@cached
def __gather_buffer_view(image_data: bytes, export_settings):
    if export_settings[gltf2_blender_export_keys.FORMAT] != 'GLTF_SEPARATE':
        return gltf2_io_binary_data.BinaryData(data=image_data)
    return None

@cached
def __gather_uri(image_data: bytes, image_name: str, mime_type: str, export_settings):
    if export_settings[gltf2_blender_export_keys.FORMAT] == 'GLTF_SEPARATE':
        return gltf2_io_image_data.ImageData(
            data=image_data,
            mime_type=mime_type,
            name=image_name,
        )
    return None

def __gather_extras(blender_material, export_settings):
    if export_settings['gltf_extras']:
        return gltf2_blender_generate_extras.generate_extras(blender_material)
    return None


def __gather_name(blender_material, export_settings):
    return blender_material.name


def __gather_normal_texture(blender_material, export_settings):
    normal = gltf2_blender_get.get_socket_or_texture_slot(blender_material, "Normal")
    if normal is None:
        normal = gltf2_blender_get.get_socket_or_texture_slot_old(blender_material, "Normal")
    return gltf2_blender_gather_material_normal_texture_info_class.gather_material_normal_texture_info_class(
        (normal,),
        export_settings)


def __gather_orm_texture(blender_material, export_settings):
    # Check for the presence of Occlusion, Roughness, Metallic sharing a single image.
    # If not fully shared, return None, so the images will be cached and processed separately.

    occlusion = gltf2_blender_get.get_socket_or_texture_slot(blender_material, "Occlusion")
    if occlusion is None or not __has_image_node_from_socket(occlusion):
        occlusion = gltf2_blender_get.get_socket_or_texture_slot_old(blender_material, "Occlusion")
        if occlusion is None or not __has_image_node_from_socket(occlusion):
            return None

    metallic_socket = gltf2_blender_get.get_socket_or_texture_slot(blender_material, "Metallic")
    roughness_socket = gltf2_blender_get.get_socket_or_texture_slot(blender_material, "Roughness")

    hasMetal = metallic_socket is not None and __has_image_node_from_socket(metallic_socket)
    hasRough = roughness_socket is not None and __has_image_node_from_socket(roughness_socket)

    if not hasMetal and not hasRough:
        metallic_roughness = gltf2_blender_get.get_socket_or_texture_slot_old(blender_material, "MetallicRoughness")
        if metallic_roughness is None or not __has_image_node_from_socket(metallic_roughness):
            return None
        result = (occlusion, metallic_roughness)
    elif not hasMetal:
        result = (occlusion, roughness_socket)
    elif not hasRough:
        result = (occlusion, metallic_socket)
    else:
        result = (occlusion, roughness_socket, metallic_socket)

    # Double-check this will past the filter in texture_info (otherwise there are different resolutions or other problems).
    info = gltf2_blender_gather_texture_info.gather_texture_info(result, export_settings)
    if info is None:
        return None

    return result

def __gather_occlusion_texture(blender_material, orm_texture, export_settings):
    if orm_texture is not None:
        return gltf2_blender_gather_material_occlusion_texture_info_class.gather_material_occlusion_texture_info_class(
            orm_texture,
            export_settings)
    occlusion = gltf2_blender_get.get_socket_or_texture_slot(blender_material, "Occlusion")
    if occlusion is None:
        occlusion = gltf2_blender_get.get_socket_or_texture_slot_old(blender_material, "Occlusion")
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
