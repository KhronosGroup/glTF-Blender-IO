import argparse
import shutil
import os

GLTF_ROOT = "/home/julien/glTF-Blender-IO/"
BLENDER_ROOT = "/home/julien/blender-git/blender/"

tests = [
    ("tests/roundtrip/", "roundtrip/"),
    ("tests/scenes/", "export")
]

# Retrieve the branch name from the command line arguments
parser = argparse.ArgumentParser(description='Run glTF-Blender-IO tests on Blender.')
parser.add_argument('--branch', type=str, required=True, help='The name of the branch to test against.')
args = parser.parse_args()
branch_name = args.branch

# Make sure we are on the main branch of the blender repository & the glTF-Blender-IO repository
os.system(f"cd {GLTF_ROOT} && git checkout main")

# Copy all tests from the glTF-Blender-IO repository to the Blender repository
for test in tests:
    src = os.path.join(GLTF_ROOT, test[0])
    dst = os.path.join(BLENDER_ROOT, "tests", "files", "io_tests", "gltf", test[1], "all")
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)

# Then, run the tests on Blender
build_dir = os.path.join(BLENDER_ROOT, "../build_linux")
# Go to the build_dir, and then launch "ctest -R gltf"
# Because all these files will not have the reference, pass the env var to
# create the reference files instead of comparing with them
os.environ["BLENDER_TEST_UPDATE"] = "1"
os.chdir(build_dir)
os.system("ctest -R gltf --output-on-failure")
os.environ["BLENDER_TEST_UPDATE"] = "0"

# And now, switch to branches on glTF-Blender-IO
os.system(f"cd {GLTF_ROOT} && git checkout {branch_name}")

# We can run the tests again, to compare with the reference files, that was generated from main
os.chdir(build_dir)
os.system("ctest -R gltf --output-on-failure")

# Now, delete the `all` folders
for test in tests:
    dst = os.path.join(BLENDER_ROOT, "tests", "files", "io_tests", "gltf", test[1], "all")
    if os.path.exists(dst):
        shutil.rmtree(dst)

# The, clean git by launching "git clean -f" & "git checkout ."
os.system(f"cd {BLENDER_ROOT} && git clean -f && git checkout .")

# And go back to the main branch of the glTF-Blender-IO repository
os.system(f"cd {GLTF_ROOT} && git checkout main")
