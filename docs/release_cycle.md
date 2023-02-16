# Repositories

- This repository, called _Khronos repo_ : [glTF-Blender-IO](https://github.com/KhronosGroup/glTF-Blender-IO)
- Blender addon repository, called _Blender repo_ : [blender-addons](https://projects.blender.org/blender/blender-addons)

# Release Cycle

This addon follow the [Blender release cycle](https://wiki.blender.org/wiki/Process/Release_Cycle).

# How to manage branches before and after Bcon3

- From Bcon1 to Bcon3:
    - Branches:
        - stable version is blender-vX.Y-release
        - main branch is future next stable version X.Y+1 (or X+1.0)
    - How to commit
        - You can push commit to main branch

- From Bcon3 to release
    - Branches:
        - stable version is blender-vX.Y-release
        - main branch is future stable version X.Y+2 (or X+1.1)
        - future next stable is blender-vX.Y+1 (or blender-vX+1.0)

# To be perform at Bcon3

- update README.md to change versions
    - main branch => update the version
    - add new line with next stable release
- on your local clone of _Blender repo_, pull newly created branch
- Create new branch (blender-vX.Y+1-release), and push this branch
- on main branch of _Khronos repo_, bump version number to the new version, commit, push
- copy this change to main branch of _Blender repo_ (see details bellow)
- update version test config file : ci.yml

# How to commit from bcon3 to release

- _Khronos repo_ : git checkout blender-vX.Y-release
- (Merge PR from github + git pull) or (commit + push) on blender-vX.Y-release
- git pull _Blender repo_
- _Blender repo_: git checkout blender-vX.Y-release
- python tools/copy_repo -r /path/blender_repo/source/release/addons -b -w
- _Blender repo_: git add . ; git commit ; git push
- _Blender repo_: git checkout main ; git merge blender-vX.Y-release
- _Blender repo_: fix merge error (bump version on main) ; git push
- _Khronos repo_: git add . ; git commit (Bump version)
- _Khronos repo_: git checkout main ; git merge blender-vX.Y-release
- _Khronos repo_: fix merge error (bump version on main) ; git push


# At release

TODO

# Corrective release / LTS

TODO
