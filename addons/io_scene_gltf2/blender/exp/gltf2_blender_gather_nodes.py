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


from io_scene_gltf2.blender.exp.gltf2_blender_gather import cached
from io_scene_gltf2.blender.exp import gltf2_blender_extract
from io_scene_gltf2.io.com import gltf2_io


@cached
def __gather_node(blender_object, export_settings):
    node = gltf2_io.Node(
        camera=None,
        children=[],
        extensions={},
        extras=None,
        matrix=[],
        mesh=None,
        name=None,
        rotation=None,
        scale=None,
        skin=None,
        translation=None,
        weights=None
    )
    node.camera=__gather_camera(blender_object)
    node.children = __gather_children(blender_object)
    node.extensions = __gather_extensions(blender_object)
    node.extras = __gather_extras(blender_object)
    node.matrix = __gather_matrix(blender_object)
    node.mesh = __gather_mesh(blender_object)
    node.name = blender_object.name
    node.translation, node.rotation, node.scale = __gather_trans_rot_scale(blender_object)
    node.skin = __gather_skin(blender_object)
    node.weights = __gather_weights(blender_object)


def __gather_camera(blender_object, export_settings):
    return None


def __gather_children(blender_object, export_settings):
    children = []
    for child_object in blender_object.children:
        children.append(__gather_node(child_object))
    return children


def __gather_extensions(blender_object, export_settings):
    return {}


def __gather_extras(blender_object, export_settings):
    return None


def __gather_matrix(blender_object, export_settings):
    return []


def __gather_mesh(blender_object, export_settings):
    if blender_object.layers[0] or for
    return None


def __gather_trans_rot_scale(blender_object):
    return gltf2_blender_extract.decompose_transition(blender_object.matrix_local, 'NODE', None)


def __gather_skin(blender_object, export_settings):
    return None


def __gather_weights(blender_object, export_settings):
    return None