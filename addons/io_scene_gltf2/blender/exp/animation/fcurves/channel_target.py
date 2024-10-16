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

import bpy
import typing
from .....io.com import gltf2_io
from .....io.exp.user_extensions import export_user_extensions
from ....com.conversion import get_target
from ...cache import cached
from ...joints import gather_joint_vnode


@cached
def gather_fcurve_channel_target(
        obj_uuid: str,
        channels: typing.Tuple[bpy.types.FCurve],
        bone: typing.Optional[str],
        export_settings
) -> gltf2_io.AnimationChannelTarget:

    animation_channel_target = gltf2_io.AnimationChannelTarget(
        extensions=None,
        extras=None,
        node=__gather_node(obj_uuid, bone, export_settings),
        path=__gather_path(channels, export_settings)
    )

    blender_object = export_settings['vtree'].nodes[obj_uuid].blender_object
    export_user_extensions('animation_gather_fcurve_channel_target', export_settings, blender_object, bone)

    return animation_channel_target


def __gather_node(obj_uuid: str,
                  bone: typing.Union[str, None],
                  export_settings
                  ) -> gltf2_io.Node:

    if bone is not None:
        return gather_joint_vnode(export_settings['vtree'].nodes[obj_uuid].bones[bone], export_settings)
    else:
        return export_settings['vtree'].nodes[obj_uuid].node


def __gather_path(channels: typing.Tuple[bpy.types.FCurve],
                  export_settings
                  ) -> str:

    # Note: channels has some None items only for SK if some SK are not animated, so keep a not None channel item
    target = [c for c in channels if c is not None][0].data_path.split('.')[-1]

    return get_target(target)
