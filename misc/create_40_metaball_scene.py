"""Create a minimal metaball scene for glTF export tests (issue #2726)."""
import bpy
from pathlib import Path

out = Path(__file__).resolve().parents[1] / "tests" / "scenes" / "40_metaball.blend"

# Clear default scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Default metaball ball
bpy.ops.object.metaball_add(type='BALL', enter_editmode=False, align='WORLD', location=(0, 0, 0))
obj = bpy.context.active_object
assert obj is not None and obj.type == 'META', f"expected META, got {obj}"

# Ensure only this object remains
for o in list(bpy.data.objects):
    if o != obj:
        bpy.data.objects.remove(o, do_unlink=True)

out.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(out))
print(f"Saved {out}")
print(f"Object: {obj.name} type={obj.type}")
