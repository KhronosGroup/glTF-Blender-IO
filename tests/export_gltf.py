import bpy
import os

bpy.ops.export_scene.gltf(filepath=os.path.splitext(bpy.data.filepath)[0] + ".gltf")
