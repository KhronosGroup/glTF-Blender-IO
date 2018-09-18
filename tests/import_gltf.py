import bpy
import sys

try:
    argv = sys.argv
    argv = argv[argv.index("--") + 1:]  # get all args after "--"

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=argv[0])
except Exception as err:
    sys.exit(1)
