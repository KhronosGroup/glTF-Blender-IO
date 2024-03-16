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

bl_info = {
    'name': 'glTF 2.0 format',
    'author': 'Julien Duroure, Scurest, Norbert Nopper, Urs Hanselmann, Moritz Becher, Benjamin Schmithüsen, Jim Eckerlein, and many external contributors',
    "version": (4, 1, 62),
    'blender': (4, 1, 0),
    'location': 'File > Import-Export',
    'description': 'Import-Export as glTF 2.0',
    'warning': '',
    'doc_url': "{BLENDER_MANUAL_URL}/addons/import_export/scene_gltf2.html",
    'tracker_url': "https://github.com/KhronosGroup/glTF-Blender-IO/issues/",
    'support': 'OFFICIAL',
    'category': 'Import-Export',
}

def get_version_string():
    return str(bl_info['version'][0]) + '.' + str(bl_info['version'][1]) + '.' + str(bl_info['version'][2])

#
# Script reloading (if the user calls 'Reload Scripts' from Blender)
#

def reload_package(module_dict_main):
    import importlib
    from pathlib import Path

    def reload_package_recursive(current_dir, module_dict):
        for path in current_dir.iterdir():
            if "__init__" in str(path) or path.stem not in module_dict:
                continue

            if path.is_file() and path.suffix == ".py":
                importlib.reload(module_dict[path.stem])
            elif path.is_dir():
                reload_package_recursive(path, module_dict[path.stem].__dict__)

    reload_package_recursive(Path(__file__).parent, module_dict_main)


if "bpy" in locals():
    reload_package(locals())

import bpy
from bpy.props import (StringProperty,
                       BoolProperty,
                       EnumProperty,
                       IntProperty,
                       FloatProperty,
                       CollectionProperty)
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper, ExportHelper


#
#  Functions / Classes.
#

exporter_extension_panel_unregister_functors = []
importer_extension_panel_unregister_functors = []


def ensure_filepath_matches_export_format(filepath, export_format):
    import os
    filename = os.path.basename(filepath)
    if not filename:
        return filepath

    stem, ext = os.path.splitext(filename)
    if stem.startswith('.') and not ext:
        stem, ext = '', stem

    desired_ext = '.glb' if export_format == 'GLB' else '.gltf'
    ext_lower = ext.lower()
    if ext_lower not in ['.glb', '.gltf']:
        return filepath + desired_ext
    elif ext_lower != desired_ext:
        filepath = filepath[:-len(ext)]  # strip off ext
        return filepath + desired_ext
    else:
        return filepath


def on_export_format_changed(self, context):
    # Update the filename in the file browser when the format (.glb/.gltf)
    # changes
    sfile = context.space_data
    if not isinstance(sfile, bpy.types.SpaceFileBrowser):
        return
    if not sfile.active_operator:
        return
    if sfile.active_operator.bl_idname != "EXPORT_SCENE_OT_gltf":
        return

    sfile.params.filename = ensure_filepath_matches_export_format(
        sfile.params.filename,
        self.export_format,
    )

    # Also change the filter
    sfile.params.filter_glob = '*.glb' if self.export_format == 'GLB' else '*.gltf'
    # Force update of file list, because update the filter does not update the real file list
    bpy.ops.file.refresh()

def on_export_action_filter_changed(self, context):
    if self.export_action_filter is True:
        bpy.types.Scene.gltf_action_filter = bpy.props.CollectionProperty(type=GLTF2_filter_action)
        bpy.types.Scene.gltf_action_filter_active = bpy.props.IntProperty()

        for action in bpy.data.actions:
            if id(action) not in [id(item.action) for item in bpy.data.scenes[0].gltf_action_filter]:
                item = bpy.data.scenes[0].gltf_action_filter.add()
                item.keep = True
                item.action = action

    else:
        bpy.data.scenes[0].gltf_action_filter.clear()
        del bpy.types.Scene.gltf_action_filter
        del bpy.types.Scene.gltf_action_filter_active


def get_format_items(scene, context):


    items = (('GLB', 'glTF Binary (.glb)',
                'Exports a single file, with all data packed in binary form. '
                'Most efficient and portable, but more difficult to edit later'),
               ('GLTF_SEPARATE', 'glTF Separate (.gltf + .bin + textures)',
                'Exports multiple files, with separate JSON, binary and texture data. '
                'Easiest to edit later'))

    if bpy.context.preferences.addons['io_scene_gltf2'].preferences \
            and "allow_embedded_format" in bpy.context.preferences.addons['io_scene_gltf2'].preferences \
            and bpy.context.preferences.addons['io_scene_gltf2'].preferences['allow_embedded_format']:
            # At initialization, the preferences are not yet loaded
            # The second line check is needed until the PR is merge in Blender, for github CI tests
        items += (('GLTF_EMBEDDED', 'glTF Embedded (.gltf)',
                    'Exports a single file, with all data packed in JSON. '
                    'Less efficient than binary, but easier to edit later'
                ),)

    return items


class ConvertGLTF2_Base:
    """Base class containing options that should be exposed during both import and export."""

    export_import_convert_lighting_mode: EnumProperty(
        name='Lighting Mode',
        items=(
            ('SPEC', 'Standard', 'Physically-based glTF lighting units (cd, lx, nt)'),
            ('COMPAT', 'Unitless', 'Non-physical, unitless lighting. Useful when exposure controls are not available'),
            ('RAW', 'Raw (Deprecated)', 'Blender lighting strengths with no conversion'),
        ),
        description='Optional backwards compatibility for non-standard render engines. Applies to lights',# TODO: and emissive materials',
        default='SPEC'
    )

class ExportGLTF2_Base(ConvertGLTF2_Base):
    # TODO: refactor to avoid boilerplate

    def __init__(self):
        from .io.com import gltf2_io_draco_compression_extension
        self.is_draco_available = gltf2_io_draco_compression_extension.dll_exists()

    bl_options = {'PRESET'}

    # Don't use export_ prefix here, I don't want it to be saved with other export settings
    gltf_export_id: StringProperty(
        name='Identifier',
        description=(
            'Identifier of caller (in case of add-on calling this exporter). '
            'Can be useful in case of Extension added by other add-ons'
        ),
        default=''
    )

    # gltfpack properties
    export_use_gltfpack: BoolProperty(
        name='Use Gltfpack',
        description='Use gltfpack to simplify the mesh and/or compress its textures',
        default=False,
    )

    export_gltfpack_tc: BoolProperty(
        name='KTX2 Compression',
        description='Convert all textures to KTX2 with BasisU supercompression',
        default=True,
    )

    export_gltfpack_tq: IntProperty(
        name='Texture Encoding Quality',
        description='Texture encoding quality',
        default=8,
        min=1,
        max=10,
    )

    export_gltfpack_si: FloatProperty(
        name='Mesh Simplification Ratio',
        description='Simplify meshes targeting triangle count ratio',
        default=1.0,
        min=0.0,
        max=1.0,
    )

    export_gltfpack_sa: BoolProperty(
        name='Aggressive Mesh Simplification',
        description='Aggressively simplify to the target ratio disregarding quality',
        default=False,
    )

    export_gltfpack_slb: BoolProperty(
        name='Lock Mesh Border Vertices',
        description='Lock border vertices during simplification to avoid gaps on connected meshes',
        default=False,
    )

    export_gltfpack_vp: IntProperty(
        name='Position Quantization',
        description='Use N-bit quantization for positions',
        default=14,
        min=1,
        max=16,
    )

    export_gltfpack_vt: IntProperty(
        name='Texture Coordinate Quantization',
        description='Use N-bit quantization for texture coordinates',
        default=12,
        min=1,
        max=16,
    )

    export_gltfpack_vn: IntProperty(
        name='Normal/Tangent Quantization',
        description='Use N-bit quantization for normals and tangents',
        default=8,
        min=1,
        max=16,
    )

    export_gltfpack_vc: IntProperty(
        name='Vertex Color Quantization',
        description='Use N-bit quantization for colors',
        default=8,
        min=1,
        max=16,
    )

    export_gltfpack_vpi: EnumProperty(
        name='Vertex Position Attributes',
        description='Type to use for vertex position attributes',
        items=(('Integer', 'Integer', 'Use integer attributes for positions'),
                ('Normalized', 'Normalized', 'Use normalized attributes for positions'),
                ('Floating-point', 'Floating-point', 'Use floating-point attributes for positions')),
        default='Integer',
    )

    export_gltfpack_noq: BoolProperty(
        name='Disable Quantization',
        description='Disable quantization; produces much larger glTF files with no extensions',
        default=True,
    )

    # TODO: some stuff in Textures

    # TODO: Animations

    # TODO: Scene

    # TODO: some stuff in Miscellaneous

    export_format: EnumProperty(
        name='Format',
        items=get_format_items,
        description=(
            'Output format. Binary is most efficient, '
            'but JSON may be easier to edit later'
        ),
        default=0, #Warning => If you change the default, need to change the default filter too
        update=on_export_format_changed,
    )

    ui_tab: EnumProperty(
        items=(('GENERAL', "General", "General settings"),
               ('MESHES', "Meshes", "Mesh settings"),
               ('OBJECTS', "Objects", "Object settings"),
               ('ANIMATION', "Animation", "Animation settings")),
        name="ui_tab",
        description="Export setting categories",
    )

    export_copyright: StringProperty(
        name='Copyright',
        description='Legal rights and conditions for the model',
        default=''
    )

    export_image_format: EnumProperty(
        name='Images',
        items=(('AUTO', 'Automatic',
                'Save PNGs as PNGs, JPEGs as JPEGs, WebPs as WebPs. '
                'For other formats, use PNG'),
                ('JPEG', 'JPEG Format (.jpg)',
                'Save images as JPEGs. (Images that need alpha are saved as PNGs though.) '
                'Be aware of a possible loss in quality'),
                ('WEBP', 'WebP Format',
                'Save images as WebPs as main image (no fallback)'),
                ('NONE', 'None',
                 'Don\'t export images'),
               ),
        description=(
            'Output format for images. PNG is lossless and generally preferred, but JPEG might be preferable for web '
            'applications due to the smaller file size. Alternatively they can be omitted if they are not needed'
        ),
        default='AUTO'
    )

    export_image_add_webp: BoolProperty(
        name='Create WebP',
        description=(
            "Creates WebP textures for every texture. "
            "For already WebP textures, nothing happens"
        ),
        default=False
    )

    export_image_webp_fallback: BoolProperty(
        name='WebP fallback',
        description=(
            "For all WebP textures, create a PNG fallback texture"
        ),
        default=False
    )

    export_texture_dir: StringProperty(
        name='Textures',
        description='Folder to place texture files in. Relative to the .gltf file',
        default='',
    )

    # Keep for back compatibility
    export_jpeg_quality: IntProperty(
        name='JPEG quality',
        description='Quality of JPEG export',
        default=75,
        min=0,
        max=100
    )

    # Keep for back compatibility
    export_image_quality: IntProperty(
        name='Image quality',
        description='Quality of image export',
        default=75,
        min=0,
        max=100
    )

    export_keep_originals: BoolProperty(
        name='Keep original',
        description=('Keep original textures files if possible. '
                     'WARNING: if you use more than one texture, '
                     'where pbr standard requires only one, only one texture will be used. '
                     'This can lead to unexpected results'
        ),
        default=False,
    )

    export_texcoords: BoolProperty(
        name='UVs',
        description='Export UVs (texture coordinates) with meshes',
        default=True
    )

    export_normals: BoolProperty(
        name='Normals',
        description='Export vertex normals with meshes',
        default=True
    )

    export_gn_mesh: BoolProperty(
        name='Geometry Nodes Instances (Experimental)',
        description='Export Geometry nodes instance meshes',
        default=False
    )

    export_draco_mesh_compression_enable: BoolProperty(
        name='Draco mesh compression',
        description='Compress mesh using Draco',
        default=False
    )

    export_draco_mesh_compression_level: IntProperty(
        name='Compression level',
        description='Compression level (0 = most speed, 6 = most compression, higher values currently not supported)',
        default=6,
        min=0,
        max=10
    )

    export_draco_position_quantization: IntProperty(
        name='Position quantization bits',
        description='Quantization bits for position values (0 = no quantization)',
        default=14,
        min=0,
        max=30
    )

    export_draco_normal_quantization: IntProperty(
        name='Normal quantization bits',
        description='Quantization bits for normal values (0 = no quantization)',
        default=10,
        min=0,
        max=30
    )

    export_draco_texcoord_quantization: IntProperty(
        name='Texcoord quantization bits',
        description='Quantization bits for texture coordinate values (0 = no quantization)',
        default=12,
        min=0,
        max=30
    )

    export_draco_color_quantization: IntProperty(
        name='Color quantization bits',
        description='Quantization bits for color values (0 = no quantization)',
        default=10,
        min=0,
        max=30
    )

    export_draco_generic_quantization: IntProperty(
        name='Generic quantization bits',
        description='Quantization bits for generic values like weights or joints (0 = no quantization)',
        default=12,
        min=0,
        max=30
    )

    export_tangents: BoolProperty(
        name='Tangents',
        description='Export vertex tangents with meshes',
        default=False
    )

    export_materials: EnumProperty(
        name='Materials',
        items=(('EXPORT', 'Export',
        'Export all materials used by included objects'),
        ('PLACEHOLDER', 'Placeholder',
        'Do not export materials, but write multiple primitive groups per mesh, keeping material slot information'),
        ('NONE', 'No export',
        'Do not export materials, and combine mesh primitive groups, losing material slot information')),
        description='Export materials',
        default='EXPORT'
    )

    export_unused_images: BoolProperty(
        name='Unused images',
        description='Export images not assigned to any material',
        default=False)

    export_unused_textures: BoolProperty(
        name='Prepare Unused textures',
        description=(
            'Export image texture nodes not assigned to any material. '
            'This feature is not standard and needs an external extension to be included in the glTF file'
        ),
        default=False)

    export_colors: BoolProperty(
        name='Dummy',
        description='Keep for compatibility only',
        default=True
    )

    export_attributes: BoolProperty(
        name='Attributes',
        description='Export Attributes (when starting with underscore)',
        default=False
    )

    use_mesh_edges: BoolProperty(
        name='Loose Edges',
        description=(
            'Export loose edges as lines, using the material from the first material slot'
        ),
        default=False,
    )

    use_mesh_vertices: BoolProperty(
        name='Loose Points',
        description=(
            'Export loose points as glTF points, using the material from the first material slot'
        ),
        default=False,
    )

    export_cameras: BoolProperty(
        name='Cameras',
        description='Export cameras',
        default=False
    )

    use_selection: BoolProperty(
        name='Selected Objects',
        description='Export selected objects only',
        default=False
    )

    use_visible: BoolProperty(
        name='Visible Objects',
        description='Export visible objects only',
        default=False
    )

    use_renderable: BoolProperty(
        name='Renderable Objects',
        description='Export renderable objects only',
        default=False
    )

    use_active_collection_with_nested: BoolProperty(
        name='Include Nested Collections',
        description='Include active collection and nested collections',
        default=True
    )

    use_active_collection: BoolProperty(
        name='Active Collection',
        description='Export objects in the active collection only',
        default=False
    )

    use_active_scene: BoolProperty(
        name='Active Scene',
        description='Export active scene only',
        default=False
    )

    export_extras: BoolProperty(
        name='Custom Properties',
        description='Export custom properties as glTF extras',
        default=False
    )

    export_yup: BoolProperty(
        name='+Y Up',
        description='Export using glTF convention, +Y up',
        default=True
    )

    export_apply: BoolProperty(
        name='Apply Modifiers',
        description='Apply modifiers (excluding Armatures) to mesh objects -'
                    'WARNING: prevents exporting shape keys',
        default=False
    )

    export_shared_accessors: BoolProperty(
        name='Shared Accessors',
        description='Export Primitives using shared accessors for attributes',
        default=False
    )

    export_animations: BoolProperty(
        name='Animations',
        description='Exports active actions and NLA tracks as glTF animations',
        default=True
    )

    export_frame_range: BoolProperty(
        name='Limit to Playback Range',
        description='Clips animations to selected playback range',
        default=False
    )

    export_frame_step: IntProperty(
        name='Sampling Rate',
        description='How often to evaluate animated values (in frames)',
        default=1,
        min=1,
        max=120
    )

    export_force_sampling: BoolProperty(
        name='Always Sample Animations',
        description='Apply sampling to all animations',
        default=True
    )

    export_animation_mode: EnumProperty(
        name='Animation mode',
        items=(('ACTIONS', 'Actions',
        'Export actions (actives and on NLA tracks) as separate animations'),
        ('ACTIVE_ACTIONS', 'Active actions merged',
        'All the currently assigned actions become one glTF animation'),
        ('NLA_TRACKS', 'NLA Tracks',
        'Export individual NLA Tracks as separate animation'),
        ('SCENE', 'Scene',
        'Export baked scene as a single animation')
        ),
        description='Export Animation mode',
        default='ACTIONS'
    )

    export_nla_strips_merged_animation_name: StringProperty(
        name='Merged Animation Name',
        description=(
            "Name of single glTF animation to be exported"
        ),
        default='Animation'
    )

    export_def_bones: BoolProperty(
        name='Export Deformation Bones Only',
        description='Export Deformation bones only',
        default=False
    )

    export_hierarchy_flatten_bones: BoolProperty(
        name='Flatten Bone Hierarchy',
        description='Flatten Bone Hierarchy. Useful in case of non decomposable transformation matrix',
        default=False
    )

    export_hierarchy_flatten_objs: BoolProperty(
        name='Flatten Object Hierarchy',
        description='Flatten Object Hierarchy. Useful in case of non decomposable transformation matrix',
        default=False
    )

    export_armature_object_remove: BoolProperty(
        name='Remove Armature Object',
        description=(
            'Remove Armature object if possible. '
            'If Armature has multiple root bones, object will not be removed'
            ),
        default=False
    )

    export_optimize_animation_size: BoolProperty(
        name='Optimize Animation Size',
        description=(
            "Reduce exported file size by removing duplicate keyframes"
        ),
        default=True
    )

    export_optimize_animation_keep_anim_armature: BoolProperty(
        name='Force keeping channels for bones',
        description=(
            "If all keyframes are identical in a rig, "
            "force keeping the minimal animation. "
            "When off, all possible channels for "
            "the bones will be exported, even if empty "
            "(minimal animation, 2 keyframes)"
        ),
        default=True
    )

    export_optimize_animation_keep_anim_object: BoolProperty(
        name='Force keeping channel for objects',
        description=(
            "If all keyframes are identical for object transformations, "
            "force keeping the minimal animation"
        ),
        default=False
    )

    export_negative_frame: EnumProperty(
        name='Negative Frames',
        items=(('SLIDE', 'Slide',
        'Slide animation to start at frame 0'),
        ('CROP', 'Crop',
        'Keep only frames above frame 0'),
        ),
        description='Negative Frames are slid or cropped',
        default='SLIDE'
    )

    export_anim_slide_to_zero: BoolProperty(
        name='Set all glTF Animation starting at 0',
        description=(
            "Set all glTF animation starting at 0.0s. "
            "Can be useful for looping animations"
        ),
        default=False
    )

    export_bake_animation: BoolProperty(
        name='Bake All Objects Animations',
        description=(
            "Force exporting animation on every object. "
            "Can be useful when using constraints or driver. "
            "Also useful when exporting only selection"
        ),
        default=False
    )

    export_anim_single_armature: BoolProperty(
        name='Export all Armature Actions',
        description=(
            "Export all actions, bound to a single armature. "
            "WARNING: Option does not support exports including multiple armatures"
        ),
        default=True
    )

    export_reset_pose_bones: BoolProperty(
        name='Reset pose bones between actions',
        description=(
            "Reset pose bones between each action exported. "
            "This is needed when some bones are not keyed on some animations"
        ),
        default=True
    )

    export_current_frame: BoolProperty(
        name='Use Current Frame as Object Rest Transformations',
        description=(
            'Export the scene in the current animation frame. '
            'When off, frame 0 is used as rest transformations for objects'
        ),
        default=False
    )

    export_rest_position_armature: BoolProperty(
        name='Use Rest Position Armature',
        description=(
            "Export armatures using rest position as joints' rest pose. "
            "When off, current frame pose is used as rest pose"
        ),
        default=True
    )

    export_anim_scene_split_object: BoolProperty(
        name='Split Animation by Object',
        description=(
            "Export Scene as seen in Viewport, "
            "But split animation by Object"
        ),
        default=True
    )

    export_skins: BoolProperty(
        name='Skinning',
        description='Export skinning (armature) data',
        default=True
    )

    export_influence_nb: IntProperty(
        name='Bone Influences',
        description='Choose how many Bone influences to export',
        default=4,
        min=1
    )

    export_all_influences: BoolProperty(
        name='Include All Bone Influences',
        description='Allow export of all joint vertex influences. Models may appear incorrectly in many viewers',
        default=False
    )

    export_morph: BoolProperty(
        name='Shape Keys',
        description='Export shape keys (morph targets)',
        default=True
    )

    export_morph_normal: BoolProperty(
        name='Shape Key Normals',
        description='Export vertex normals with shape keys (morph targets)',
        default=True
    )

    export_morph_tangent: BoolProperty(
        name='Shape Key Tangents',
        description='Export vertex tangents with shape keys (morph targets)',
        default=False
    )

    export_morph_animation: BoolProperty(
        name='Shape Key Animations',
        description='Export shape keys animations (morph targets)',
        default=True
    )

    export_morph_reset_sk_data: BoolProperty(
        name='Reset shape keys between actions',
        description=(
            "Reset shape keys between each action exported. "
            "This is needed when some SK channels are not keyed on some animations"
        ),
        default=True
    )

    export_lights: BoolProperty(
        name='Punctual Lights',
        description='Export directional, point, and spot lights. '
                    'Uses "KHR_lights_punctual" glTF extension',
        default=False
    )

    export_try_sparse_sk: BoolProperty(
        name='Use Sparse Accessor if better',
        description='Try using Sparse Accessor if it saves space',
        default=True
    )

    export_try_omit_sparse_sk: BoolProperty(
        name='Omitting Sparse Accessor if data is empty',
        description='Omitting Sparse Accessor if data is empty',
        default=False
    )

    export_gpu_instances: BoolProperty(
        name='GPU Instances',
        description='Export using EXT_mesh_gpu_instancing. '
                    'Limited to children of a given Empty. '
                    'Multiple materials might be omitted',
        default=False
    )

    export_action_filter: BoolProperty(
        name='Filter Actions',
        description='Filter Actions to be exported',
        default=False,
        update=on_export_action_filter_changed,
    )

    # This parameter is only here for backward compatibility, as this option is removed in 3.6
    # This option does nothing, and is not displayed in UI
    # What you are looking for is probably "export_animation_mode"
    export_nla_strips: BoolProperty(
        name='Group by NLA Track',
        description=(
            "When on, multiple actions become part of the same glTF animation if "
            "they're pushed onto NLA tracks with the same name. "
            "When off, all the currently assigned actions become one glTF animation"
        ),
        default=True
    )

    # Keep for back compatibility, but no more used
    export_original_specular: BoolProperty(
        name='Export original PBR Specular',
        description=(
            'Export original glTF PBR Specular, instead of Blender Principled Shader Specular'
        ),
        default=False,
    )

    will_save_settings: BoolProperty(
        name='Remember Export Settings',
        description='Store glTF export settings in the Blender project',
        default=False)

    export_hierarchy_full_collections: BoolProperty(
        name='Full Collection Hierarchy',
        description='Export full hierarchy, including intermediate collections',
        default=False
    )

    # Custom scene property for saving settings
    scene_key = "glTF2ExportSettings"

    #

    def check(self, _context):
        # Ensure file extension matches format
        old_filepath = self.filepath
        self.filepath = ensure_filepath_matches_export_format(
            self.filepath,
            self.export_format,
        )
        return self.filepath != old_filepath

    def invoke(self, context, event):
        settings = context.scene.get(self.scene_key)
        self.will_save_settings = False
        if settings:
            try:
                for (k, v) in settings.items():
                    setattr(self, k, v)
                self.will_save_settings = True

                # Update filter if user saved settings
                if hasattr(self, 'export_format'):
                    self.filter_glob = '*.glb' if self.export_format == 'GLB' else '*.gltf'

            except (AttributeError, TypeError):
                self.report({"ERROR"}, "Loading export settings failed. Removed corrupted settings")
                del context.scene[self.scene_key]

        import sys
        preferences = bpy.context.preferences
        for addon_name in preferences.addons.keys():
            try:
                if hasattr(sys.modules[addon_name], 'glTF2ExportUserExtension') or hasattr(sys.modules[addon_name], 'glTF2ExportUserExtensions'):
                    exporter_extension_panel_unregister_functors.append(sys.modules[addon_name].register_panel())
            except Exception:
                pass

        self.has_active_exporter_extensions = len(exporter_extension_panel_unregister_functors) > 0
        return ExportHelper.invoke(self, context, event)

    def save_settings(self, context):
        # find all props to save
        exceptional = [
            # options that don't start with 'export_'
            'use_selection',
            'use_visible',
            'use_renderable',
            'use_active_collection_with_nested',
            'use_active_collection',
            'use_mesh_edges',
            'use_mesh_vertices',
            'use_active_scene',
        ]
        all_props = self.properties
        export_props = {
            x: getattr(self, x) for x in dir(all_props)
            if (x.startswith("export_") or x in exceptional) and all_props.get(x) is not None
        }
        context.scene[self.scene_key] = export_props

    def execute(self, context):
        import os
        import datetime
        from .blender.exp import gltf2_blender_export
        from .io.com.gltf2_io_path import path_to_uri

        if self.will_save_settings:
            self.save_settings(context)

        self.check(context)  # ensure filepath has the right extension

        # All custom export settings are stored in this container.
        export_settings = {}

        export_settings['exported_images'] = {}
        export_settings['exported_texture_nodes'] = []
        export_settings['additional_texture_export'] = []
        export_settings['additional_texture_export_current_idx'] = 0

        export_settings['timestamp'] = datetime.datetime.now()
        export_settings['gltf_export_id'] = self.gltf_export_id
        export_settings['gltf_filepath'] = self.filepath
        export_settings['gltf_filedirectory'] = os.path.dirname(export_settings['gltf_filepath']) + '/'
        export_settings['gltf_texturedirectory'] = os.path.join(
            export_settings['gltf_filedirectory'],
            self.export_texture_dir,
        )
        export_settings['gltf_keep_original_textures'] = self.export_keep_originals

        export_settings['gltf_format'] = self.export_format
        export_settings['gltf_image_format'] = self.export_image_format
        export_settings['gltf_add_webp'] = self.export_image_add_webp
        export_settings['gltf_webp_fallback'] = self.export_image_webp_fallback
        export_settings['gltf_image_quality'] = self.export_image_quality
        export_settings['gltf_copyright'] = self.export_copyright
        export_settings['gltf_texcoords'] = self.export_texcoords
        export_settings['gltf_normals'] = self.export_normals
        export_settings['gltf_tangents'] = self.export_tangents and self.export_normals
        export_settings['gltf_loose_edges'] = self.use_mesh_edges
        export_settings['gltf_loose_points'] = self.use_mesh_vertices

        if self.is_draco_available:
            export_settings['gltf_draco_mesh_compression'] = self.export_draco_mesh_compression_enable
            export_settings['gltf_draco_mesh_compression_level'] = self.export_draco_mesh_compression_level
            export_settings['gltf_draco_position_quantization'] = self.export_draco_position_quantization
            export_settings['gltf_draco_normal_quantization'] = self.export_draco_normal_quantization
            export_settings['gltf_draco_texcoord_quantization'] = self.export_draco_texcoord_quantization
            export_settings['gltf_draco_color_quantization'] = self.export_draco_color_quantization
            export_settings['gltf_draco_generic_quantization'] = self.export_draco_generic_quantization
        else:
            export_settings['gltf_draco_mesh_compression'] = False

        export_settings['gltf_gn_mesh'] = self.export_gn_mesh

        export_settings['gltf_materials'] = self.export_materials
        export_settings['gltf_attributes'] = self.export_attributes
        export_settings['gltf_cameras'] = self.export_cameras

        export_settings['gltf_unused_textures'] = self.export_unused_textures
        export_settings['gltf_unused_images'] = self.export_unused_images

        export_settings['gltf_visible'] = self.use_visible
        export_settings['gltf_renderable'] = self.use_renderable

        export_settings['gltf_active_collection'] = self.use_active_collection
        if self.use_active_collection:
            export_settings['gltf_active_collection_with_nested'] = self.use_active_collection_with_nested
        else:
            export_settings['gltf_active_collection_with_nested'] = False
        export_settings['gltf_active_scene'] = self.use_active_scene

        export_settings['gltf_selected'] = self.use_selection
        export_settings['gltf_layers'] = True  # self.export_layers
        export_settings['gltf_extras'] = self.export_extras
        export_settings['gltf_yup'] = self.export_yup
        export_settings['gltf_apply'] = self.export_apply
        export_settings['gltf_shared_accessors'] = self.export_shared_accessors
        export_settings['gltf_current_frame'] = self.export_current_frame
        export_settings['gltf_animations'] = self.export_animations
        export_settings['gltf_def_bones'] = self.export_def_bones
        export_settings['gltf_flatten_bones_hierarchy'] = self.export_hierarchy_flatten_bones
        export_settings['gltf_flatten_obj_hierarchy'] = self.export_hierarchy_flatten_objs
        export_settings['gltf_armature_object_remove'] = self.export_armature_object_remove
        if self.export_animations:
            export_settings['gltf_frame_range'] = self.export_frame_range
            export_settings['gltf_force_sampling'] = self.export_force_sampling
            if not self.export_force_sampling:
                export_settings['gltf_def_bones'] = False
                export_settings['gltf_bake_animation'] = False
            export_settings['gltf_animation_mode'] = self.export_animation_mode
            if export_settings['gltf_animation_mode'] == "NLA_TRACKS":
                export_settings['gltf_force_sampling'] = True
            if export_settings['gltf_animation_mode'] == "SCENE":
                export_settings['gltf_anim_scene_split_object'] = self.export_anim_scene_split_object
            else:
                export_settings['gltf_anim_scene_split_object'] = False

            export_settings['gltf_nla_strips_merged_animation_name'] = self.export_nla_strips_merged_animation_name
            export_settings['gltf_optimize_animation'] = self.export_optimize_animation_size
            export_settings['gltf_optimize_animation_keep_armature'] = self.export_optimize_animation_keep_anim_armature
            export_settings['gltf_optimize_animation_keep_object'] = self.export_optimize_animation_keep_anim_object
            export_settings['gltf_export_anim_single_armature'] = self.export_anim_single_armature
            export_settings['gltf_export_reset_pose_bones'] = self.export_reset_pose_bones
            export_settings['gltf_export_reset_sk_data'] = self.export_morph_reset_sk_data
            export_settings['gltf_bake_animation'] = self.export_bake_animation
            export_settings['gltf_negative_frames'] = self.export_negative_frame
            export_settings['gltf_anim_slide_to_zero'] = self.export_anim_slide_to_zero
        else:
            export_settings['gltf_frame_range'] = False
            export_settings['gltf_force_sampling'] = False
            export_settings['gltf_bake_animation'] = False
            export_settings['gltf_optimize_animation'] = False
            export_settings['gltf_optimize_animation_keep_armature'] = False
            export_settings['gltf_optimize_animation_keep_object'] = False
            export_settings['gltf_export_anim_single_armature'] = False
            export_settings['gltf_export_reset_pose_bones'] = False
            export_settings['gltf_export_reset_sk_data'] = False
        export_settings['gltf_skins'] = self.export_skins
        if self.export_skins:
            export_settings['gltf_all_vertex_influences'] = self.export_all_influences
            export_settings['gltf_vertex_influences_nb'] = self.export_influence_nb
        else:
            export_settings['gltf_all_vertex_influences'] = False
            export_settings['gltf_def_bones'] = False
        export_settings['gltf_rest_position_armature'] = self.export_rest_position_armature
        export_settings['gltf_frame_step'] = self.export_frame_step

        export_settings['gltf_morph'] = self.export_morph
        if self.export_morph:
            export_settings['gltf_morph_normal'] = self.export_morph_normal
            export_settings['gltf_morph_tangent'] = self.export_morph_tangent
            export_settings['gltf_morph_anim'] = self.export_morph_animation
        else:
            export_settings['gltf_morph_normal'] = False
            export_settings['gltf_morph_tangent'] = False
            export_settings['gltf_morph_anim'] = False

        export_settings['gltf_lights'] = self.export_lights
        export_settings['gltf_lighting_mode'] = self.export_import_convert_lighting_mode
        export_settings['gltf_gpu_instances'] = self.export_gpu_instances

        export_settings['gltf_try_sparse_sk'] = self.export_try_sparse_sk
        export_settings['gltf_try_omit_sparse_sk'] = self.export_try_omit_sparse_sk
        if not self.export_try_sparse_sk:
            export_settings['gltf_try_omit_sparse_sk'] = False

        export_settings['gltf_hierarchy_full_collections'] = self.export_hierarchy_full_collections

        # gltfpack stuff
        export_settings['gltf_use_gltfpack'] = self.export_use_gltfpack
        if self.export_use_gltfpack:
            export_settings['gltf_gltfpack_tc'] = self.export_gltfpack_tc
            export_settings['gltf_gltfpack_tq'] = self.export_gltfpack_tq

            export_settings['gltf_gltfpack_si'] = self.export_gltfpack_si
            export_settings['gltf_gltfpack_sa'] = self.export_gltfpack_sa
            export_settings['gltf_gltfpack_slb'] = self.export_gltfpack_slb

            export_settings['gltf_gltfpack_vp'] = self.export_gltfpack_vp
            export_settings['gltf_gltfpack_vt'] = self.export_gltfpack_vt
            export_settings['gltf_gltfpack_vn'] = self.export_gltfpack_vn
            export_settings['gltf_gltfpack_vc'] = self.export_gltfpack_vc

            export_settings['gltf_gltfpack_vpi'] = self.export_gltfpack_vpi

            export_settings['gltf_gltfpack_noq'] = self.export_gltfpack_noq

        export_settings['gltf_binary'] = bytearray()
        export_settings['gltf_binaryfilename'] = (
            path_to_uri(os.path.splitext(os.path.basename(self.filepath))[0] + '.bin')
        )

        user_extensions = []
        pre_export_callbacks = []
        post_export_callbacks = []

        import sys
        preferences = bpy.context.preferences
        for addon_name in preferences.addons.keys():
            try:
                module = sys.modules[addon_name]
            except Exception:
                continue
            if hasattr(module, 'glTF2ExportUserExtension'):
                extension_ctor = module.glTF2ExportUserExtension
                user_extensions.append(extension_ctor())
            if hasattr(module, 'glTF2ExportUserExtensions'):
                extension_ctors = module.glTF2ExportUserExtensions
                for extension_ctor in extension_ctors:
                    user_extensions.append(extension_ctor())
            if hasattr(module, 'glTF2_pre_export_callback'):
                pre_export_callbacks.append(module.glTF2_pre_export_callback)
            if hasattr(module, 'glTF2_post_export_callback'):
                post_export_callbacks.append(module.glTF2_post_export_callback)
        export_settings['gltf_user_extensions'] = user_extensions
        export_settings['pre_export_callbacks'] = pre_export_callbacks
        export_settings['post_export_callbacks'] = post_export_callbacks

        return gltf2_blender_export.save(context, export_settings)

    def draw(self, context):
        pass # Is needed to get panels available


class GLTF_PT_export_main(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = ""
    bl_parent_id = "FILE_PT_operator"
    bl_options = {'HIDE_HEADER'}

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator

        return operator.bl_idname == "EXPORT_SCENE_OT_gltf"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        sfile = context.space_data
        operator = sfile.active_operator

        layout.prop(operator, 'export_format')
        if operator.export_format == 'GLTF_SEPARATE':
            layout.prop(operator, 'export_keep_originals')
            if operator.export_keep_originals is False:
                layout.prop(operator, 'export_texture_dir', icon='FILE_FOLDER')
        if operator.export_format == 'GLTF_EMBEDDED':
            layout.label(text="This is the least efficient of the available forms, and should only be used when required.", icon='ERROR')

        layout.prop(operator, 'export_copyright')
        layout.prop(operator, 'will_save_settings')


class GLTF_PT_export_gltfpack(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "gltfpack"
    bl_parent_id = "FILE_PT_operator"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        gltfpack_path = context.preferences.addons['io_scene_gltf2'].preferences.gltfpack_path_ui.strip()
        if (gltfpack_path == ''): # gltfpack not setup in plugin preferences -> dont show any gltfpack relevant options in export dialog
            return False

        sfile = context.space_data
        operator = sfile.active_operator

        return operator.bl_idname == "EXPORT_SCENE_OT_gltf"

    def draw(self, context):

        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        sfile = context.space_data
        operator = sfile.active_operator

        col = layout.column(heading = "gltfpack", align = True)
        col.prop(operator, 'export_use_gltfpack')

        col = layout.column(heading = "Textures", align = True)
        col.prop(operator, 'export_gltfpack_tc')
        col.prop(operator, 'export_gltfpack_tq')
        col = layout.column(heading = "Simplification", align = True)
        col.prop(operator, 'export_gltfpack_si')
        col.prop(operator, 'export_gltfpack_sa')
        col.prop(operator, 'export_gltfpack_slb')
        col = layout.column(heading = "Vertices", align = True)
        col.prop(operator, 'export_gltfpack_vp')
        col.prop(operator, 'export_gltfpack_vt')
        col.prop(operator, 'export_gltfpack_vn')
        col.prop(operator, 'export_gltfpack_vc')
        col = layout.column(heading = "Vertex positions", align = True)
        col.prop(operator, 'export_gltfpack_vpi')
        #col = layout.column(heading = "Animations", align = True)
        #col = layout.column(heading = "Scene", align = True)
        col = layout.column(heading = "Miscellaneous", align = True)
        col.prop(operator, 'export_gltfpack_noq')


class GLTF_PT_export_include(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Include"
    bl_parent_id = "FILE_PT_operator"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator

        return operator.bl_idname == "EXPORT_SCENE_OT_gltf"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        sfile = context.space_data
        operator = sfile.active_operator

        col = layout.column(heading = "Limit to", align = True)
        col.prop(operator, 'use_selection')
        col.prop(operator, 'use_visible')
        col.prop(operator, 'use_renderable')
        col.prop(operator, 'use_active_collection')
        if operator.use_active_collection:
            col.prop(operator, 'use_active_collection_with_nested')
        col.prop(operator, 'use_active_scene')

        col = layout.column(heading = "Data", align = True)
        col.prop(operator, 'export_extras')
        col.prop(operator, 'export_cameras')
        col.prop(operator, 'export_lights')


class GLTF_PT_export_transform(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Transform"
    bl_parent_id = "FILE_PT_operator"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator

        return operator.bl_idname == "EXPORT_SCENE_OT_gltf"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        sfile = context.space_data
        operator = sfile.active_operator

        layout.prop(operator, 'export_yup')


class GLTF_PT_export_data(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Data"
    bl_parent_id = "FILE_PT_operator"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator

        return operator.bl_idname == "EXPORT_SCENE_OT_gltf"

    def draw(self, context):
        pass

class GLTF_PT_export_data_scene(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Scene Graph"
    bl_parent_id = "GLTF_PT_export_data"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator
        return operator.bl_idname == "EXPORT_SCENE_OT_gltf"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        sfile = context.space_data
        operator = sfile.active_operator
        layout.prop(operator, 'export_gn_mesh')
        layout.prop(operator, 'export_gpu_instances')
        layout.prop(operator, 'export_hierarchy_flatten_objs')
        layout.prop(operator, 'export_hierarchy_full_collections')

class GLTF_PT_export_data_mesh(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Mesh"
    bl_parent_id = "GLTF_PT_export_data"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator
        return operator.bl_idname == "EXPORT_SCENE_OT_gltf"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        sfile = context.space_data
        operator = sfile.active_operator

        layout.prop(operator, 'export_apply')
        layout.prop(operator, 'export_texcoords')
        layout.prop(operator, 'export_normals')
        col = layout.column()
        col.active = operator.export_normals
        col.prop(operator, 'export_tangents')
        layout.prop(operator, 'export_attributes')

        col = layout.column()
        col.prop(operator, 'use_mesh_edges')
        col.prop(operator, 'use_mesh_vertices')

        col = layout.column()
        col.prop(operator, 'export_shared_accessors')


class GLTF_PT_export_data_material(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Material"
    bl_parent_id = "GLTF_PT_export_data"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator
        return operator.bl_idname == "EXPORT_SCENE_OT_gltf"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        sfile = context.space_data
        operator = sfile.active_operator

        layout.prop(operator, 'export_materials')
        col = layout.column()
        col.active = operator.export_materials == "EXPORT"
        col.prop(operator, 'export_image_format')
        if operator.export_image_format in ["AUTO", "JPEG", "WEBP"]:
            col.prop(operator, 'export_image_quality')
        col = layout.column()
        col.active = operator.export_image_format != "WEBP"
        col.prop(operator, "export_image_add_webp")
        col = layout.column()
        col.active = operator.export_image_format != "WEBP"
        col.prop(operator, "export_image_webp_fallback")

class GLTF_PT_export_unsed_tex_image(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Unused Textures & Images"
    bl_parent_id = "GLTF_PT_export_data_material"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator

        return operator.bl_idname == "EXPORT_SCENE_OT_gltf"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        sfile = context.space_data
        operator = sfile.active_operator

        row = layout.row()
        row.prop(operator, 'export_unused_images')
        row = layout.row()
        row.prop(operator, 'export_unused_textures')


class GLTF_PT_export_data_lighting(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Lighting"
    bl_parent_id = "GLTF_PT_export_data"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator
        return operator.bl_idname == "EXPORT_SCENE_OT_gltf"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        sfile = context.space_data
        operator = sfile.active_operator

        layout.prop(operator, 'export_import_convert_lighting_mode')

class GLTF_PT_export_data_shapekeys(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Shape Keys"
    bl_parent_id = "GLTF_PT_export_data"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator

        return operator.bl_idname == "EXPORT_SCENE_OT_gltf"

    def draw_header(self, context):
        sfile = context.space_data
        operator = sfile.active_operator
        self.layout.prop(operator, "export_morph", text="")

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        sfile = context.space_data
        operator = sfile.active_operator

        layout.active = operator.export_morph

        layout.prop(operator, 'export_morph_normal')
        col = layout.column()
        col.active = operator.export_morph_normal
        col.prop(operator, 'export_morph_tangent')


class GLTF_PT_export_data_sk_optimize(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Optimize Shape Keys"
    bl_parent_id = "GLTF_PT_export_data_shapekeys"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator

        return operator.bl_idname == "EXPORT_SCENE_OT_gltf"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        sfile = context.space_data
        operator = sfile.active_operator

        row = layout.row()
        row.prop(operator, 'export_try_sparse_sk')

        row = layout.row()
        row.active = operator.export_try_sparse_sk
        row.prop(operator, 'export_try_omit_sparse_sk')


class GLTF_PT_export_data_skinning(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Skinning"
    bl_parent_id = "GLTF_PT_export_data"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator

        return operator.bl_idname == "EXPORT_SCENE_OT_gltf"

    def draw_header(self, context):
        sfile = context.space_data
        operator = sfile.active_operator
        self.layout.prop(operator, "export_skins", text="")

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        sfile = context.space_data
        operator = sfile.active_operator

        layout.active = operator.export_skins

        row = layout.row()
        row.prop(operator, 'export_influence_nb')
        row.active = not operator.export_all_influences
        layout.prop(operator, 'export_all_influences')


class GLTF_PT_export_data_armature(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Armature"
    bl_parent_id = "GLTF_PT_export_data"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator

        return operator.bl_idname == "EXPORT_SCENE_OT_gltf"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        sfile = context.space_data
        operator = sfile.active_operator

        layout.active = operator.export_skins

        layout.prop(operator, 'export_rest_position_armature')

        row = layout.row()
        row.active = operator.export_force_sampling
        row.prop(operator, 'export_def_bones')
        if operator.export_force_sampling is False and operator.export_def_bones is True:
            layout.label(text="Export only deformation bones is not possible when not sampling animation")
        row = layout.row()
        row.prop(operator, 'export_armature_object_remove')
        row = layout.row()
        row.prop(operator, 'export_hierarchy_flatten_bones')

class GLTF_PT_export_data_compression(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Compression"
    bl_parent_id = "GLTF_PT_export_data"
    bl_options = {'DEFAULT_CLOSED'}

    def __init__(self):
        from .io.com import gltf2_io_draco_compression_extension
        self.is_draco_available = gltf2_io_draco_compression_extension.dll_exists(quiet=True)

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator
        if operator.is_draco_available:
            return operator.bl_idname == "EXPORT_SCENE_OT_gltf"

    def draw_header(self, context):
        sfile = context.space_data
        operator = sfile.active_operator
        self.layout.prop(operator, "export_draco_mesh_compression_enable", text="")

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        sfile = context.space_data
        operator = sfile.active_operator

        layout.active = operator.export_draco_mesh_compression_enable
        layout.prop(operator, 'export_draco_mesh_compression_level')

        col = layout.column(align=True)
        col.prop(operator, 'export_draco_position_quantization', text="Quantize Position")
        col.prop(operator, 'export_draco_normal_quantization', text="Normal")
        col.prop(operator, 'export_draco_texcoord_quantization', text="Tex Coord")
        col.prop(operator, 'export_draco_color_quantization', text="Color")
        col.prop(operator, 'export_draco_generic_quantization', text="Generic")


class GLTF_PT_export_animation(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Animation"
    bl_parent_id = "FILE_PT_operator"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator

        return operator.bl_idname == "EXPORT_SCENE_OT_gltf"

    def draw_header(self, context):
        sfile = context.space_data
        operator = sfile.active_operator
        self.layout.prop(operator, "export_animations", text="")

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        sfile = context.space_data
        operator = sfile.active_operator

        layout.active = operator.export_animations

        layout.prop(operator, 'export_animation_mode')
        if operator.export_animation_mode == "ACTIVE_ACTIONS":
            layout.prop(operator, 'export_nla_strips_merged_animation_name')

        row = layout.row()
        row.active = operator.export_force_sampling and operator.export_animation_mode in ['ACTIONS', 'ACTIVE_ACTIONS']
        row.prop(operator, 'export_bake_animation')
        if operator.export_animation_mode == "SCENE":
            layout.prop(operator, 'export_anim_scene_split_object')

class GLTF_PT_export_animation_notes(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Notes"
    bl_parent_id = "GLTF_PT_export_animation"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator

        return operator.bl_idname == "EXPORT_SCENE_OT_gltf" and \
            operator.export_animation_mode in ["NLA_TRACKS", "SCENE"]

    def draw(self, context):
        operator = context.space_data.active_operator
        layout = self.layout
        if operator.export_animation_mode == "SCENE":
            layout.label(text="Scene mode uses full bake mode:")
            layout.label(text="- sampling is active")
            layout.label(text="- baking all objects is active")
            layout.label(text="- Using scene frame range")
        elif operator.export_animation_mode == "NLA_TRACKS":
            layout.label(text="Track mode uses full bake mode:")
            layout.label(text="- sampling is active")
            layout.label(text="- baking all objects is active")

class GLTF_PT_export_animation_ranges(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Rest & Ranges"
    bl_parent_id = "GLTF_PT_export_animation"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator

        return operator.bl_idname == "EXPORT_SCENE_OT_gltf"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        sfile = context.space_data
        operator = sfile.active_operator

        layout.active = operator.export_animations

        layout.prop(operator, 'export_current_frame')
        row = layout.row()
        row.active = operator.export_animation_mode in ['ACTIONS', 'ACTIVE_ACTIONS', 'NLA_TRACKS']
        row.prop(operator, 'export_frame_range')
        layout.prop(operator, 'export_anim_slide_to_zero')
        row = layout.row()
        row.active = operator.export_animation_mode in ['ACTIONS', 'ACTIVE_ACTIONS', 'NLA_TRACKS']
        layout.prop(operator, 'export_negative_frame')

class GLTF_PT_export_animation_armature(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Armature"
    bl_parent_id = "GLTF_PT_export_animation"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator

        return operator.bl_idname == "EXPORT_SCENE_OT_gltf"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        sfile = context.space_data
        operator = sfile.active_operator

        layout.active = operator.export_animations

        layout.prop(operator, 'export_anim_single_armature')
        layout.prop(operator, 'export_reset_pose_bones')

class GLTF_PT_export_animation_shapekeys(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Shape Keys Animation"
    bl_parent_id = "GLTF_PT_export_animation"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator

        return operator.bl_idname == "EXPORT_SCENE_OT_gltf"

    def draw_header(self, context):
        sfile = context.space_data
        operator = sfile.active_operator
        self.layout.active = operator.export_animations and operator.export_morph
        self.layout.prop(operator, "export_morph_animation", text="")

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        sfile = context.space_data
        operator = sfile.active_operator

        layout.active = operator.export_animations

        layout.prop(operator, 'export_morph_reset_sk_data')


class GLTF_PT_export_animation_sampling(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Sampling Animations"
    bl_parent_id = "GLTF_PT_export_animation"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator

        return operator.bl_idname == "EXPORT_SCENE_OT_gltf"

    def draw_header(self, context):
        sfile = context.space_data
        operator = sfile.active_operator
        self.layout.active = operator.export_animations and operator.export_animation_mode in ['ACTIONS', 'ACTIVE_ACTIONS']
        self.layout.prop(operator, "export_force_sampling", text="")

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        sfile = context.space_data
        operator = sfile.active_operator

        layout.active = operator.export_animations

        layout.prop(operator, 'export_frame_step')


class GLTF_PT_export_animation_optimize(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Optimize Animations"
    bl_parent_id = "GLTF_PT_export_animation"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator

        return operator.bl_idname == "EXPORT_SCENE_OT_gltf"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        sfile = context.space_data
        operator = sfile.active_operator

        layout.active = operator.export_animations

        layout.prop(operator, 'export_optimize_animation_size')

        row = layout.row()
        row.prop(operator, 'export_optimize_animation_keep_anim_armature')

        row = layout.row()
        row.prop(operator, 'export_optimize_animation_keep_anim_object')


class GLTF_PT_export_user_extensions(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Exporter Extensions"
    bl_parent_id = "FILE_PT_operator"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator

        return operator.bl_idname == "EXPORT_SCENE_OT_gltf" and operator.has_active_exporter_extensions

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

class GLTF_PT_import_user_extensions(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Importer Extensions"
    bl_parent_id = "FILE_PT_operator"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator
        return operator.bl_idname == "IMPORT_SCENE_OT_gltf" and operator.has_active_importer_extensions

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

class ExportGLTF2(bpy.types.Operator, ExportGLTF2_Base, ExportHelper):
    """Export scene as glTF 2.0 file"""
    bl_idname = 'export_scene.gltf'
    bl_label = 'Export glTF 2.0'

    filename_ext = ''

    filter_glob: StringProperty(default='*.glb', options={'HIDDEN'})


def menu_func_export(self, context):
    self.layout.operator(ExportGLTF2.bl_idname, text='glTF 2.0 (.glb/.gltf)')


class ImportGLTF2(Operator, ConvertGLTF2_Base, ImportHelper):
    """Load a glTF 2.0 file"""
    bl_idname = 'import_scene.gltf'
    bl_label = 'Import glTF 2.0'
    bl_options = {'REGISTER', 'UNDO'}

    filter_glob: StringProperty(default="*.glb;*.gltf", options={'HIDDEN'})

    files: CollectionProperty(
        name="File Path",
        type=bpy.types.OperatorFileListElement,
    )

    loglevel: IntProperty(
        name='Log Level',
        description="Log Level")

    import_pack_images: BoolProperty(
        name='Pack Images',
        description='Pack all images into .blend file',
        default=True
    )

    merge_vertices: BoolProperty(
        name='Merge Vertices',
        description=(
            'The glTF format requires discontinuous normals, UVs, and '
            'other vertex attributes to be stored as separate vertices, '
            'as required for rendering on typical graphics hardware. '
            'This option attempts to combine co-located vertices where possible. '
            'Currently cannot combine verts with different normals'
        ),
        default=False,
    )

    import_shading: EnumProperty(
        name="Shading",
        items=(("NORMALS", "Use Normal Data", ""),
               ("FLAT", "Flat Shading", ""),
               ("SMOOTH", "Smooth Shading", "")),
        description="How normals are computed during import",
        default="NORMALS")

    bone_heuristic: EnumProperty(
        name="Bone Dir",
        items=(
            ("BLENDER", "Blender (best for import/export round trip)",
                "Good for re-importing glTFs exported from Blender, "
                "and re-exporting glTFs to glTFs after Blender editing. "
                "Bone tips are placed on their local +Y axis (in glTF space)"),
            ("TEMPERANCE", "Temperance (average)",
                "Decent all-around strategy. "
                "A bone with one child has its tip placed on the local axis "
                "closest to its child"),
            ("FORTUNE", "Fortune (may look better, less accurate)",
                "Might look better than Temperance, but also might have errors. "
                "A bone with one child has its tip placed at its child's root. "
                "Non-uniform scalings may get messed up though, so beware"),
        ),
        description="Heuristic for placing bones. Tries to make bones pretty",
        default="BLENDER",
    )

    guess_original_bind_pose: BoolProperty(
        name='Guess Original Bind Pose',
        description=(
            'Try to guess the original bind pose for skinned meshes from '
            'the inverse bind matrices. '
            'When off, use default/rest pose as bind pose'
        ),
        default=True,
    )

    import_webp_texture: BoolProperty(
        name='Import WebP textures',
        description=(
            "If a texture exists in WebP format, "
            "loads the WebP texture instead of the fallback PNG/JPEG one"
        ),
        default=False,
    )

    def draw(self, context):
        layout = self.layout

        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        layout.prop(self, 'import_pack_images')
        layout.prop(self, 'merge_vertices')
        layout.prop(self, 'import_shading')
        layout.prop(self, 'guess_original_bind_pose')
        layout.prop(self, 'bone_heuristic')
        layout.prop(self, 'export_import_convert_lighting_mode')
        layout.prop(self, 'import_webp_texture')

    def invoke(self, context, event):
        import sys
        preferences = bpy.context.preferences
        for addon_name in preferences.addons.keys():
            try:
                if hasattr(sys.modules[addon_name], 'glTF2ImportUserExtension') or hasattr(sys.modules[addon_name], 'glTF2ImportUserExtensions'):
                    importer_extension_panel_unregister_functors.append(sys.modules[addon_name].register_panel())
            except Exception:
                pass

        self.has_active_importer_extensions = len(importer_extension_panel_unregister_functors) > 0
        return ImportHelper.invoke(self, context, event)

    def execute(self, context):
        return self.import_gltf2(context)

    def import_gltf2(self, context):
        import os

        self.set_debug_log()
        import_settings = self.as_keywords()

        user_extensions = []

        import sys
        preferences = bpy.context.preferences
        for addon_name in preferences.addons.keys():
            try:
                module = sys.modules[addon_name]
            except Exception:
                continue
            if hasattr(module, 'glTF2ImportUserExtension'):
                extension_ctor = module.glTF2ImportUserExtension
                user_extensions.append(extension_ctor())
        import_settings['import_user_extensions'] = user_extensions

        if self.files:
            # Multiple file import
            ret = {'CANCELLED'}
            dirname = os.path.dirname(self.filepath)
            for file in self.files:
                path = os.path.join(dirname, file.name)
                if self.unit_import(path, import_settings) == {'FINISHED'}:
                    ret = {'FINISHED'}
            return ret
        else:
            # Single file import
            return self.unit_import(self.filepath, import_settings)

    def unit_import(self, filename, import_settings):
        import time
        from .io.imp.gltf2_io_gltf import glTFImporter, ImportError
        from .blender.imp.gltf2_blender_gltf import BlenderGlTF

        try:
            gltf_importer = glTFImporter(filename, import_settings)
            gltf_importer.read()
            gltf_importer.checks()

            print("Data are loaded, start creating Blender stuff")

            start_time = time.time()
            BlenderGlTF.create(gltf_importer)
            elapsed_s = "{:.2f}s".format(time.time() - start_time)
            print("glTF import finished in " + elapsed_s)

            gltf_importer.log.removeHandler(gltf_importer.log_handler)

            return {'FINISHED'}

        except ImportError as e:
            self.report({'ERROR'}, e.args[0])
            return {'CANCELLED'}

    def set_debug_log(self):
        import logging
        if bpy.app.debug_value == 0:
            self.loglevel = logging.CRITICAL
        elif bpy.app.debug_value == 1:
            self.loglevel = logging.ERROR
        elif bpy.app.debug_value == 2:
            self.loglevel = logging.WARNING
        elif bpy.app.debug_value == 3:
            self.loglevel = logging.INFO
        else:
            self.loglevel = logging.NOTSET


class GLTF2_filter_action(bpy.types.PropertyGroup):
    keep : bpy.props.BoolProperty(name="Keep Animation")
    action: bpy.props.PointerProperty(type=bpy.types.Action)

def gltf_variant_ui_update(self, context):
    from .blender.com.gltf2_blender_ui import variant_register, variant_unregister
    if self.KHR_materials_variants_ui is True:
        # register all needed types
        variant_register()
    else:
        variant_unregister()

def gltf_animation_ui_update(self, context):
    from .blender.com.gltf2_blender_ui import anim_ui_register, anim_ui_unregister
    if self.animation_ui is True:
        # register all needed types
        anim_ui_register()
    else:
        anim_ui_unregister()

class GLTF_AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    settings_node_ui : bpy.props.BoolProperty(
        default= False,
        description="Displays glTF Material Output node in Shader Editor (Menu Add > Output)"
    )

    KHR_materials_variants_ui : bpy.props.BoolProperty(
        default= False,
        description="Displays glTF UI to manage material variants",
        update=gltf_variant_ui_update
    )

    animation_ui: bpy.props.BoolProperty(
        default=False,
        description="Display glTF UI to manage animations",
        update=gltf_animation_ui_update
    )

    gltfpack_path_ui: bpy.props.StringProperty(
        default="",
        name="glTFpack file path",
        description="Path to gltfpack binary",
        subtype='FILE_PATH'
    )

    allow_embedded_format: bpy.props.BoolProperty(
        default = False,
        name='Allow glTF Embedded format',
        description="Allow glTF Embedded format"
    )

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.prop(self, "settings_node_ui", text="Shader Editor Add-ons")
        row.prop(self, "KHR_materials_variants_ui", text="Material Variants")
        row.prop(self, "animation_ui", text="Animation UI")
        row = layout.row()
        row.prop(self, "gltfpack_path_ui", text="Path to gltfpack")
        row = layout.row()
        row.prop(self, "allow_embedded_format", text="Allow glTF Embedded format")
        if self.allow_embedded_format:
            layout.label(text="This is the least efficient of the available forms, and should only be used when required.", icon='ERROR')

def menu_func_import(self, context):
    self.layout.operator(ImportGLTF2.bl_idname, text='glTF 2.0 (.glb/.gltf)')


classes = (
    ExportGLTF2,
    GLTF_PT_export_main,
    GLTF_PT_export_include,
    GLTF_PT_export_transform,
    GLTF_PT_export_data,
    GLTF_PT_export_data_scene,
    GLTF_PT_export_data_mesh,
    GLTF_PT_export_data_material,
    GLTF_PT_export_unsed_tex_image,
    GLTF_PT_export_data_shapekeys,
    GLTF_PT_export_data_sk_optimize,
    GLTF_PT_export_data_armature,
    GLTF_PT_export_data_skinning,
    GLTF_PT_export_data_lighting,
    GLTF_PT_export_data_compression,
    GLTF_PT_export_animation,
    GLTF_PT_export_animation_notes,
    GLTF_PT_export_animation_ranges,
    GLTF_PT_export_animation_armature,
    GLTF_PT_export_animation_shapekeys,
    GLTF_PT_export_animation_sampling,
    GLTF_PT_export_animation_optimize,
    GLTF_PT_export_gltfpack,
    GLTF_PT_export_user_extensions,
    ImportGLTF2,
    GLTF_PT_import_user_extensions,
    GLTF2_filter_action,
    GLTF_AddonPreferences
)


def register():
    from .blender.com import gltf2_blender_ui as blender_ui

    for c in classes:
        bpy.utils.register_class(c)
    # bpy.utils.register_module(__name__)

    blender_ui.register()
    if bpy.context.preferences.addons['io_scene_gltf2'].preferences.KHR_materials_variants_ui is True:
        blender_ui.variant_register()
    if bpy.context.preferences.addons['io_scene_gltf2'].preferences.animation_ui is True:
        blender_ui.anim_ui_register()

    # add to the export / import menu
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    from .blender.com import gltf2_blender_ui as blender_ui
    blender_ui.unregister()
    if bpy.context.preferences.addons['io_scene_gltf2'].preferences.KHR_materials_variants_ui is True:
        blender_ui.variant_unregister()

    for c in classes:
        bpy.utils.unregister_class(c)
    for f in exporter_extension_panel_unregister_functors:
        f()
    exporter_extension_panel_unregister_functors.clear()

    for f in importer_extension_panel_unregister_functors:
        f()
    importer_extension_panel_unregister_functors.clear()

    # bpy.utils.unregister_module(__name__)

    # remove from the export / import menu
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
