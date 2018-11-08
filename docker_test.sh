#!/bin/sh
#
# Copyright (c) 2018 The Khronos Group Inc.
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

command=test
if [[ $1 == "--bail" ]]
then
	command=test-bail
fi

docker build -t gltf-io-test -f Dockerfile.tests .

# TODO: find a more elegant way to do this
docker run -t gltf-io-test npm run $command
ID=$(docker ps -l -q)
docker cp $ID:/tests/mochawesome-report/ . 
docker cp $ID:/tests/scenes/ .
docker cp $ID:/tests/roundtrip/ .
docker rm $ID
