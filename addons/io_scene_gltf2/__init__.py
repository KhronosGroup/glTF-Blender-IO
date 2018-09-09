# Copyright (c) 2018 The Khronos Group Inc.
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

import bpy
import os

from bpy_extras.io_utils import ImportHelper
from bpy.types import Operator

from .io.com.gltf2_io_debug import *
from .io.imp.gltf2_io_gltf_old import *
from .io.imp.gltf2_io_gltf import *
from .blender.imp.gltf2_blender_gltf import *

from bpy.props import (CollectionProperty,
                       StringProperty,
                       BoolProperty,
                       EnumProperty,
                       FloatProperty,
                       IntProperty)


from bpy_extras.io_utils import (ExportHelper)

#
# Globals
#

bl_info = {
    'name': 'glTF 2.0 format',
    'author': 'Julien Duroure & Norbert Nopper',
    'blender': (2, 79, 0),
    'location': 'File > Import-Export',
    'description': 'Import-Export as glTF 2.0',
    'warning': '',
    'wiki_url': ''
                '',
    'support': 'COMMUNITY',
    'category': 'Import-Export'}

#
#  Functions / Classes.
#

class GLTF2ExportSettings(bpy.types.Operator):
    """Save the export settings on export (saved in .blend).
Toggle off to clear settings"""
    bl_label = "Save Settings"
    bl_idname = "scene.gltf2_export_settings_set"

    def execute(self, context):
        operator = context.active_operator
        operator.will_save_settings = not operator.will_save_settings
        if not operator.will_save_settings and context.scene.get(operator.scene_key, False):
            # clear settings
            del context.scene[operator.scene_key]
        return {"FINISHED"}

class ExportGLTF2_Base():
    export_copyright = StringProperty(
            name='Copyright',
            description='',
            default=''
    )

    export_embed_buffers = BoolProperty(
            name='Embed buffers',
            description='',
            default=False
    )

    export_embed_images = BoolProperty(
            name='Embed images',
            description='',
            default=False
    )

    export_strip = BoolProperty(
            name='Strip delimiters',
            description='',
            default=False
    )

    export_indices = EnumProperty(
        name='Maximum indices',
        items=(('UNSIGNED_BYTE', 'Unsigned Byte', ''),
        ('UNSIGNED_SHORT', 'Unsigned Short', ''),
        ('UNSIGNED_INT', 'Unsigned Integer', '')),
        default='UNSIGNED_INT'
    )

    export_force_indices = BoolProperty(
            name='Force maximum indices',
            description='',
            default=False
    )

    export_texcoords = BoolProperty(
            name='Export texture coordinates',
            description='',
            default=True
    )

    export_normals = BoolProperty(
            name='Export normals',
            description='',
            default=True
    )

    export_tangents = BoolProperty(
            name='Export tangents',
            description='',
            default=True
    )

    export_materials = BoolProperty(
            name='Export materials',
            description='',
            default=True
    )

    export_colors = BoolProperty(
            name='Export colors',
            description='',
            default=True
    )

    export_cameras = BoolProperty(
            name='Export cameras',
            description='',
            default=False
    )

    export_camera_infinite = BoolProperty(
            name='Infinite perspective Camera',
            description='',
            default=False
    )

    export_selected = BoolProperty(
            name='Export selected only',
            description='',
            default=False
    )

    export_layers = BoolProperty(
            name='Export all layers',
            description='',
            default=True
    )

    export_extras = BoolProperty(
            name='Export extras',
            description='',
            default=False
    )

    export_yup = BoolProperty(
            name='Convert Z up to Y up',
            description='',
            default=True
    )

    export_apply = BoolProperty(
            name='Apply modifiers',
            description='',
            default=False
    )

    export_animations = BoolProperty(
            name='Export animations',
            description='',
            default=True
    )

    export_frame_range = BoolProperty(
            name='Export within playback range',
            description='',
            default=True
    )

    export_frame_step = IntProperty(
            name='Frame step size',
            description='Step size (in frames) for animation export.',
            default=1,
            min=1,
            max=120
    )

    export_move_keyframes = BoolProperty(
            name='Keyframes start with 0',
            description='',
            default=True
    )

    export_force_sampling = BoolProperty(
            name='Force sample animations',
            description='',
            default=False
    )

    export_current_frame = BoolProperty(
            name='Export current frame',
            description='',
            default=True
    )

    export_skins = BoolProperty(
            name='Export skinning',
            description='',
            default=True
    )

    export_bake_skins = BoolProperty(
            name='Bake skinning constraints',
            description='',
            default=False
    )

    export_morph = BoolProperty(
            name='Export morphing',
            description='',
            default=True
    )

    export_morph_normal = BoolProperty(
            name='Export morphing normals',
            description='',
            default=True
    )

    export_morph_tangent = BoolProperty(
            name='Export morphing tangents',
            description='',
            default=True
    )

    export_lights = BoolProperty(
            name='Export KHR_lights_punctual',
            description='',
            default=False
    )

    export_texture_transform = BoolProperty(
            name='Export KHR_texture_transform',
            description='',
            default=False
    )

    export_displacement = BoolProperty(
            name='Export KHR_materials_displacement',
            description='',
            default=False
    )

    will_save_settings = BoolProperty(default=False)

    # Custom scene property for saving settings
    scene_key = "glTF2ExportSettings"

    #

    def invoke(self, context, event):
        settings = context.scene.get(self.scene_key)
        self.will_save_settings = False
        if settings:
            try:
                for (k,v) in settings.items():
                    setattr(self, k, v)
                self.will_save_settings = True

            except AttributeError:
                self.report({"ERROR"}, "Loading export settings failed. Removed corrupted settings")
                del context.scene[self.scene_key]


        return ExportHelper.invoke(self, context, event)

    def save_settings(self, context):
        # find all export_ props
        all_props = self.properties
        export_props = {x:all_props.get(x) for x in dir(all_props)
            if x.startswith("export_") and all_props.get(x) is not None}

        context.scene[self.scene_key] = export_props

    def execute(self, context):
        from .blender.exp import gltf2_blender_export

        if self.will_save_settings:
            self.save_settings(context)

        # All custom export settings are stored in this container.
        export_settings = {}

        export_settings['gltf_filepath'] = bpy.path.ensure_ext(self.filepath, self.filename_ext)
        export_settings['gltf_filedirectory'] = os.path.dirname(export_settings['gltf_filepath']) + '/'

        export_settings['gltf_format'] = self.export_format
        export_settings['gltf_copyright'] = self.export_copyright
        export_settings['gltf_embed_buffers'] = self.export_embed_buffers
        export_settings['gltf_embed_images'] = self.export_embed_images
        export_settings['gltf_strip'] = self.export_strip
        export_settings['gltf_indices'] = self.export_indices
        export_settings['gltf_force_indices'] = self.export_force_indices
        export_settings['gltf_texcoords'] = self.export_texcoords
        export_settings['gltf_normals'] = self.export_normals
        export_settings['gltf_tangents'] = self.export_tangents and self.export_normals
        export_settings['gltf_materials'] = self.export_materials
        export_settings['gltf_colors'] = self.export_colors
        export_settings['gltf_cameras'] = self.export_cameras
        if self.export_cameras:
            export_settings['gltf_camera_infinite'] = self.export_camera_infinite
        else:
            export_settings['gltf_camera_infinite'] = False
        export_settings['gltf_selected'] = self.export_selected
        export_settings['gltf_layers'] = self.export_layers
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
        else:
            export_settings['gltf_bake_skins'] = False
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
        export_settings['gltf_texture_transform'] = self.export_texture_transform
        export_settings['gltf_displacement'] = self.export_displacement

        export_settings['gltf_binary'] = bytearray()
        export_settings['gltf_binaryfilename'] = os.path.splitext(os.path.basename(self.filepath))[0] + '.bin'

        return gltf2_blender_export.save(self, context, export_settings)

    def draw(self, context):
        layout = self.layout

        #

        col = layout.box().column()
        col.label('Embedding:', icon='PACKAGE')
        col.prop(self, 'export_copyright')
        if self.export_format == 'ASCII':
            col.prop(self, 'export_embed_buffers')
            col.prop(self, 'export_embed_images')
            col.prop(self, 'export_strip')

        col = layout.box().column()
        col.label('Nodes:', icon='OOPS')
        col.prop(self, 'export_selected')
        col.prop(self, 'export_layers')
        col.prop(self, 'export_extras')
        col.prop(self, 'export_yup')

        col = layout.box().column()
        col.label('Meshes:', icon='MESH_DATA')
        col.prop(self, 'export_apply')
        col.prop(self, 'export_indices')
        col.prop(self, 'export_force_indices')

        col = layout.box().column()
        col.label('Attributes:', icon='SURFACE_DATA')
        col.prop(self, 'export_texcoords')
        col.prop(self, 'export_normals')
        if self.export_normals:
            col.prop(self, 'export_tangents')
        col.prop(self, 'export_colors')

        col = layout.box().column()
        col.label('Objects:', icon='OBJECT_DATA')
        col.prop(self, 'export_cameras')
        if self.export_cameras:
            col.prop(self, 'export_camera_infinite')

        col = layout.box().column()
        col.label('Materials:', icon='MATERIAL_DATA')
        col.prop(self, 'export_materials')
        col.prop(self, 'export_texture_transform')

        col = layout.box().column()
        col.label('Animation:', icon='OUTLINER_DATA_POSE')
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
        col.prop(self, 'export_morph')
        if self.export_morph:
            col.prop(self, 'export_morph_normal')
            if self.export_morph_normal:
                col.prop(self, 'export_morph_tangent')

        addon_prefs = context.user_preferences.addons[__name__].preferences
        if addon_prefs.experimental:
            col = layout.box().column()
            col.label('Experimental:', icon='RADIO')
            col.prop(self, 'export_lights')
            col.prop(self, 'export_displacement')

        row = layout.row()
        row.operator(
            GLTF2ExportSettings.bl_idname,
            GLTF2ExportSettings.bl_label,
            icon="%s" % "PINNED" if self.will_save_settings else "UNPINNED")


class ExportGLTF2_GLTF(bpy.types.Operator, ExportGLTF2_Base, ExportHelper):
    '''Export scene as glTF 2.0 file'''
    bl_idname = 'export_scene.gltf'
    bl_label = 'Export glTF 2.0'

    filename_ext = '.gltf'
    filter_glob = StringProperty(default='*.gltf', options={'HIDDEN'})

    export_format = 'ASCII'


class ExportGLTF2_GLB(bpy.types.Operator, ExportGLTF2_Base, ExportHelper):
    '''Export scene as glTF 2.0 file'''
    bl_idname = 'export_scene.glb'
    bl_label = 'Export glTF 2.0 binary'

    filename_ext = '.glb'
    filter_glob = StringProperty(default='*.glb', options={'HIDDEN'})

    export_format = 'BINARY'


def menu_func_export_gltf(self, context):
    self.layout.operator(ExportGLTF2_GLTF.bl_idname, text='glTF 2.0 (.gltf)')


def menu_func_export_glb(self, context):
    self.layout.operator(ExportGLTF2_GLB.bl_idname, text='glTF 2.0 (.glb)')


from bpy.types import AddonPreferences

class ExportGLTF2_AddonPreferences(AddonPreferences):
    bl_idname = __name__

    experimental = BoolProperty(name='Enable experimental glTF export settings', default=False)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "experimental")


class ImportglTF2(Operator, ImportHelper):
    bl_idname = 'import_scene.gltf'
    bl_label  = "glTF 2.0 (.gltf/.glb)"

    filename_ext = ".gltf"
    filter_glob = StringProperty(default="*.gltf;*.glb", options={'HIDDEN'})

    loglevel = bpy.props.EnumProperty(items=Log.getLevels(), description="Log Level", default=Log.default())

    def execute(self, context):
        return self.import_gltf2(context)

    def import_gltf2(self, context):
        bpy.context.scene.render.engine = 'CYCLES'
        self.gltf_importer = glTFImporter(self.filepath, self.loglevel)
        success, txt = self.gltf_importer.read()
        if not success:
            self.report({'ERROR'}, txt)
            return {'CANCELLED'}
        self.gltf_importer.log.critical("Data are loaded, start creating Blender stuff")
        BlenderGlTF.create(self.gltf_importer)
        self.gltf_importer.log.critical("glTF import is now finished")
        self.gltf_importer.log.removeHandler(self.gltf.log_handler)

        # Switch to newly created main scene
        bpy.context.screen.scene = bpy.data.scenes[self.gltf.blender_scene]

        return {'FINISHED'}


def menu_func_import(self, context):
    self.layout.operator(ImportglTF2.bl_idname, text=ImportglTF2.bl_label)


def register():
    bpy.utils.register_module(__name__)

    bpy.types.INFO_MT_file_export.append(menu_func_export_gltf)
    bpy.types.INFO_MT_file_export.append(menu_func_export_glb)

    bpy.types.INFO_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_module(__name__)

    bpy.types.INFO_MT_file_export.remove(menu_func_export_gltf)
    bpy.types.INFO_MT_file_export.remove(menu_func_export_glb)

    bpy.types.INFO_MT_file_import.remove(menu_func_import)
