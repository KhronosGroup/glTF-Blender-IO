# Copyright 2018-2021 The glTF-Blender-IO authors.
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

# This file copy documentation into local svn repo
# in order to update online doc on blender server
# Example:
# copy_doc -r /home/<user>/blender_docs/

import argparse
import shutil
from os.path import isfile, isdir, dirname, realpath
from os import listdir

ap = argparse.ArgumentParser()
ap.add_argument("-r", "--repo", required=True, help="repo path")
args = vars(ap.parse_args())

doc = dirname(realpath(__file__)) + "/../docs/blender_docs/scene_gltf2.rst"
images = dirname(realpath(__file__)) + "/../images/"

if not isdir(args["repo"]):
    import sys
    sys.exit()

shutil.copy(doc, args["repo"] + "/manual/addons/import_export/scene_gltf2.rst")

images_list = listdir(images)
for img in images_list:
    if not isfile(images + img):
        continue
    shutil.copy(images + img, args["repo"] + "/manual/images/" + img)
