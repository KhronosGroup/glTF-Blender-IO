#!/bin/sh

docker build -t gltf-io-test -f Dockerfile.tests .

# TODO: find a more elegant way to do this
docker run -t gltf-io-test npm test
ID=$(docker ps -l -q)
docker cp $ID:/tests/mochawesome-report/ . 
docker rm $ID
