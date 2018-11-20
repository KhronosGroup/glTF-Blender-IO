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

from os import walk, makedirs
from os.path import realpath, dirname, isdir, splitext, exists

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

                for line in tab_:


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
                                erase_mode = False
                                mode = "IF"
                                f_output.write(line + "\n")

                        elif current_nb_spaces < nb_spaces:
                            if len(line) != 0:
                                # erase mode is finished
                                # 2 cases: else is finished, or there is no else
                                erase_mode = False
                                mode = "IF"
                            f_output.write(line + "\n")
                        else:
                            if else_mode == "ELSE":
                                # write line, but remove 1 indentation level
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
                            f_output.write(line + "\n")
