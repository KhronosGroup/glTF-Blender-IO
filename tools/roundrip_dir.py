from pathlib import Path
import argparse
from subprocess import run

ap = argparse.ArgumentParser()
ap.add_argument("-i", "--input", required=True, help="Input Dir")
ap.add_argument("-o", "--output", required=True, help="Output Dir")
ap.add_argument("-b", "--blender", required=True, help="Blender exe path")
ap.add_argument("-l", "--logfile", required=True, help="Log file dir")
args = vars(ap.parse_args())

files = []
for path in Path(args['input']).rglob('*.gltf'):
    files.append(path)
for path in Path(args['input']).rglob('*.glb'):
    files.append(path)

command = "{} -b --addons io_scene_gltf2 -noaudio --python ../tests/roundtrip_gltf.py -- \"{}\" {} {}".format(args['blender'], "{}", args['output'], "")



with open(args['logfile'], "w") as f:
    f.write("roundtrip {} file(s)\n".format(len(files)))

for file in files:
    try:
        command = [
            args['blender'],
            '-b',
            '--addons',
            'io_scene_gltf2',
            '-noaudio',
            '--python',
            '../tests/roundtrip_gltf.py',
            '--',
            file,
            args['output']
        ]
        run(command, check=True)
    except Exception as e:
        with open(args['logfile'], "a") as f:
            f.write(str(file) + "\n")
            f.write(str(e) + "\n")