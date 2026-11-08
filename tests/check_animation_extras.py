"""Check user-approved synthetic extras on existing upstream animation assets.

Run with Blender --background --python-exit-code 1 --python this_file --
SOURCE_ROOT OUTPUT_DIRECTORY. No source asset is overwritten.
"""

import json
import importlib.util
import os
from pathlib import Path
import sys

import bpy


source, output = map(Path, sys.argv[sys.argv.index("--") + 1:])
sys.path.insert(0, str(source / "addons"))
import addon_utils

addon_utils.disable("io_scene_gltf2", default_set=False)
for module in list(sys.modules):
    if module == "io_scene_gltf2" or module.startswith("io_scene_gltf2."):
        del sys.modules[module]
spec = importlib.util.spec_from_file_location(
    "io_scene_gltf2", source / "addons" / "io_scene_gltf2" / "__init__.py")
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
addon_utils.enable("io_scene_gltf2", default_set=False)
import io_scene_gltf2

assert Path(io_scene_gltf2.__file__).resolve().is_relative_to(source.resolve())
output.mkdir(parents=True, exist_ok=True)
failures = []
for fixture in ("03_all_animations", "24_animation_pointer"):
    original = source / "tests" / "roundtrip" / fixture / (fixture + ".gltf")
    document = json.loads(original.read_text())
    expected = {}
    for index, animation in enumerate(document["animations"]):
        extras = {"synthetic_fixture": True, "label": animation["name"],
                  "index": index, "nested": {"enabled": True}, "values": [1, 2, 3]}
        animation["extras"] = extras
        expected[animation["name"]] = extras
    for buffer in document.get("buffers", []):
        if "uri" in buffer and not buffer["uri"].startswith("data:"):
            buffer["uri"] = os.path.relpath(original.parent / buffer["uri"], output)
    for image in document.get("images", []):
        if "uri" in image and not image["uri"].startswith("data:"):
            image["uri"] = os.path.relpath(original.parent / image["uri"], output)
    fixture_path = output / (fixture + "_synthetic.gltf")
    fixture_path.write_text(json.dumps(document, indent=2) + "\n")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(fixture_path))
    for name, extras in expected.items():
        action = bpy.data.actions.get(name)
        actual = action.id_properties_ensure().to_dict() if action else None
        passed = actual == extras
        print("IMPORT", fixture, name, "PASS" if passed else "FAIL", actual)
        if not passed:
            failures.append((fixture, name, actual))
    if fixture == "24_animation_pointer":
        continue
    result_path = output / (fixture + "_roundtrip.gltf")
    bpy.ops.export_scene.gltf(filepath=str(result_path), export_format="GLTF_SEPARATE",
                             export_extras=True, export_animation_mode="ACTIONS",
                             export_pointer_animation=False)
    exported = json.loads(result_path.read_text())
    actual = {a["name"]: a.get("extras") for a in exported.get("animations", [])}
    for name, extras in expected.items():
        passed = actual.get(name) == extras
        print("ROUNDTRIP", fixture, name, "PASS" if passed else "FAIL")
        if not passed:
            failures.append((fixture, name, "roundtrip"))
assert not failures, failures
print("PASS: ordinary and pointer import; ordinary animation round-trip")
