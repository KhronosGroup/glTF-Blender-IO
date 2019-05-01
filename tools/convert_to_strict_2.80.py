# This file generate code for >=2.80 version of blender
# Without any check to version
# That means:
#   Delete all code relative to <= 2.79
#   Replace operator class properties to annotations

# In order to work, this script assumes that:
# - any version check is done with 'if bpy.app.version < (2, 80, 0):',
#   and 2.80 code is in 'else'
# - any properties is declare with:
#   - ' = ' just before
#   - '(' just after
#   For example 'test = BoolProperty()'

# You can use -r to copy newly created file into another directory
# Example:
# convert_to_strict_2.80.py -r /home/<user>/blender-git/blender/release/scripts/addons/

from os import walk, makedirs
import argparse
from os.path import realpath, dirname, isdir, splitext, exists, isfile
from shutil import copyfile
import sys

ap = argparse.ArgumentParser()
ap.add_argument("-r", "--repo", required=False, help="repo path")
ap.add_argument("-b", "--bump", required=False, action="store_true", help="bump to +1 minor version number")
args = vars(ap.parse_args())


root = dirname(realpath(__file__))
INPUT = root + "/../addons/"
OUTPUT = root + "/../2.80/"

properties = [
    'CollectionProperty',
    'StringProperty',
    'BoolProperty',
    'EnumProperty',
    'FloatProperty',
    'IntProperty'
]

if not isdir(OUTPUT):
    makedirs(OUTPUT)

# On glTF-Blender-IO repo, increase version number if needed
if args["bump"] is True:
    if args["repo"] is None:
        print("You can't bump to new version if --repo is not set")
        sys.exit()

    if args["repo"][-1] != "/":
        args["repo"] += "/"

    init_file = INPUT + "io_scene_gltf2/__init__.py"
    if not isfile(init_file):
        print("Can't find __init__ file")
        sys.exit()

    data = ""
    new_line = ""
    with open(init_file, "r") as f_read:
        data = f_read.read()

        for l in data.split("\n"):
            if "\"version\"" in l:
                try:
                    versions = l.split('(')[1].split(')')[0].split(',')
                    if len(versions) != 3:
                        print("Can't find version properly")
                        sys.exit()

                    new_line = "    \"version\": (" + versions[0] + "," + versions[1] + ", " + str(int(versions[2]) + 1) + "),"
                    break
                except:
                    print("Can't find version")
                    sys.exit()

    with open(init_file, "w") as f_write:
        for idx, l in enumerate(data.split("\n")):
            if "\"version\"" in l:
                f_write.write(new_line + "\n")
            else:
                if idx == len(data.split("\n")) - 1:
                    f_write.write(l)
                else:
                    f_write.write(l + "\n")

# Create 2.80 version of files
for root, dirs, files in walk(INPUT):
    new_dir = root[len(INPUT):]

    for file in files:
        filename, fileext = splitext(file)
        if fileext != ".py":
            continue

        with open(root + "/" + file) as f_input:
            data = f_input.read()
            tab_ = data.split("\n")

            if not exists(dirname(OUTPUT + new_dir + "/" + file)):
                makedirs(dirname(OUTPUT + new_dir + "/" + file))

            with open(OUTPUT + new_dir + "/" + file, "w") as f_output:

                erase_mode = False
                mode = "IF"

                for idx_line, line in enumerate(tab_):


                    if erase_mode is True:

                        # check if indentation of version check is finished or not
                        current_nb_spaces = len(line) - len(line.lstrip(' '))
                        if current_nb_spaces == nb_spaces:
                            # check if we have an else
                            if 'else:' in line:
                                else_mode = "ELSE"
                                # Do not write 'else:' line
                            else:
                                # else is now finished

                                # but we have first to check if we start a new IF
                                if "bpy.app.version" in line:
                                    # get indentation of the line
                                    nb_spaces = len(line) - len(line.lstrip(' '))
                                    erase_mode = True
                                    else_mode = "IF"
                                else:
                                    erase_mode = False
                                    mode = "IF"
                                    last_line = line
                                    f_output.write(line + "\n")

                        elif current_nb_spaces < nb_spaces:
                            if len(line) != 0:
                                # erase mode is finished
                                # 2 cases: else is finished, or there is no else
                                erase_mode = False
                                mode = "IF"
                            if idx_line != len(tab_)-1:
                                last_line = line
                                f_output.write(line + "\n")
                            elif idx_line == len(tab_)-1 and line != "":
                                last_line = line
                                f_output.write(line + "\n")
                        else:
                            if else_mode == "ELSE":
                                # write line, but remove 1 indentation level
                                last_line = line
                                f_output.write(line[4:] + "\n")

                    else:

                        # check if contains a check on version
                        if "bpy.app.version" in line:
                            # get indentation of the line
                            nb_spaces = len(line) - len(line.lstrip(' '))
                            erase_mode = True
                            else_mode = "IF"
                        else:
                            # check if this is a property definition
                            for prop in properties:
                                if line.find(prop) != -1:
                                    # do not change import declaration
                                    if line[line.find(prop)+len(prop)] != "(":
                                        break
                                    line = line[:line.find(prop)-3] + ": " + line[line.find(prop):]
                                    break
                            # Write line
                            last_line = line
                            f_output.write(line + "\n")

                if last_line != "":
                    f_output.write("\n")
                    pass

# Now that files are written in 2.80 dir, copy it on blender repo if needed
if args["repo"] is not None:

    if args["repo"][-1] != "/":
        args["repo"] += "/"

    for root, dirs, files in walk(OUTPUT):
        new_dir = args["repo"] + root[len(OUTPUT):]

        if not isdir(new_dir):
            makedirs(new_dir)

        for file in files:
            filename, fileext = splitext(file)
            if fileext != ".py":
                continue

            copyfile(root + "/" + file, new_dir + "/" + file)
