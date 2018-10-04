import bpy
import os
import sys

try:
    bpy.ops.export_scene.gltf(filepath=os.path.splitext(bpy.data.filepath)[0] + ".gltf", export_experimental=True)
except Exception as err:
    sys.exit(1)
