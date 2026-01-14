# Copyright 2018-2022 The glTF-Blender-IO authors.
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

# This script is used to copy this repository to blender code repository

import sys
from os import walk, makedirs, remove
import argparse
from os.path import dirname, realpath, isdir, splitext, join, isfile
from shutil import copyfile
from subprocess import run

autopep8_args = [
    "/home/julien/blender-git/blender/lib/linux_x64/python/bin/python3.11",
    "/home/julien/blender-git/blender/lib/linux_x64/python/lib/python3.11/site-packages/autopep8.py",
    "--in-place",
    "--recursive"
]


ap = argparse.ArgumentParser()
ap.add_argument("-r", "--repo", required=False, help="repo path")
ap.add_argument("-b", "--bump", required=False, action="store_true", help="bump to +1 minor version number")
ap.add_argument("-w", "--rewrite", required=False, action="store_true", help="rewrite SPDX license identifiers")
ap.add_argument("-o", "--rewriteold", required=False, action="store_true",
                help="rewrite SPDX license identifiers before 4.0")
args = vars(ap.parse_args())

root = dirname(realpath(__file__))
INPUT = root + "/../addons/"

# Apply autopep8 before copying
autopep8_args.append(INPUT)
print("Applying autopep8...")
run(autopep8_args)

print("Bumping version...")
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

                    new_line = "    \"version\": (" + versions[0] + "," + \
                        versions[1] + ", " + str(int(versions[2]) + 1) + "),"
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

# Copy it on blender repo
print("Copying files...")
if args["repo"] is not None:
    if args["repo"][-1] != "/":
        args["repo"] += "/"

    for root, dirs, files in walk(INPUT):
        new_dir = args["repo"] + root[len(INPUT):]

        if not isdir(new_dir):
            makedirs(new_dir)

        for file in files:
            filename, fileext = splitext(file)
            if fileext != ".py":
                continue

            if args["rewrite"] is False and args['rewriteold'] is False:
                copyfile(root + "/" + file, new_dir + "/" + file)
            else:
                start_of_file = True
                with open(root + "/" + file, "r") as fr:
                    with open(new_dir + "/" + file, 'w') as fw:
                        if args['rewriteold'] is True:
                            fw.write("# SPDX-License-Identifier: Apache-2.0\n")
                        for idx, l in enumerate(fr.readlines()):
                            if args['rewrite'] is True:
                                if idx == 0:
                                    txt = l[12:-2]  # remove Copyright word (and point at end of line)
                                    txt = "# SPDX-FileCopyrightText: " + txt + "\n"
                                    fw.write(txt)
                                elif idx == 1:
                                    fw.write(l)
                                elif idx == 2:
                                    fw.write("# SPDX-License-Identifier: Apache-2.0\n")
                                else:
                                    if start_of_file is True and l[0] == "#":
                                        continue
                                    elif start_of_file is True and l[0] != "#":
                                        start_of_file = False

                                    if start_of_file is False:
                                        fw.write(l)
                            elif args['rewriteold'] is True:
                                if idx == 0:
                                    fw.write(l)
                                else:
                                    if start_of_file is True and l[0] == "#":
                                        continue
                                    elif start_of_file is True and l[0] != "#":
                                        start_of_file = False

                                    if start_of_file is False:
                                        fw.write(l)

    # Check that files removed are also removed in blender repo
    for root, dirs, files in walk(join(args["repo"], "io_scene_gltf2")):
        for file in files:
            if not isfile(join(INPUT, join(root[len(args["repo"]):], file))):
                print(join(root[len(args["repo"]):], file))
                remove(join(args["repo"], join(root[len(args["repo"]):], file)))
