# Copyright 2018 The glTF-Blender-IO authors.
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

import typing


def chunks(lst: typing.Sequence[typing.Any], n: int) -> typing.List[typing.Any]:
    """
    Generator that yields successive n sized chunks of the list l
    :param lst: the list to be split
    :param n: the length of the chunks
    :return: a sublist of at most length n
    """
    result = []
    for i in range(0, len(lst), n):
        result.append(lst[i:i + n])
    return result


def unzip(*args: typing.Iterable[typing.Any]) -> typing.Iterable[typing.Iterable[typing.Any]]:
    """
    Unzip the list. Inverse of the builtin zip
    :param args: a list of lists or multiple list arguments
    :return: a list of unzipped lists
    """
    if len(args) == 1:
        args = args[0]

    return zip(*args)
