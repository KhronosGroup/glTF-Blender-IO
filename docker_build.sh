#!/bin/sh

docker build -t blender-gltf-testenv -f Dockerfile.testenv .
docker build -t gltf-io-test -f Dockerfile.tests tests
