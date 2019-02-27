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

#
# Imports
#

import os
import time
import bpy
from bpy_extras.io_utils import ImportHelper, ExportHelper
from bpy.types import Operator, AddonPreferences

from .io.com.gltf2_io_debug import Log

from bpy.props import (CollectionProperty,
                       StringProperty,
                       BoolProperty,
                       EnumProperty,
                       FloatProperty,
                       IntProperty)

from io_scene_gltf2.io.exp import gltf2_io_draco_compression_extension

#
# Globals
#

bl_info = {
    'name': 'glTF 2.0 format',
    'author': 'Julien Duroure, Norbert Nopper, Urs Hanselmann, Moritz Becher, Benjamin Schmithüsen, Jim Eckerlein',
    "version": (0, 0, 1),
    'blender': (2, 80, 0),
    'location': 'File > Import-Export',
    'description': 'Import-Export as glTF 2.0',
    'warning': '',
    'wiki_url': "https://docs.blender.org/manual/en/dev/addons/io_gltf2.html",
    'tracker_url': "https://github.com/KhronosGroup/glTF-Blender-IO/issues/",
    'support': 'OFFICIAL',
    'category': 'Import-Export'}


#
#  Functions / Classes.
#


class ExportGLTF2_Base:
    # TODO: refactor to avoid boilerplate

    def __init__(self):
        self.is_draco_available = gltf2_io_draco_compression_extension.dll_exists()

    bl_options = {'UNDO', 'PRESET'}

    export_format = EnumProperty(
        name='Format',
        items=(('GLB', 'glTF Binary (.glb)',
                'Exports a single file, with all data packed in binary form. '
                'Most efficient and portable, but more difficult to edit later'),
               ('GLTF_EMBEDDED', 'glTF Embedded (.gltf)',
                'Exports a single file, with all data packed in JSON. '
                'Less efficient than binary, but easier to edit later'),
               ('GLTF_SEPARATE', 'glTF Separate (.gltf + .bin + textures)',
                'Exports multiple files, with separate JSON, binary and texture data. '
                'Easiest to edit later')),
        description=(
            'Output format and embedding options. Binary is most efficient, '
            'but JSON (embedded or separate) may be easier to edit later'
        ),
        default='GLB'
    )

    ui_tab = EnumProperty(
        items=(('GENERAL', "General", "General settings"),
               ('MESHES', "Meshes", "Mesh settings"),
               ('OBJECTS', "Objects", "Object settings"),
               ('ANIMATION', "Animation", "Animation settings")),
        name="ui_tab",
        description="Export setting categories",
    )

    export_copyright = StringProperty(
        name='Copyright',
        description='Legal rights and conditions for the model',
        default=''
    )

    export_texcoords = BoolProperty(
        name='UVs',
        description='Export UVs (texture coordinates) with meshes',
        default=True
    )

    export_normals = BoolProperty(
        name='Normals',
        description='Export vertex normals with meshes',
        default=True
    )

    export_draco_mesh_compression_enable = BoolProperty(
        name='Draco mesh compression',
        description='Compress mesh using Draco',
        default=False
    )

    export_draco_mesh_compression_level = IntProperty(
        name='Compression level',
        description='Compression level (0 = most speed, 6 = most compression, higher values currently not supported)',
        default=6,
        min=0,
        max=6
    )

    export_draco_position_quantization = IntProperty(
        name='Position quantization bits',
        description='Quantization bits for position values (0 = no quantization)',
        default=14,
        min=0,
        max=30
    )

    export_draco_normal_quantization = IntProperty(
        name='Normal quantization bits',
        description='Quantization bits for normal values (0 = no quantization)',
        default=10,
        min=0,
        max=30
    )

    export_draco_texcoord_quantization = IntProperty(
        name='Texcoord quantization bits',
        description='Quantization bits for texture coordinate values (0 = no quantization)',
        default=12,
        min=0,
        max=30
    )

    export_tangents = BoolProperty(
        name='Tangents',
        description='Export vertex tangents with meshes',
        default=False
    )

    export_materials = BoolProperty(
        name='Materials',
        description='Export materials',
        default=True
    )

    export_colors = BoolProperty(
        name='Vertex Colors',
        description='Export vertex colors with meshes',
        default=True
    )

    export_cameras = BoolProperty(
        name='Cameras',
        description='Export cameras',
        default=False
    )

    export_selected = BoolProperty(
        name='Selected Objects',
        description='Export selected objects only',
        default=False
    )

    # export_layers = BoolProperty(
    #     name='All layers',
    #     description='Export all layers, rather than just the first',
    #     default=True
    # )

    export_extras = BoolProperty(
        name='Custom Properties',
        description='Export custom properties as glTF extras',
        default=False
    )

    export_yup = BoolProperty(
        name='+Y Up',
        description='Export using glTF convention, +Y up',
        default=True
    )

    export_apply = BoolProperty(
        name='Apply Modifiers',
        description='Apply modifiers (excluding Armatures) to mesh objects',
        default=False
    )

    export_animations = BoolProperty(
        name='Animations',
        description='Exports active actions and NLA tracks as glTF animations',
        default=True
    )

    export_frame_range = BoolProperty(
        name='Limit to Playback Range',
        description='Clips animations to selected playback range',
        default=True
    )

    export_frame_step = IntProperty(
        name='Sampling Rate',
        description='How often to evaluate animated values (in frames)',
        default=1,
        min=1,
        max=120
    )

    export_move_keyframes = BoolProperty(
        name='Keyframes Start at 0',
        description='Keyframes start at 0, instead of 1',
        default=True
    )

    export_force_sampling = BoolProperty(
        name='Always Sample Animations',
        description='Apply sampling to all animations',
        default=False
    )

    export_current_frame = BoolProperty(
        name='Use Current Frame',
        description='Export the scene in the current animation frame',
        default=True
    )

    export_skins = BoolProperty(
        name='Skinning',
        description='Export skinning (armature) data',
        default=True
    )

    export_bake_skins = BoolProperty(
        name='Bake Skinning Constraints',
        description='Apply skinning constraints to armatures',
        default=False
    )

    export_all_influences = BoolProperty(
        name='Include All Bone Influences',
        description='Allow >4 joint vertex influences. Models may appear incorrectly in many viewers',
        default=False
    )

    export_morph = BoolProperty(
        name='Shape Keys',
        description='Export shape keys (morph targets)',
        default=True
    )

    export_morph_normal = BoolProperty(
        name='Shape Key Normals',
        description='Export vertex normals with shape keys (morph targets)',
        default=True
    )

    export_morph_tangent = BoolProperty(
        name='Shape Key Tangents',
        description='Export vertex tangents with shape keys (morph targets)',
        default=False
    )

    export_lights = BoolProperty(
        name='Punctual Lights',
        description='Export directional, point, and spot lights. '
                    'Uses "KHR_lights_punctual" glTF extension',
        default=False
    )

    export_displacement = BoolProperty(
        name='Displacement Textures (EXPERIMENTAL)',
        description='EXPERIMENTAL: Export displacement textures. '
                    'Uses incomplete "KHR_materials_displacement" glTF extension',
        default=False
    )

    will_save_settings = BoolProperty(
        name='Remember Export Settings',
        description='Store glTF export settings in the Blender project',
        default=False)

    # Custom scene property for saving settings
    scene_key = "glTF2ExportSettings"

    #

    def invoke(self, context, event):
        settings = context.scene.get(self.scene_key)
        self.will_save_settings = False
        if settings:
            try:
                for (k, v) in settings.items():
                    setattr(self, k, v)
                self.will_save_settings = True

            except (AttributeError, TypeError):
                self.report({"ERROR"}, "Loading export settings failed. Removed corrupted settings")
                del context.scene[self.scene_key]

        return ExportHelper.invoke(self, context, event)

    def save_settings(self, context):
        # find all export_ props
        all_props = self.properties
        export_props = {x: getattr(self, x) for x in dir(all_props)
                        if x.startswith("export_") and all_props.get(x) is not None}

        context.scene[self.scene_key] = export_props

    def execute(self, context):
        import datetime
        from .blender.exp import gltf2_blender_export

        if self.will_save_settings:
            self.save_settings(context)

        if self.export_format == 'GLB':
            self.filename_ext = '.glb'
        else:
            self.filename_ext = '.gltf'

        # All custom export settings are stored in this container.
        export_settings = {}

        export_settings['timestamp'] = datetime.datetime.now()

        export_settings['gltf_filepath'] = bpy.path.ensure_ext(self.filepath, self.filename_ext)
        export_settings['gltf_filedirectory'] = os.path.dirname(export_settings['gltf_filepath']) + '/'

        export_settings['gltf_format'] = self.export_format
        export_settings['gltf_copyright'] = self.export_copyright
        export_settings['gltf_texcoords'] = self.export_texcoords
        export_settings['gltf_normals'] = self.export_normals
        export_settings['gltf_tangents'] = self.export_tangents and self.export_normals

        if self.is_draco_available:
            export_settings['gltf_draco_mesh_compression'] = self.export_draco_mesh_compression_enable
            export_settings['gltf_draco_mesh_compression_level'] = self.export_draco_mesh_compression_level
            export_settings['gltf_draco_position_quantization'] = self.export_draco_position_quantization
            export_settings['gltf_draco_normal_quantization'] = self.export_draco_normal_quantization
            export_settings['gltf_draco_texcoord_quantization'] = self.export_draco_texcoord_quantization
        else:
            export_settings['gltf_draco_mesh_compression'] = False

        export_settings['gltf_materials'] = self.export_materials
        export_settings['gltf_colors'] = self.export_colors
        export_settings['gltf_cameras'] = self.export_cameras
        export_settings['gltf_selected'] = self.export_selected
        export_settings['gltf_layers'] = True  # self.export_layers
        export_settings['gltf_extras'] = self.export_extras
        export_settings['gltf_yup'] = self.export_yup
        export_settings['gltf_apply'] = self.export_apply
        export_settings['gltf_animations'] = self.export_animations
        if self.export_animations:
            export_settings['gltf_current_frame'] = False
            export_settings['gltf_frame_range'] = self.export_frame_range
            export_settings['gltf_move_keyframes'] = self.export_move_keyframes
            export_settings['gltf_force_sampling'] = self.export_force_sampling
        else:
            export_settings['gltf_current_frame'] = self.export_current_frame
            export_settings['gltf_frame_range'] = False
            export_settings['gltf_move_keyframes'] = False
            export_settings['gltf_force_sampling'] = False
        export_settings['gltf_skins'] = self.export_skins
        if self.export_skins:
            export_settings['gltf_bake_skins'] = self.export_bake_skins
            export_settings['gltf_all_vertex_influences'] = self.export_all_influences
        else:
            export_settings['gltf_bake_skins'] = False
            export_settings['gltf_all_vertex_influences'] = False
        export_settings['gltf_frame_step'] = self.export_frame_step
        export_settings['gltf_morph'] = self.export_morph
        if self.export_morph:
            export_settings['gltf_morph_normal'] = self.export_morph_normal
        else:
            export_settings['gltf_morph_normal'] = False
        if self.export_morph and self.export_morph_normal:
            export_settings['gltf_morph_tangent'] = self.export_morph_tangent
        else:
            export_settings['gltf_morph_tangent'] = False

        export_settings['gltf_lights'] = self.export_lights
        export_settings['gltf_displacement'] = self.export_displacement

        export_settings['gltf_binary'] = bytearray()
        export_settings['gltf_binaryfilename'] = os.path.splitext(os.path.basename(self.filepath))[0] + '.bin'

        return gltf2_blender_export.save(context, export_settings)

    def draw(self, context):
        self.layout.prop(self, 'ui_tab', expand=True)
        if self.ui_tab == 'GENERAL':
            self.draw_general_settings()
        elif self.ui_tab == 'MESHES':
            self.draw_mesh_settings()
        elif self.ui_tab == 'OBJECTS':
            self.draw_object_settings()
        elif self.ui_tab == 'MATERIALS':
            self.draw_material_settings()
        elif self.ui_tab == 'ANIMATION':
            self.draw_animation_settings()

    def draw_general_settings(self):
        col = self.layout.box().column()
        col.prop(self, 'export_format')
        col.prop(self, 'export_selected')
        col.prop(self, 'export_apply')
        col.prop(self, 'export_yup')
        col.prop(self, 'export_extras')
        col.prop(self, 'will_save_settings')
        col.prop(self, 'export_copyright')

    def draw_mesh_settings(self):
        col = self.layout.box().column()
        col.prop(self, 'export_texcoords')
        col.prop(self, 'export_normals')
        if self.export_normals:
            col.prop(self, 'export_tangents')
        col.prop(self, 'export_colors')
        col.prop(self, 'export_materials')

        # Add Draco compression option only if the DLL could be found.
        if self.is_draco_available:
            col.prop(self, 'export_draco_mesh_compression_enable')

            # Display options when Draco compression is enabled.
            if self.export_draco_mesh_compression_enable:
                col.prop(self, 'export_draco_mesh_compression_level')
                col.prop(self, 'export_draco_position_quantization')
                col.prop(self, 'export_draco_normal_quantization')
                col.prop(self, 'export_draco_texcoord_quantization')

    def draw_object_settings(self):
        col = self.layout.box().column()
        col.prop(self, 'export_cameras')
        col.prop(self, 'export_lights')

    def draw_animation_settings(self):
        col = self.layout.box().column()
        col.prop(self, 'export_animations')
        if self.export_animations:
            col.prop(self, 'export_frame_range')
            col.prop(self, 'export_frame_step')
            col.prop(self, 'export_move_keyframes')
            col.prop(self, 'export_force_sampling')
        else:
            col.prop(self, 'export_current_frame')
        col.prop(self, 'export_skins')
        if self.export_skins:
            col.prop(self, 'export_bake_skins')
            col.prop(self, 'export_all_influences')
        col.prop(self, 'export_morph')
        if self.export_morph:
            col.prop(self, 'export_morph_normal')
            if self.export_morph_normal:
                col.prop(self, 'export_morph_tangent')


class ExportGLTF2(bpy.types.Operator, ExportGLTF2_Base, ExportHelper):
    """Export scene as glTF 2.0 file"""
    bl_idname = 'export_scene.gltf'
    bl_label = 'Export glTF 2.0'

    filename_ext = ''

    filter_glob = StringProperty(default='*.glb;*.gltf', options={'HIDDEN'})


def menu_func_export(self, context):
    self.layout.operator(ExportGLTF2.bl_idname, text='glTF 2.0 (.glb/.gltf)')


class ImportGLTF2(Operator, ImportHelper):
    """Load a glTF 2.0 file"""
    bl_idname = 'import_scene.gltf'
    bl_label = 'Import glTF 2.0'

    filter_glob = StringProperty(default="*.glb;*.gltf", options={'HIDDEN'})

    loglevel = EnumProperty(
        items=Log.get_levels(),
        name="Log Level",
        description="Set level of log to display",
        default=Log.default())

    import_pack_images = BoolProperty(
        name='Pack images',
        description='Pack all images into .blend file',
        default=True
    )

    import_shading = EnumProperty(
        name="Shading",
        items=(("NORMALS", "Use Normal Data", ""),
               ("FLAT", "Flat Shading", ""),
               ("SMOOTH", "Smooth Shading", "")),
        description="How normals are computed during import",
        default="NORMALS")

    def draw(self, context):
        layout = self.layout

        layout.prop(self, 'loglevel')
        layout.prop(self, 'import_pack_images')
        layout.prop(self, 'import_shading')

    def execute(self, context):
        return self.import_gltf2(context)

    def import_gltf2(self, context):
        from .io.imp.gltf2_io_gltf import glTFImporter
        from .blender.imp.gltf2_blender_gltf import BlenderGlTF

        import_settings = self.as_keywords()

        self.gltf_importer = glTFImporter(self.filepath, import_settings)
        success, txt = self.gltf_importer.read()
        if not success:
            self.report({'ERROR'}, txt)
            return {'CANCELLED'}
        success, txt = self.gltf_importer.checks()
        if not success:
            self.report({'ERROR'}, txt)
            return {'CANCELLED'}
        self.gltf_importer.log.critical("Data are loaded, start creating Blender stuff")
        start_time = time.time()
        BlenderGlTF.create(self.gltf_importer)
        elapsed_s = "{:.2f}s".format(time.time() - start_time)
        self.gltf_importer.log.critical("glTF import finished in " + elapsed_s)
        self.gltf_importer.log.removeHandler(self.gltf_importer.log_handler)

        return {'FINISHED'}


def menu_func_import(self, context):
    self.layout.operator(ImportGLTF2.bl_idname, text='glTF 2.0 (.glb/.gltf)')


classes = (
    ExportGLTF2,
    ImportGLTF2
)


def register():
    for c in classes:
        bpy.utils.register_class(c)
    # bpy.utils.register_module(__name__)

    # add to the export / import menu
    if bpy.app.version < (2, 80, 0):
        bpy.types.INFO_MT_file_export.append(menu_func_export)
        bpy.types.INFO_MT_file_import.append(menu_func_import)
    else:
        bpy.types.TOPBAR_MT_file_export.append(menu_func_export)
        bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
    # bpy.utils.unregister_module(__name__)

    # remove from the export / import menu
    if bpy.app.version < (2, 80, 0):
        bpy.types.INFO_MT_file_export.remove(menu_func_export)
        bpy.types.INFO_MT_file_import.remove(menu_func_import)
    else:
        bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
        bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
