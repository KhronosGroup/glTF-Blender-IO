import os
import shutil
import bpy
import zlib
import struct
from io_scene_gltf2.blender.exp import gltf2_blender_get

def create_image_file(context, blender_image, dst_path, file_format):
    """
    Creates JPEG or PNG file from a given Blender image.
    """

    # Check, if source image exists e.g. does not exist if image is packed.
    file_exists = 1
    try:
        src_path = bpy.path.abspath(blender_image.filepath, library=blender_image.library)
        file = open(src_path)
    except IOError:
        file_exists = 0
    else:
        file.close()

    if file_exists == 0:
        # Image does not exist on disk ...
        blender_image.filepath = dst_path
        # ... so save it.
        blender_image.save()

    elif file_format == blender_image.file_format:
        # Copy source image to destination, keeping original format.

        src_path = bpy.path.abspath(blender_image.filepath, library=blender_image.library)

        # Required for comapre.
        src_path = src_path.replace('\\', '/')
        dst_path = dst_path.replace('\\', '/')

        # Check that source and destination path are not the same using os.path.abspath
        # because bpy.path.abspath seems to not always return an absolute path
        if os.path.abspath(dst_path) != os.path.abspath(src_path):
            shutil.copyfile(src_path, dst_path)

    else:
        # Render a new image to destination, converting to target format.

        # TODO: Reusing the existing scene means settings like exposure are applied on export,
        # which we don't want, but I'm not sure how to create a new Scene object through the
        # Python API. See: https://github.com/KhronosGroup/glTF-Blender-Exporter/issues/184.

        context.scene.render.image_settings.file_format = file_format
        context.scene.render.image_settings.color_depth = '8'
        blender_image.save_render(dst_path, context.scene)


def create_image_data(context, export_settings, blender_image, file_format):
    """
    Creates JPEG or PNG byte array from a given Blender image.
    """
    if blender_image is None:
        return None

    if file_format == 'PNG':
        return _create_png_data(blender_image)
    else:
        return _create_jpg_data(context, export_settings, blender_image)


def _create_jpg_data(context, export_settings, blender_image):
    """
    Creates a JPEG byte array from a given Blender image.
    """

    uri = gltf2_blender_get.get_image_uri(export_settings, blender_image)
    path = export_settings['gltf_filedirectory'] + uri

    create_image_file(context, blender_image, path, 'JPEG')

    jpg_data = open(path, 'rb').read()
    os.remove(path)

    return jpg_data


def _create_png_data(blender_image):
    """
    Creates a PNG byte array from a given Blender image.
    """

    width = blender_image.size[0]
    height = blender_image.size[1]

    buf = bytearray([int(channel * 255.0) for channel in blender_image.pixels])

    #
    # Taken from 'blender-thumbnailer.py' in Blender.
    #

    # reverse the vertical line order and add null bytes at the start
    width_byte_4 = width * 4
    raw_data = b"".join(
        b'\x00' + buf[span:span + width_byte_4] for span in range((height - 1) * width * 4, -1, - width_byte_4))

    def png_pack(png_tag, data):
        chunk_head = png_tag + data
        return struct.pack("!I", len(data)) + chunk_head + struct.pack("!I", 0xFFFFFFFF & zlib.crc32(chunk_head))

    return b"".join([
        b'\x89PNG\r\n\x1a\n',
        png_pack(b'IHDR', struct.pack("!2I5B", width, height, 8, 6, 0, 0, 0)),
        png_pack(b'IDAT', zlib.compress(raw_data, 9)),
        png_pack(b'IEND', b'')])
