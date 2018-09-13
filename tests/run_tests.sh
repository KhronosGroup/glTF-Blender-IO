#!/bin/sh

blender -b --addons io_scene_gltf2 -noaudio scenes/01_cube.blend --python export_gltf.py
gltf_validator scenes/01_cube.gltf
blender -b --addons io_scene_gltf2 -noaudio --python import_gltf.py -- scenes/01_cube.gltf
