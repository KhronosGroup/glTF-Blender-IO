// Copyright 2018-2021 The Khronos Group Inc.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

const fs = require('fs');
const path = require('path');
const validator = require('gltf-validator');

const OUT_PREFIX = process.env.OUT_PREFIX || '../tests_out';

const blenderVersions = [
    "blender"
];

const validator_info_keys = [
    'version',
    'animationCount',
    'materialCount',
    'hasMorphTargets',
    'hasSkins',
    'hasTextures',
    'hasDefaultScene',
    'drawCallCount',
    'totalTriangleCount',
    'maxUVs',
    'maxInfluences'
];

function blenderFileToGltf(blenderVersion, blenderPath, outDirName, done, options = '') {
    const { exec } = require('child_process');
    const cmd = `${blenderVersion} -b --addons io_scene_gltf2 -noaudio ${blenderPath} --python export_gltf.py -- ${outDirName} ${options}`;
    var prc = exec(cmd, (error, stdout, stderr) => {
        //if (stderr) process.stderr.write(stderr);

        if (error) {
            done(error);
            return;
        }
        done();
    });
}

function blenderRoundtripGltf(blenderVersion, gltfPath, outDirName, done, options = '') {
    const { exec } = require('child_process');
    const cmd = `${blenderVersion} -b --addons io_scene_gltf2 -noaudio --python roundtrip_gltf.py -- ${gltfPath} ${outDirName} ${options}`;
    var prc = exec(cmd, (error, stdout, stderr) => {
        //if (stderr) process.stderr.write(stderr);

        if (error) {
            done(error);
            return;
        }
        done();
    });
}

function validateGltf(gltfPath, done) {
    const asset = fs.readFileSync(gltfPath);
    validator.validateBytes(new Uint8Array(asset), {
        uri: gltfPath,
        externalResourceFunction: (uri) =>
            new Promise((resolve, reject) => {
                uri = path.resolve(path.dirname(gltfPath), decodeURIComponent(uri));
                // console.info("Loading external file: " + uri);
                fs.readFile(uri, (err, data) => {
                    if (err) {
                        console.error(err.toString());
                        reject(err.toString());
                        return;
                    }
                    resolve(data);
                });
            })
    }).then((result) => {
        // [result] will contain validation report in object form.
        if (result.issues.numErrors > 0) {
            const errors = result.issues.messages.filter(i => i.severity === 0)
                .reduce((msg, i, idx) => (idx > 5) ? msg : `${msg}\n${i.pointer} - ${i.message} (${i.code})`, '');
            done(new Error("Validation failed for " + gltfPath + '\nFirst few messages:' + errors), result);
            return;
        }
        done(null, result);
    }, (result) => {
        // Promise rejection means that arguments were invalid or validator was unable
        // to detect file format (glTF or GLB).
        // [result] will contain exception string.
        done(result);
    });
}

var assert = require('assert');

// This tests floating-point numbers for equality, ignoring roundoff errors.
assert.equalEpsilon = function (actual, expected) {
    if (typeof actual !== 'number') {
        throw new Error("Expected " + actual + " to be a number.");
    }
    let epsilon = 1e-6;
    epsilon = Math.max(epsilon, Math.abs(expected * epsilon));
    if (Math.abs(actual - expected) > epsilon) {
        throw new Error("Expected " + actual + " to equal " + expected);
    }
};

assert.equalEpsilonArray = function (actual, expected) {
    const length = expected.length;
    assert.strictEqual(actual.length, length);

    for (let i = 0; i < length; ++i) {
        assert.equalEpsilon(actual[i], expected[i]);
    }
};

function getAccessorData(gltfPath, asset, accessorIndex, bufferCache) {
    // This is only for testing exporter output, it does not handle enough
    // cases to parse arbitrary glTF files from outside this test suite.

    const accessor = asset.accessors[accessorIndex];
    const bufferView = asset.bufferViews[accessor.bufferView];
    const bufferIndex = bufferView.buffer;
    let bufferData;
    if (bufferCache[bufferIndex] !== undefined) {
        bufferData = bufferCache[bufferIndex];
    } else {
        const buffer = asset.buffers[bufferIndex];
        const binPath = path.resolve(gltfPath, '../' + buffer.uri);
        bufferData = fs.readFileSync(binPath);
        bufferCache[bufferIndex] = bufferData;
    }

    const bufferViewByteOffset = bufferView.byteOffset || 0;
    const bufferViewData = bufferData.slice(bufferViewByteOffset, bufferViewByteOffset + bufferView.byteLength);

    let componentSize;
    switch (accessor.componentType) {
        case 5126:  // FLOAT
            componentSize = 4;
            break;
        case 5121:  // UNSIGNED_BYTE
            componentSize = 1;
            break;
        case 5123:  // UNSIGNED_SHORT
            componentSize = 2;
            break;
        default:
            throw new Error("Untested accessor componentType " + accessor.componentType);
    }

    let numElements;
    switch (accessor.type) {
        case 'SCALAR':
            numElements = 1;
            break;
        case 'VEC2':
            numElements = 2;
            break;
        case 'VEC3':
            numElements = 3;
            break;
        case 'VEC4':
            numElements = 4;
            break;
        default:
            throw new Error("Untested accessor type " + accessor.type);
    }

    const count = accessor.count;
    const stride = (bufferView.byteStride !== undefined) ? bufferView.byteStride : (componentSize * numElements);
    const byteOffset = accessor.byteOffset || 0;

    const accessorData = [];
    for (let i = 0, o = byteOffset; i < count; ++i, o += stride) {
        for (let j = 0; j < numElements; ++j) {
            switch (accessor.componentType) {
                case 5126:  // FLOAT
                    accessorData.push(bufferViewData.readFloatLE(o + (j * componentSize)));
                    break;
                case 5121:  // UNSIGNED_BYTE
                    accessorData.push(bufferViewData.readUInt8(o + j * componentSize));
                    break;
                case 5123:  // UNSIGNED_SHORT
                    accessorData.push(bufferViewData.readUInt16LE(o + j * componentSize));
                    break;
                default:
                    throw new Error("Untested accessor componentType " + accessor.componentType);
            }
        }
    }
    return accessorData;
}

function buildVectorHash(accessorData) {
    // Vertex order is not preserved by this exporter, but, we can build a hash table of all the vectors we
    // expect to find in the test output, to see if they are all accounted for.

    let vectorHashTable = {};
    const dataLen = accessorData.length;
    if ((dataLen % 3) !== 0) {
        throw new Error("Expected accessor length " + dataLen);
    }

    const precision = 3;
    const count = dataLen / 3;
    for (let i = 0; i < count; ++i) {
        const index = i * 3;
        let key = accessorData[index].toFixed(precision) + ',' + accessorData[index + 1].toFixed(precision) +
            ',' + accessorData[index + 2].toFixed(precision);

        key = key.replace(/-0\.000/g, '0.000');

        if (Object.prototype.hasOwnProperty.call(vectorHashTable, key)) {
            ++vectorHashTable[key];
        } else {
            vectorHashTable[key] = 1;
        }
    }

    return vectorHashTable;
}

describe('General', function () {
    describe('gltf_validator', function () {
        it('should verify a simple glTF file without errors', function (done) {
            validateGltf('gltf/Box.gltf', done);
        });
        it('should verify a simple glTF binary file without errors', function (done) {
            validateGltf('gltf/Box.glb', done);
        });
    });
});

describe('Exporter', function () {
    let blenderSampleScenes = fs.readdirSync('scenes').filter(f => f.endsWith('.blend')).map(f => f.substring(0, f.length - 6));

    blenderVersions.forEach(function (blenderVersion) {
        let variants = [
            ['', ''],
            ['_glb', '--glb']
        ];

        variants.forEach(function (variant) {
            const args = variant[1];
            describe(blenderVersion + '_export' + variant[0], function () {
                blenderSampleScenes.forEach((scene) => {
                    it(scene, function (done) {
                        let outDirName = 'out' + blenderVersion + variant[0];
                        let blenderPath = `scenes/${scene}.blend`;
                        let ext = args.indexOf('--glb') === -1 ? '.gltf' : '.glb';
                        let outDirPath = path.resolve(OUT_PREFIX, 'scenes', outDirName);
                        let dstPath = path.resolve(outDirPath, `${scene}${ext}`);
                        blenderFileToGltf(blenderVersion, blenderPath, outDirPath, (error) => {
                            if (error)
                                return done(error);

                            // tmp: skip validator if the name of file contains "pointer"
                            if (!(scene.includes("pointer"))) {
                                validateGltf(dstPath, done);
                            } else {
                                done();
                            }
                        }, args);
                        //validateGltf(dstPath, done); // uncomment this and comment blenderFileToGltf to not re-export all files
                    });
                });
            });
        });

        describe(blenderVersion + '_export_results', function () {
            let outDirName = 'out' + blenderVersion;
            let outDirPath = path.resolve(OUT_PREFIX, 'scenes', outDirName);

            it('can export a base color', function () {
                let gltfPath = path.resolve(outDirPath, '01_principled_material.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));

                assert.strictEqual(asset.materials.length, 1);
                const textureIndex = asset.materials[0].pbrMetallicRoughness.baseColorTexture.index;
                const imageIndex = asset.textures[textureIndex].source;

                assert.strictEqual(asset.images[imageIndex].uri, '01_principled_baseColor.png');
                assert(fs.existsSync(path.resolve(outDirPath, '01_principled_baseColor.png')));
            });

            it('can export a normal map', function () {
                let gltfPath = path.resolve(outDirPath, '01_principled_material.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));

                assert.strictEqual(asset.materials.length, 1);
                const textureIndex = asset.materials[0].normalTexture.index;
                const imageIndex = asset.textures[textureIndex].source;

                assert.strictEqual(asset.images[imageIndex].uri, '01_principled_normal.png');
                assert(fs.existsSync(path.resolve(outDirPath, '01_principled_normal.png')));
            });

            it('can export an emissive map from the Emission node', function () {
                let gltfPath = path.resolve(outDirPath, '01_principled_material.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));

                assert.strictEqual(asset.materials.length, 1);
                const textureIndex = asset.materials[0].emissiveTexture.index;
                const imageIndex = asset.textures[textureIndex].source;

                assert.strictEqual(asset.images[imageIndex].uri, '01_principled_emissive.png');
                assert.deepStrictEqual(asset.materials[0].emissiveFactor, [1, 1, 1]);
                assert(fs.existsSync(path.resolve(outDirPath, '01_principled_emissive.png')));
            });

            it('can export an emissive map from the Principled BSDF node', function () {
                let gltfPath = path.resolve(outDirPath, '01_principled_material_280.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));

                assert.strictEqual(asset.materials.length, 1);
                const textureIndex = asset.materials[0].emissiveTexture.index;
                const imageIndex = asset.textures[textureIndex].source;

                assert.strictEqual(asset.images[imageIndex].uri, '01_principled_emissive.png');
                assert.deepStrictEqual(asset.materials[0].emissiveFactor, [1, 1, 1]);
                assert(fs.existsSync(path.resolve(outDirPath, '01_principled_emissive.png')));
            });

            it('can create instances of a mesh with different materials', function () {
                let gltfPath = path.resolve(outDirPath, '02_material_instancing.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));

                assert.strictEqual(asset.meshes.length, 4);
                assert.strictEqual(asset.materials.length, 3);

                const materialRed = asset.materials.filter(m => m.name === 'MaterialRed')[0];
                const materialGreen = asset.materials.filter(m => m.name === 'MaterialGreen')[0];
                const materialBlue = asset.materials.filter(m => m.name === 'MaterialBlue')[0];

                const cubeRedMesh = asset.meshes[asset.nodes.filter(m => m.name === 'CubeRed')[0].mesh];
                const cubeGreenMesh = asset.meshes[asset.nodes.filter(m => m.name === 'CubeGreen')[0].mesh];
                const cubeBlueMesh = asset.meshes[asset.nodes.filter(m => m.name === 'CubeBlue')[0].mesh];
                const cubeNoMatMesh = asset.meshes[asset.nodes.filter(m => m.name === 'CubeNoMat')[0].mesh];

                // The "NoMat" mesh is a separate Blender mesh with no material defined.
                assert.strictEqual(cubeNoMatMesh.primitives.length, 1);
                assert.strictEqual(cubeNoMatMesh.primitives[0].material, undefined);

                // CubeRed, CubeGreen, and CubeBlue share a single Blender mesh, but have separate
                // materials.  This converts to glTF as separate meshes that share vertex attributes.
                assert.strictEqual(cubeRedMesh.primitives.length, 1);
                assert.strictEqual(cubeGreenMesh.primitives.length, 1);
                assert.strictEqual(cubeBlueMesh.primitives.length, 1);
                const cubeRedPrimitive = cubeRedMesh.primitives[0];
                const cubeGreenPrimitive = cubeGreenMesh.primitives[0];
                const cubeBluePrimitive = cubeBlueMesh.primitives[0];

                // Each glTF mesh is assigned a different material.
                assert.strictEqual(asset.materials[cubeRedPrimitive.material], materialRed);
                assert.strictEqual(asset.materials[cubeGreenPrimitive.material], materialGreen);
                assert.strictEqual(asset.materials[cubeBluePrimitive.material], materialBlue);

                // Sharing of vertex attributes indicates that mesh data has been successfully re-used.
                assert.strictEqual(cubeGreenPrimitive.indices, cubeRedPrimitive.indices);
                assert.strictEqual(cubeGreenPrimitive.attributes.POSITION, cubeRedPrimitive.attributes.POSITION);
                assert.strictEqual(cubeGreenPrimitive.attributes.NORMAL, cubeRedPrimitive.attributes.NORMAL);
                assert.strictEqual(cubeBluePrimitive.indices, cubeRedPrimitive.indices);
                assert.strictEqual(cubeBluePrimitive.attributes.POSITION, cubeRedPrimitive.attributes.POSITION);
                assert.strictEqual(cubeBluePrimitive.attributes.NORMAL, cubeRedPrimitive.attributes.NORMAL);
            });

            it('exports UNSIGNED_SHORT when count is 65535', function () {
                let gltfPath = path.resolve(outDirPath, '01_vertex_count_16bit.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));

                assert.strictEqual(asset.meshes.length, 1);
                assert.strictEqual(asset.meshes[0].primitives.length, 1);

                const primitive = asset.meshes[0].primitives[0];

                // There are 65535 vertices, numbered 0 to 65534, avoiding the
                // primitive restart value at 65535 (the highest 16-bit unsigned integer value).
                assert.strictEqual(asset.accessors[primitive.attributes.POSITION].count, 65535);

                // The indices componentType should be 5123 (UNSIGNED_SHORT).
                assert.strictEqual(asset.accessors[primitive.indices].componentType, 5123);
            });

            it('exports UNSIGNED_INT when count is 65536', function () {
                let gltfPath = path.resolve(outDirPath, '01_vertex_count_32bit.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));

                assert.strictEqual(asset.meshes.length, 1);
                assert.strictEqual(asset.meshes[0].primitives.length, 1);

                const primitive = asset.meshes[0].primitives[0];

                // There are 65536 vertices, numbered 0 to 65535.  Because of the primitive
                // restart value, 32-bit indicies are required at this point and beyond.
                assert.strictEqual(asset.accessors[primitive.attributes.POSITION].count, 65536);

                // The indices componentType should be 5125 (UNSIGNED_INT).
                assert.strictEqual(asset.accessors[primitive.indices].componentType, 5125);
            });

            // ORM tests, source images:
            // Occlusion: Black square in upper-left on white background, grayscale image
            // Roughness: Black square in upper-right on white background, grayscale image
            //  Metallic: Black square in lower-left on white background, grayscale image
            // When the texture is present, expect the factor to be undefined, and vice-versa

            it('produces a Roughness texture', function () {
                // Expect magenta (inverted green) square
                let resultName = path.resolve(outDirPath, '08_img_rough.png');
                let expectedRgbBuffer = fs.readFileSync('scenes/08_tiny-box-_g_.png');
                let testBuffer = fs.readFileSync(resultName);
                assert(testBuffer.equals(expectedRgbBuffer));
            });

            it('references the Roughness texture', function () {
                let gltfPath = path.resolve(outDirPath, '08_only_rough.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));

                assert.strictEqual(asset.materials.length, 1);
                assert.strictEqual(asset.materials[0].occlusionTexture, undefined);
                assert.strictEqual(asset.materials[0].pbrMetallicRoughness.metallicRoughnessTexture.index, 0);
                assert.strictEqual(asset.materials[0].pbrMetallicRoughness.roughnessFactor, undefined);
                assert.equalEpsilon(asset.materials[0].pbrMetallicRoughness.metallicFactor, 0.1);
                assert.strictEqual(asset.textures.length, 1);
                assert.strictEqual(asset.textures[0].source, 0);
                assert.strictEqual(asset.images.length, 1);
                assert.strictEqual(asset.images[0].uri, '08_img_rough.png');
            });

            it('produces a Metallic texture', function () {
                // Expect yellow (inverted blue) square
                let resultName = path.resolve(outDirPath, '08_img_metal.png');
                let expectedRgbBuffer = fs.readFileSync('scenes/08_tiny-box-__b.png');
                let testBuffer = fs.readFileSync(resultName);
                assert(testBuffer.equals(expectedRgbBuffer));
            });

            it('references the Metallic texture', function () {
                let gltfPath = path.resolve(outDirPath, '08_only_metal.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));

                assert.strictEqual(asset.materials.length, 1);
                assert.strictEqual(asset.materials[0].occlusionTexture, undefined);
                assert.strictEqual(asset.materials[0].pbrMetallicRoughness.metallicRoughnessTexture.index, 0);
                assert.equalEpsilon(asset.materials[0].pbrMetallicRoughness.roughnessFactor, 0.2);
                assert.strictEqual(asset.materials[0].pbrMetallicRoughness.metallicFactor, undefined);
                assert.strictEqual(asset.textures.length, 1);
                assert.strictEqual(asset.textures[0].source, 0);
                assert.strictEqual(asset.images.length, 1);
                assert.strictEqual(asset.images[0].uri, '08_img_metal.png');
            });

            it('combines two images into a RoughnessMetallic texture', function () {
                // Expect magenta (inverted green) and yellow (inverted blue) squares
                let resultName = path.resolve(outDirPath, '08_metallic-08_roughness.png');
                let expectedRgbBuffer = fs.readFileSync('scenes/08_tiny-box-_gb.png');
                let testBuffer = fs.readFileSync(resultName);
                assert(testBuffer.equals(expectedRgbBuffer));
            });

            it('references the RoughnessMetallic texture', function () {
                let gltfPath = path.resolve(outDirPath, '08_combine_roughMetal.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));

                assert.strictEqual(asset.materials.length, 1);
                assert.strictEqual(asset.materials[0].occlusionTexture, undefined);
                assert.strictEqual(asset.materials[0].pbrMetallicRoughness.metallicRoughnessTexture.index, 0);
                assert.strictEqual(asset.materials[0].pbrMetallicRoughness.roughnessFactor, undefined);
                assert.strictEqual(asset.materials[0].pbrMetallicRoughness.metallicFactor, undefined);
                assert.strictEqual(asset.textures.length, 1);
                assert.strictEqual(asset.textures[0].source, 0);
                assert.strictEqual(asset.images.length, 1);
                assert.strictEqual(asset.images[0].uri, '08_metallic-08_roughness.png');
            });

            it('produces an Occlusion texture', function () {
                // Expect upper-left black square.  This is a special case because when R/M are not
                // present, occlusion may take all channels.  This test now "expects" the
                // grayscale PNG to be preserved exactly.
                let resultName = path.resolve(outDirPath, '08_img_occlusion.png');
                let expectedRgbBuffer = fs.readFileSync('scenes/08_img_occlusion.png');
                let testBuffer = fs.readFileSync(resultName);
                assert(testBuffer.equals(expectedRgbBuffer));
            });

            it('references the Occlusion texture', function () {
                let gltfPath = path.resolve(outDirPath, '08_only_occlusion.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));

                assert.strictEqual(asset.materials.length, 1);
                assert.strictEqual(asset.materials[0].occlusionTexture.index, 0);
                assert.strictEqual(asset.materials[0].pbrMetallicRoughness.metallicRoughnessTexture, undefined);
                assert.equalEpsilon(asset.materials[0].pbrMetallicRoughness.roughnessFactor, 0.2);
                assert.equalEpsilon(asset.materials[0].pbrMetallicRoughness.metallicFactor, 0.1);
                assert.strictEqual(asset.textures.length, 1);
                assert.strictEqual(asset.textures[0].source, 0);
                assert.strictEqual(asset.images.length, 1);
                assert.strictEqual(asset.images[0].uri, '08_img_occlusion.png');
            });

            it('combines two images into an OcclusionRoughness texture', function () {
                // Expect cyan (inverted red) and magenta (inverted green) squares
                let resultName = path.resolve(outDirPath, '08_occlusion-08_roughness.png');
                let expectedRgbBuffer = fs.readFileSync('scenes/08_tiny-box-rg_.png');
                let testBuffer = fs.readFileSync(resultName);
                assert(testBuffer.equals(expectedRgbBuffer));
            });

            it('references the OcclusionRoughness texture', function () {
                let gltfPath = path.resolve(outDirPath, '08_combine_occlusionRough.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));

                assert.strictEqual(asset.materials.length, 1);
                assert.strictEqual(asset.materials[0].occlusionTexture.index, 0);
                assert.strictEqual(asset.materials[0].pbrMetallicRoughness.metallicRoughnessTexture.index, 0);
                assert.strictEqual(asset.materials[0].pbrMetallicRoughness.roughnessFactor, undefined);
                assert.equalEpsilon(asset.materials[0].pbrMetallicRoughness.metallicFactor, 0.1);
                assert.strictEqual(asset.textures.length, 1);
                assert.strictEqual(asset.textures[0].source, 0);
                assert.strictEqual(asset.images.length, 1);
                assert.strictEqual(asset.images[0].uri, '08_occlusion-08_roughness.png');
            });

            it('combines two images into an OcclusionMetallic texture', function () {
                // Expect cyan (inverted red) and yellow (inverted blue) squares
                let resultName = path.resolve(outDirPath, '08_occlusion-08_metallic.png');
                let expectedRgbBuffer = fs.readFileSync('scenes/08_tiny-box-r_b.png');
                let testBuffer = fs.readFileSync(resultName);
                assert(testBuffer.equals(expectedRgbBuffer));
            });

            it('references the OcclusionMetallic texture', function () {
                let gltfPath = path.resolve(outDirPath, '08_combine_occlusionMetal.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));

                assert.strictEqual(asset.materials.length, 1);
                assert.strictEqual(asset.materials[0].occlusionTexture.index, 0);
                assert.strictEqual(asset.materials[0].pbrMetallicRoughness.metallicRoughnessTexture.index, 0);
                assert.equalEpsilon(asset.materials[0].pbrMetallicRoughness.roughnessFactor, 0.2);
                assert.strictEqual(asset.materials[0].pbrMetallicRoughness.metallicFactor, undefined);
                assert.strictEqual(asset.textures.length, 1);
                assert.strictEqual(asset.textures[0].source, 0);
                assert.strictEqual(asset.images.length, 1);
                assert.strictEqual(asset.images[0].uri, '08_occlusion-08_metallic.png');
            });

            it('combines three images into an OcclusionRoughnessMetallic texture', function () {
                // Expect cyan (inverted red), magenta (inverted green), and yellow (inverted blue) squares
                let resultName = path.resolve(outDirPath, '08_occlusion-08_roughness-08_metallic.png');
                let expectedRgbBuffer = fs.readFileSync('scenes/08_tiny-box-rgb.png');
                let testBuffer = fs.readFileSync(resultName);
                assert(testBuffer.equals(expectedRgbBuffer));
            });

            it('references the OcclusionRoughnessMetallic texture', function () {
                let gltfPath = path.resolve(outDirPath, '08_combine_orm.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));

                assert.strictEqual(asset.materials.length, 1);
                assert.strictEqual(asset.materials[0].occlusionTexture.index, 0);
                assert.strictEqual(asset.materials[0].pbrMetallicRoughness.metallicRoughnessTexture.index, 0);
                assert.strictEqual(asset.materials[0].pbrMetallicRoughness.roughnessFactor, undefined);
                assert.strictEqual(asset.materials[0].pbrMetallicRoughness.metallicFactor, undefined);
                assert.strictEqual(asset.textures.length, 1);
                assert.strictEqual(asset.textures[0].source, 0);
                assert.strictEqual(asset.images.length, 1);
                assert.strictEqual(asset.images[0].uri, '08_occlusion-08_roughness-08_metallic.png');
            });

            it('can share a normal map and a Clearcoat normal map', function () {
                let gltfPath = path.resolve(outDirPath, '08_clearcoat.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));

                assert.strictEqual(asset.materials.length, 1);
                assert.strictEqual(asset.images.length, 1);
                const clearcoat = asset.materials[0].extensions.KHR_materials_clearcoat;
                assert.equalEpsilon(clearcoat.clearcoatFactor, 0.225);
                assert.equalEpsilon(clearcoat.clearcoatRoughnessFactor, 0.1);

                // Base normal map
                assert.strictEqual(asset.materials[0].normalTexture.scale, 2);
                const texture1 = asset.materials[0].normalTexture.index;
                const source1 = asset.textures[texture1].source;
                assert.strictEqual(asset.images[source1].uri, '08_normal_ribs.png');

                // Clearcoat normal map
                assert.strictEqual(clearcoat.clearcoatNormalTexture.scale, 2);
                const texture2 = clearcoat.clearcoatNormalTexture.index;
                const source2 = asset.textures[texture2].source;
                assert.strictEqual(source1, source2);
            });

            it('combines two images into a Clearcoat strength and roughness texture', function () {
                // Expect cyan (inverted red) and magenta (inverted green) squares
                let resultName = path.resolve(outDirPath, '08_cc_strength-08_cc_roughness.png');
                let expectedRgbBuffer = fs.readFileSync('scenes/08_tiny-box-rg_.png');
                let testBuffer = fs.readFileSync(resultName);
                assert(testBuffer.equals(expectedRgbBuffer));
            });

            it('references the Clearcoat texture', function () {
                let gltfPath = path.resolve(outDirPath, '08_combine_clearcoat.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));

                assert.strictEqual(asset.materials.length, 1);
                assert.strictEqual(asset.textures.length, 1);
                assert.strictEqual(asset.images.length, 1);
                const clearcoat = asset.materials[0].extensions.KHR_materials_clearcoat;
                assert.strictEqual(clearcoat.clearcoatFactor, 1);
                assert.strictEqual(clearcoat.clearcoatRoughnessFactor, 1);
                assert.strictEqual(clearcoat.clearcoatTexture.index, 0);
                assert.strictEqual(clearcoat.clearcoatRoughnessTexture.index, 0);
                assert.strictEqual(asset.textures[0].source, 0);
                assert.strictEqual(asset.images[0].uri, '08_cc_strength-08_cc_roughness.png');
            });

            it('exports texture transform from mapping type point', function () {
                let gltfPath = path.resolve(outDirPath, '09_tex_transform_from_point.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));

                assert.strictEqual(asset.materials.length, 1);
                const transform = asset.materials[0].pbrMetallicRoughness.baseColorTexture.extensions.KHR_texture_transform;

                assert.equalEpsilon(transform.rotation, 0.2617993950843811);
                assert.equalEpsilon(transform.scale[0], 2);
                assert.equalEpsilon(transform.scale[1], 3);
                assert.equalEpsilon(transform.offset[0], -0.2764571564185425);
                assert.equalEpsilon(transform.offset[1], -2.2977774791709993);
            });

            it('exports texture transform from mapping type texture', function () {
                let gltfPath = path.resolve(outDirPath, '09_tex_transform_from_texture.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));

                assert.strictEqual(asset.materials.length, 1);
                const transform = asset.materials[0].pbrMetallicRoughness.baseColorTexture.extensions.KHR_texture_transform;

                assert.equalEpsilon(transform.rotation, -0.2617993950843811);
                assert.equalEpsilon(transform.scale[0], 5);
                assert.equalEpsilon(transform.scale[1], 5);
                assert.equalEpsilon(transform.offset[0], -1.6383571988477919);
                assert.equalEpsilon(transform.offset[1], -2.54482482508252);
            });

            it('exports texture transform from mapping type vector', function () {
                let gltfPath = path.resolve(outDirPath, '09_tex_transform_from_vector.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));

                assert.strictEqual(asset.materials.length, 1);
                const transform = asset.materials[0].pbrMetallicRoughness.baseColorTexture.extensions.KHR_texture_transform;

                assert.equalEpsilon(transform.rotation, 0.2617993950843811);
                assert.equalEpsilon(transform.scale[0], 0.4);
                assert.equalEpsilon(transform.scale[1], 0.8);
                assert.equalEpsilon(transform.offset[0], -0.20705524479697487);
                assert.equalEpsilon(transform.offset[1], 0.2272593289624576);
            });

            it('export mirror wrapping', function () {
                let gltfPath = path.resolve(outDirPath, '09_tex_wrapping_mirror.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));

                const materials = asset.materials;
                assert.deepStrictEqual(materials.length, 2);
                assert.deepStrictEqual(asset.samplers.length, 1);

                const samp = asset.samplers[0];
                assert.deepStrictEqual(samp.wrapS, 33648);  // MIRRORED_REPEAT
                assert.deepStrictEqual(samp.wrapT, 33648);  // MIRRORED_REPEAT
            });

            it('exports custom normals', function () {
                let gltfPath = path.resolve(outDirPath, '10_custom_normals.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));
                assert.strictEqual(asset.meshes.length, 1);

                let bufferCache = {};

                const smoothCubeMesh = asset.meshes.filter(m => m.name === 'SmoothCube')[0];
                const customNormals = smoothCubeMesh.primitives[0].attributes.NORMAL;
                const customNormalData = getAccessorData(gltfPath, asset, customNormals, bufferCache);
                const customNormalHash = buildVectorHash(customNormalData);

                // In this mesh, the beveled cube has custom normals that are all
                // axis-aligned to the nearest cube face.
                const expectedCustomNormalHash = {
                    "0.000,1.000,0.000": 16,
                    "-1.000,0.000,0.000": 16,
                    "0.000,0.000,-1.000": 16,
                    "0.000,-1.000,0.000": 16,
                    "1.000,0.000,0.000": 16,
                    "0.000,0.000,1.000": 16
                };
                assert.deepStrictEqual(customNormalHash, expectedCustomNormalHash);
            });

            it('exports custom normals with Apply Modifiers', function () {
                let gltfPath = path.resolve(outDirPath, '10_custom_normals_with_modifier.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));
                assert.strictEqual(asset.meshes.length, 1);

                let bufferCache = {};

                // Make sure the Array modifier was applied
                const positions = asset.meshes[0].primitives[0].attributes.POSITION;
                const positionData = getAccessorData(gltfPath, asset, positions, bufferCache);
                const positionHash = buildVectorHash(positionData);
                const numVerts = Object.keys(positionHash).length;
                assert.deepStrictEqual(numVerts, 6);

                const customNormals = asset.meshes[0].primitives[0].attributes.NORMAL;
                const customNormalData = getAccessorData(gltfPath, asset, customNormals, bufferCache);

                // All custom normals are approximately (-Y Blender) = (+Z glTF).
                for (let i = 0; i < customNormalData.length; i += 3) {
                    const normal = customNormalData.slice(i, i + 3);
                    const rounded = normal.map(Math.round);
                    assert.deepStrictEqual(rounded, [0, 0, 1]);
                }
            });

            it('exports loose edges/points', function () {
                let gltfPath = path.resolve(outDirPath, '11_loose_geometry.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));
                assert.strictEqual(asset.meshes.length, 1);

                const prims = asset.meshes[0].primitives;
                let tri_prims = prims.filter(prim => prim.mode === 4 || prim.mode === undefined);
                let edge_prims = prims.filter(prim => prim.mode === 1);
                let point_prims = prims.filter(prim => prim.mode === 0);

                assert.strictEqual(tri_prims.length, 1);
                assert.strictEqual(edge_prims.length, 1);
                assert.strictEqual(point_prims.length, 1);
            });

            it('exports custom range sampled', function () {
                let gltfPath = path.resolve(outDirPath, '12_anim_range_sampled.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));
                const ranged = asset.animations.filter(a => a.name === 'Ranged')[0];
                const no_ranged = asset.animations.filter(a => a.name === 'NoRange')[0];

                assert.strictEqual(asset.accessors[ranged.samplers[ranged.channels[0].sampler].input].count, 13);
                assert.strictEqual(asset.accessors[no_ranged.samplers[no_ranged.channels[0].sampler].input].count, 15);

                assert.strictEqual(asset.accessors[ranged.samplers[ranged.channels[0].sampler].input].count, asset.accessors[ranged.samplers[ranged.channels[0].sampler].output].count);
                assert.strictEqual(asset.accessors[no_ranged.samplers[no_ranged.channels[0].sampler].input].count, asset.accessors[no_ranged.samplers[no_ranged.channels[0].sampler].output].count);
            });

            it('exports custom range not sampled', function () {
                let gltfPath = path.resolve(outDirPath, '12_anim_range_not_sampled.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));
                const ranged = asset.animations.filter(a => a.name === 'Ranged')[0];
                const no_ranged = asset.animations.filter(a => a.name === 'NoRange')[0];

                assert.strictEqual(asset.accessors[ranged.samplers[ranged.channels[0].sampler].input].count, 2);
                assert.strictEqual(asset.accessors[no_ranged.samplers[no_ranged.channels[0].sampler].input].count, 4);

                assert.strictEqual(asset.accessors[ranged.samplers[ranged.channels[0].sampler].input].count * 3, asset.accessors[ranged.samplers[ranged.channels[0].sampler].output].count);
                assert.strictEqual(asset.accessors[no_ranged.samplers[no_ranged.channels[0].sampler].input].count * 3, asset.accessors[no_ranged.samplers[no_ranged.channels[0].sampler].output].count);
            });

            it('exports custom range with driver', function () {
                let gltfPath = path.resolve(outDirPath, '12_anim_range_driver.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));
                const anim = asset.animations.filter(a => a.name === 'ArmatureAction')[0];

                assert.strictEqual(asset.accessors[anim.samplers[anim.channels[0].sampler].input].count, 7);
                assert.strictEqual(asset.accessors[anim.samplers[anim.channels[1].sampler].input].count, asset.accessors[anim.samplers[anim.channels[0].sampler].input].count);
                assert.strictEqual(anim.samplers[anim.channels[0].sampler].input, anim.samplers[anim.channels[1].sampler].input);
                assert.strictEqual(asset.accessors[anim.samplers[anim.channels[0].sampler].input].count, asset.accessors[anim.samplers[anim.channels[0].sampler].output].count);
                assert.strictEqual(asset.accessors[anim.samplers[anim.channels[0].sampler].output].count, asset.accessors[anim.samplers[anim.channels[1].sampler].output].count);
            });

            it('exports transmission', function () {
                let gltfPath = path.resolve(outDirPath, '14_transmission.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));
                const mat_no_transmission = asset.materials.find(mat => mat.name === 'NoTransmission');
                const mat_transmission = asset.materials.find(mat => mat.name === 'Transmission');

                assert.ok('KHR_materials_transmission' in mat_transmission.extensions);
                assert.strictEqual(mat_no_transmission.extensions, undefined);
                const transmission = mat_transmission.extensions.KHR_materials_transmission;
                assert.equalEpsilon(transmission.transmissionFactor, 0.2);

            });

            it('exports volume', function () {
                let gltfPath = path.resolve(outDirPath, '16_volume.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));

                const mat_no_volume = asset.materials.find(mat => mat.name === 'NoVolume');
                assert.ok(!("KHR_materials_volume" in mat_no_volume.extensions));

                const mat_volume = asset.materials.find(mat => mat.name === 'Volume');
                assert.ok("KHR_materials_volume" in mat_volume.extensions);

                const mat_thickness_zero = asset.materials.find(mat => mat.name === 'ThicknessZero');
                assert.ok(!("KHR_materials_volume" in mat_thickness_zero.extensions));

            });

            it('exports IOR', function () {
                let gltfPath = path.resolve(outDirPath, '17_ior.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));

                const pbr = asset.materials.find(mat => mat.name === 'pbr');
                assert.strictEqual(pbr.extensions, undefined);

                const ior_2_no_transmission = asset.materials.find(mat => mat.name === 'ior_2_no_transmission');
                assert.strictEqual(ior_2_no_transmission.extensions, undefined);

                const ior_2 = asset.materials.find(mat => mat.name === 'ior_2');
                assert.ok("KHR_materials_ior" in ior_2.extensions);

                const ior_145 = asset.materials.find(mat => mat.name === 'ior_1.45');
                assert.ok("KHR_materials_ior" in ior_145.extensions);

                const ior_15 = asset.materials.find(mat => mat.name === 'ior_1.5');
                assert.ok(!("KHR_materials_ior" in ior_15.extensions));

            });

            it('exports Variants', function () {
                let gltfPath = path.resolve(outDirPath, '18_variants.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));

                const variant_blue_index = asset.extensions['KHR_materials_variants']['variants'].findIndex(variant => variant.name === "Variant_Blue");
                const variant_red_index = asset.extensions['KHR_materials_variants']['variants'].findIndex(variant => variant.name === "Variant_Red");


                const mat_blue_index = asset.materials.findIndex(mat => mat.name === "Blue");
                const mat_green_index = asset.materials.findIndex(mat => mat.name === "Green");
                const mat_white_index = asset.materials.findIndex(mat => mat.name === "White");
                const mat_orange_index = asset.materials.findIndex(mat => mat.name === "Orange");
                const mat_red_index = asset.materials.findIndex(mat => mat.name === "Red");
                const prim_blue = asset.meshes[0].primitives.find(prim => prim.material === mat_blue_index);
                const prim_green = asset.meshes[0].primitives.find(prim => prim.material === mat_green_index);
                const prim_white = asset.meshes[0].primitives.find(prim => prim.material === mat_white_index);

                assert.strictEqual(asset.extensions['KHR_materials_variants']['variants'].length, 2);

                assert.strictEqual(prim_blue.extensions['KHR_materials_variants']['mappings'].length, 2);
                prim_blue.extensions['KHR_materials_variants']['mappings'].forEach(function (mapping) {
                    assert.strictEqual(mapping.variants.length, 1);
                });
                const map_1 = prim_blue.extensions['KHR_materials_variants']['mappings'].find(mapping => mapping.material === mat_red_index);
                assert.strictEqual(map_1.variants[0], variant_red_index);
                const map_2 = prim_blue.extensions['KHR_materials_variants']['mappings'].find(mapping => mapping.material === mat_blue_index);
                assert.strictEqual(map_2.variants[0], variant_blue_index);

                assert.strictEqual(prim_green.extensions['KHR_materials_variants']['mappings'].length, 2);
                prim_green.extensions['KHR_materials_variants']['mappings'].forEach(function (mapping) {
                    assert.strictEqual(mapping.variants.length, 1);
                });
                const map_3 = prim_green.extensions['KHR_materials_variants']['mappings'].find(mapping => mapping.material === mat_orange_index);
                assert.strictEqual(map_3.variants[0], variant_red_index);
                const map_4 = prim_green.extensions['KHR_materials_variants']['mappings'].find(mapping => mapping.material === mat_green_index);
                assert.strictEqual(map_4.variants[0], variant_blue_index);

                assert.strictEqual(prim_white.extensions['KHR_materials_variants']['mappings'].length, 1);
                prim_white.extensions['KHR_materials_variants']['mappings'].forEach(function (mapping) {
                    assert.strictEqual(mapping.variants.length, 2);
                });
                const map_5 = prim_white.extensions['KHR_materials_variants']['mappings'].find(mapping => mapping.material === mat_white_index);
                assert.ok(variant_red_index in map_5.variants);
                assert.ok(variant_blue_index in map_5.variants);

            });

            it('exports Specular', function () {
                let gltfPath = path.resolve(outDirPath, '20_specular.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));

                const mat_NoTextDefault = asset.materials.find(mat => mat.name === "NoTextDefault");
                const mat_NoTextSpec = asset.materials.find(mat => mat.name === "NoTextSpec");
                const mat_NoTextTint = asset.materials.find(mat => mat.name === "NoTextTint");
                const mat_NoTextAll = asset.materials.find(mat => mat.name === "NoTextAll");
                const mat_NoTextAllIOR = asset.materials.find(mat => mat.name === "NoTextAllIOR");
                const mat_BaseColorTex_Factor = asset.materials.find(mat => mat.name === "BaseColorTex_Factor");
                const mat_BaseColorText_NoFactor = asset.materials.find(mat => mat.name === "BaseColorText_NoFactor");
                const mat_TexTrans = asset.materials.find(mat => mat.name === "TexTrans");
                const mat_TexTint = asset.materials.find(mat => mat.name === "TexTint");
                const mat_TextSpec = asset.materials.find(mat => mat.name === "TextSpec");
                const mat_TextBaseSpec = asset.materials.find(mat => mat.name === "TextBaseSpec");
                const mat_TextBaseSpecTint = asset.materials.find(mat => mat.name === "TextBaseSpecTint");
                const mat_TextBaseSpecTintTrans = asset.materials.find(mat => mat.name === "TextBaseSpecTintTrans");
                const mat_TextTrans = asset.materials.find(mat => mat.name === "TextTrans");

                assert.strictEqual(mat_NoTextDefault.extensions, undefined);

                assert.ok(!("specularTexture" in mat_NoTextSpec.extensions['KHR_materials_specular']));
                assert.ok(!("specularColorTexture" in mat_NoTextSpec.extensions['KHR_materials_specular']));
                assert.equalEpsilonArray(mat_NoTextSpec.extensions['KHR_materials_specular']["specularColorFactor"], [1.26, 1.12, 0.98]);
                assert.ok(!("specularFactor" in mat_NoTextSpec.extensions['KHR_materials_specular']));

                assert.ok(!("specularTexture" in mat_NoTextTint.extensions['KHR_materials_specular']));
                assert.ok(!("specularColorTexture" in mat_NoTextTint.extensions['KHR_materials_specular']));
                assert.equalEpsilonArray(mat_NoTextTint.extensions['KHR_materials_specular']["specularColorFactor"], [0.96, 0.96, 0.96]);
                assert.ok(!("specularFactor" in mat_NoTextTint.extensions['KHR_materials_specular']));

                assert.ok(!("specularTexture" in mat_NoTextAll.extensions['KHR_materials_specular']));
                assert.ok(!("specularColorTexture" in mat_NoTextAll.extensions['KHR_materials_specular']));
                assert.equalEpsilonArray(mat_NoTextAll.extensions['KHR_materials_specular']["specularColorFactor"], [1.312, 1.504, 1.456]);
                assert.ok(!("specularFactor" in mat_NoTextAll.extensions['KHR_materials_specular']));

                assert.ok(!("specularTexture" in mat_NoTextAllIOR.extensions['KHR_materials_specular']));
                assert.ok(!("specularColorTexture" in mat_NoTextAllIOR.extensions['KHR_materials_specular']));
                assert.equalEpsilonArray(mat_NoTextAllIOR.extensions['KHR_materials_specular']["specularColorFactor"], [1.312, 1.504, 1.4592]);
                assert.ok(!("specularFactor" in mat_NoTextAllIOR.extensions['KHR_materials_specular']));

                assert.ok(!("specularTexture" in mat_BaseColorTex_Factor.extensions['KHR_materials_specular']));
                assert.ok(!("specularColorTexture" in mat_BaseColorTex_Factor.extensions['KHR_materials_specular']));
                assert.equalEpsilonArray(mat_BaseColorTex_Factor.extensions['KHR_materials_specular']["specularColorFactor"], [1.312, 1.504, 1.456]);
                assert.ok(!("specularFactor" in mat_BaseColorTex_Factor.extensions['KHR_materials_specular']));

                assert.ok(!("extensions" in mat_BaseColorText_NoFactor));

            });

            it('exports Collections', function () {
                let gltfPath = path.resolve(outDirPath, '21_scene.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));

                assert.strictEqual(asset.nodes.length, 47);
                assert.strictEqual(asset.scenes[0].nodes.length, 9);
                assert.strictEqual(asset.meshes.length, 6);
            });

            it('manages node groups', function () {
                let gltfPath = path.resolve(outDirPath, '22_node_groups.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));

                const mat_ref = asset.materials.find(mat => mat.name === "Ref");
                const mat_out = asset.materials.find(mat => mat.name === "out");
                const mat_in = asset.materials.find(mat => mat.name === "in");
                const mat_nested = asset.materials.find(mat => mat.name === "nested");
                const mat_2groups = asset.materials.find(mat => mat.name === "2groups");

                assert.ok("baseColorTexture" in mat_ref.pbrMetallicRoughness);
                assert.ok("baseColorTexture" in mat_out.pbrMetallicRoughness);
                assert.ok("baseColorTexture" in mat_in.pbrMetallicRoughness);
                assert.ok("baseColorTexture" in mat_nested.pbrMetallicRoughness);
                assert.ok("baseColorTexture" in mat_2groups.pbrMetallicRoughness);

            });


            it('exports Attributes', function () {
                let gltfPath = path.resolve(outDirPath, '22_vertex_colors_and_attributes.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));

                let bufferCache = {};

                const primitive = asset.meshes[asset.nodes.filter(m => m.name === 'Cube_attributes')[0].mesh].primitives[0];

                assert.ok(!("_KO" in primitive.attributes));

                const _vertex_float = asset.accessors[primitive.attributes._VERTEX_FLOAT];
                const _vertex_float_data = getAccessorData(gltfPath, asset, primitive.attributes._VERTEX_FLOAT, bufferCache);
                assert.strictEqual(_vertex_float.count, 24);
                const expected_vertex_float = [0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 2.0, 2.0, 2.0, 3.0, 3.0, 3.0, 4.0, 4.0, 4.0, 5.0, 5.0, 5.0, 6.0, 6.0, 6.0, 7.0, 7.0, 7.0];
                assert.deepStrictEqual(_vertex_float_data, expected_vertex_float);

                const _vertex_integer = asset.accessors[primitive.attributes._VERTEX_INTEGER];
                const _vertex_integer_data = getAccessorData(gltfPath, asset, primitive.attributes._VERTEX_INTEGER, bufferCache);
                assert.strictEqual(_vertex_integer.count, 24);
                const expected_vertex_integer = [0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 2.0, 2.0, 2.0, 3.0, 3.0, 3.0, 4.0, 4.0, 4.0, 5.0, 5.0, 5.0, 6.0, 6.0, 6.0, 7.0, 7.0, 7.0];
                assert.deepStrictEqual(_vertex_integer_data, expected_vertex_integer);

                assert.ok(!("_VERTEX_STRING" in primitive.attributes));

                const _vertex_8bitinteger = asset.accessors[primitive.attributes._VERTEX_8BITINTEGER];
                const _vertex_8bitinteger_data = getAccessorData(gltfPath, asset, primitive.attributes._VERTEX_8BITINTEGER, bufferCache);
                assert.strictEqual(_vertex_8bitinteger.count, 24);
                const expected_vertex_8bitinteger = [0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 2.0, 2.0, 2.0, 3.0, 3.0, 3.0, 4.0, 4.0, 4.0, 5.0, 5.0, 5.0, 6.0, 6.0, 6.0, 7.0, 7.0, 7.0];
                assert.deepStrictEqual(_vertex_8bitinteger_data, expected_vertex_8bitinteger);

                const _vertex_vector = asset.accessors[primitive.attributes._VERTEX_VECTOR];
                const _vertex_vector_data = getAccessorData(gltfPath, asset, primitive.attributes._VERTEX_VECTOR, bufferCache);
                assert.strictEqual(_vertex_vector.count, 24);
                const expected_vertex_vector = [0.0, 1.0, 2.0, 0.0, 1.0, 2.0, 0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 3.0, 4.0, 5.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 6.0, 7.0, 8.0, 6.0, 7.0, 8.0,
                    9.0, 10.0, 11.0, 9.0, 10.0, 11.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0, 12.0, 13.0, 14.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 15.0, 16.0, 17.0, 15.0, 16.0, 17.0,
                    18.0, 19.0, 20.0, 18.0, 19.0, 20.0, 18.0, 19.0, 20.0, 21.0, 22.0, 23.0, 21.0, 22.0, 23.0, 21.0, 22.0, 23.0];
                assert.deepStrictEqual(_vertex_vector_data, expected_vertex_vector);

                const _vertex_2dvector = asset.accessors[primitive.attributes._VERTEX_2DVECTOR];
                const _vertex_2dvector_data = getAccessorData(gltfPath, asset, primitive.attributes._VERTEX_2DVECTOR, bufferCache);
                assert.strictEqual(_vertex_2dvector.count, 24);
                const expected_vertex_2dvector = [0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 2.0, 3.0, 2.0, 3.0, 2.0, 3.0, 4.0, 5.0, 4.0, 5.0, 4.0, 5.0, 6.0, 7.0, 6.0, 7.0, 6.0, 7.0,
                    8.0, 9.0, 8.0, 9.0, 8.0, 9.0, 10.0, 11.0, 10.0, 11.0, 10.0, 11.0, 12.0, 13.0, 12.0, 13.0, 12.0, 13.0, 14.0, 15.0, 14.0, 15.0, 14.0, 15.0];
                assert.deepStrictEqual(_vertex_2dvector_data, expected_vertex_2dvector);

                const _vertex_boolean = asset.accessors[primitive.attributes._VERTEX_BOOLEAN];
                const _vertex_boolean_data = getAccessorData(gltfPath, asset, primitive.attributes._VERTEX_BOOLEAN, bufferCache);
                assert.strictEqual(_vertex_boolean.count, 24);
                const expected_vertex_boolean = [1, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0];
                assert.deepStrictEqual(_vertex_boolean_data, expected_vertex_boolean);

                assert.ok(!("_EDGE_FLOAT" in primitive.attributes));

                const _face_float = asset.accessors[primitive.attributes._FACE_FLOAT];
                const _face_float_data = getAccessorData(gltfPath, asset, primitive.attributes._FACE_FLOAT, bufferCache);
                assert.strictEqual(_face_float.count, 24);
                const expected_face_float = [0.0, 4.0, 5.0, 3.0, 4.0, 5.0, 0.0, 1.0, 4.0, 1.0, 3.0, 4.0, 0.0, 2.0, 5.0, 2.0, 3.0, 5.0, 0.0, 1.0, 2.0, 1.0, 2.0, 3.0];
                assert.deepStrictEqual(_face_float_data, expected_face_float);

                const _facecorner_float = asset.accessors[primitive.attributes._FACECORNER_FLOAT];
                const _facecorner_float_data = getAccessorData(gltfPath, asset, primitive.attributes._FACECORNER_FLOAT, bufferCache);
                assert.strictEqual(_facecorner_float.count, 24);
                const expected_facecorner_float = [100, 117, 122, 113, 116, 123, 103, 105, 118, 104, 114, 119, 101, 110, 121, 111, 112, 120, 102, 106, 109, 107, 108, 115];
                assert.deepStrictEqual(_facecorner_float_data, expected_facecorner_float);

                const _facecorner_vector = asset.accessors[primitive.attributes._FACECORNER_VECTOR];
                assert.strictEqual(_facecorner_vector.count, 24);

                const _face_vector = asset.accessors[primitive.attributes._FACE_VECTOR];
                assert.strictEqual(_face_vector.count, 24);

                const _facecorner_vector2d = asset.accessors[primitive.attributes._FACECORNER_VECTOR2D];
                assert.strictEqual(_facecorner_vector2d.count, 24);

                const _face_vector2d = asset.accessors[primitive.attributes._FACE_VECTOR2D];
                assert.strictEqual(_face_vector2d.count, 24);

                // Edge only
                const primitive_edge_only = asset.meshes[asset.nodes.filter(m => m.name === 'Edge')[0].mesh].primitives[0];
                assert.ok(!("_FACE_FLOAT" in primitive_edge_only.attributes));

                const _vertex_float_edge = asset.accessors[primitive_edge_only.attributes._VERTEX_FLOAT];
                const _vertex_float_edge_data = getAccessorData(gltfPath, asset, primitive_edge_only.attributes._VERTEX_FLOAT, bufferCache);
                assert.strictEqual(_vertex_float_edge.count, 2);
                const expected_vertex_float_edge = [1.0, 2.0];
                assert.deepStrictEqual(_vertex_float_edge_data, expected_vertex_float_edge);

                // Vertices only
                const primitive_vertex_only = asset.meshes[asset.nodes.filter(m => m.name === 'Vertex')[0].mesh].primitives[0];
                assert.ok(!("_EDGE_FLOAT" in primitive_vertex_only.attributes));

                const _vertex_float_vertex = asset.accessors[primitive_vertex_only.attributes._VERTEX_FLOAT];
                const _vertex_float_vertex_data = getAccessorData(gltfPath, asset, primitive_vertex_only.attributes._VERTEX_FLOAT, bufferCache);
                assert.strictEqual(_vertex_float_vertex.count, 2);
                const expected_vertex_float_vertex = [3.0, 4.0];
                assert.deepStrictEqual(_vertex_float_vertex_data, expected_vertex_float_vertex);

                // Mix
                const primitive_face = asset.meshes[asset.nodes.filter(m => m.name === 'Cube_and_edges')[0].mesh].primitives[0];
                const primitive_edge = asset.meshes[asset.nodes.filter(m => m.name === 'Cube_and_edges')[0].mesh].primitives[1];

                const mix_p0_vertex_float = asset.accessors[primitive_face.attributes._VERTEX_FLOAT];
                const mix_p0_vertex_float_data = getAccessorData(gltfPath, asset, primitive_face.attributes._VERTEX_FLOAT, bufferCache);
                assert.strictEqual(mix_p0_vertex_float.count, 24);
                const expected_mix_p0_vertex_float_data = [3.0, 3.0, 3.0, 4.0, 4.0, 4.0, 5.0, 5.0, 5.0, 6.0, 6.0, 6.0, 7.0, 7.0, 7.0, 8.0, 8.0, 8.0, 9.0, 9.0, 9.0, 10.0, 10.0, 10.0];
                assert.deepStrictEqual(mix_p0_vertex_float_data, expected_mix_p0_vertex_float_data);

                const mix_p1_vertex_float = asset.accessors[primitive_edge.attributes._VERTEX_FLOAT];
                const mix_p1_vertex_float_data = getAccessorData(gltfPath, asset, primitive_edge.attributes._VERTEX_FLOAT, bufferCache);
                assert.strictEqual(mix_p1_vertex_float.count, 2);
                const expected_mix_p1_vertex_float_data = [1.0, 2.0];
                assert.deepStrictEqual(mix_p1_vertex_float_data, expected_mix_p1_vertex_float_data);

                // GLobal Mix
                const primitive_faces = asset.meshes[asset.nodes.filter(m => m.name === 'Cube_and_edges_and_vertex')[0].mesh].primitives[0];
                const primitive_edges = asset.meshes[asset.nodes.filter(m => m.name === 'Cube_and_edges_and_vertex')[0].mesh].primitives[1];
                const primitive_vertices = asset.meshes[asset.nodes.filter(m => m.name === 'Cube_and_edges_and_vertex')[0].mesh].primitives[2];

                const gmix_p0_vertex_float = asset.accessors[primitive_faces.attributes._VERTEX_FLOAT];
                const gmix_p0_vertex_float_data = getAccessorData(gltfPath, asset, primitive_faces.attributes._VERTEX_FLOAT, bufferCache);
                assert.strictEqual(gmix_p0_vertex_float.count, 24);
                const expected_gmix_p0_vertex_float_data = [0.3, 0.3, 0.3, 0.4, 0.4, 0.4, 0.5, 0.5, 0.5, 0.6, 0.6, 0.6, 0.7, 0.7, 0.7, 0.8, 0.8, 0.8, 0.9, 0.9, 0.9, 0.01, 0.01, 0.01];
                assert.equalEpsilonArray(gmix_p0_vertex_float_data, expected_gmix_p0_vertex_float_data);

                const mix_p2_vertex_float = asset.accessors[primitive_edges.attributes._VERTEX_FLOAT];
                const mix_p2_vertex_float_data = getAccessorData(gltfPath, asset, primitive_edges.attributes._VERTEX_FLOAT, bufferCache);
                assert.strictEqual(mix_p2_vertex_float.count, 3);
                const expected_mix_p2_vertex_float_data = [0.1, 0.2, 1.2];
                assert.equalEpsilonArray(mix_p2_vertex_float_data, expected_mix_p2_vertex_float_data);

                const mix_p3_vertex_float = asset.accessors[primitive_vertices.attributes._VERTEX_FLOAT];
                const mix_p3_vertex_float_data = getAccessorData(gltfPath, asset, primitive_vertices.attributes._VERTEX_FLOAT, bufferCache);
                assert.strictEqual(mix_p3_vertex_float.count, 1);
                const expected_mix_p3_vertex_float_data = [1.1];
                assert.equalEpsilonArray(mix_p3_vertex_float_data, expected_mix_p3_vertex_float_data);

            });

            it('exports Active Collection', function () {
                let gltfPath_1 = path.resolve(outDirPath, '23_use_active_collection_without_nested.gltf');
                const asset_1 = JSON.parse(fs.readFileSync(gltfPath_1));
                assert.strictEqual(asset_1.nodes.length, 1);

                let gltfPath_2 = path.resolve(outDirPath, '23_use_active_collection_all.gltf');
                const asset_2 = JSON.parse(fs.readFileSync(gltfPath_2));
                assert.strictEqual(asset_2.nodes.length, 3);

                let gltfPath_3 = path.resolve(outDirPath, '23_use_active_collection_nested.gltf');
                const asset_3 = JSON.parse(fs.readFileSync(gltfPath_3));
                assert.strictEqual(asset_3.nodes.length, 2);
            });

            it('exports GN', function () {
                let gltfPath = path.resolve(outDirPath, '22_simple_GN.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));

                assert.strictEqual(asset.materials.length, 2);
                assert.strictEqual(asset.meshes.length, 2);

            });

            it('exports correct no SK when modifier', function () {
                let gltfPath_1 = path.resolve(outDirPath, '27_apply_modifier_with_shapekeys.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath_1));

                const modifier_mesh = asset.meshes[asset.nodes.filter(m => m.name === 'modifier')[0].mesh];
                assert.ok(!('weights' in modifier_mesh));
                if ("extras" in modifier_mesh) {
                    assert.ok(!('targetNames' in modifier_mesh['extras']));
                }
                const primitive_modifier_mesh = modifier_mesh.primitives[0];
                assert.ok(!('targets' in primitive_modifier_mesh));

                const no_modifier_mesh = asset.meshes[asset.nodes.filter(m => m.name === 'no_modifier')[0].mesh];
                assert.ok('weights' in no_modifier_mesh);
                if ("extras" in no_modifier_mesh) {
                    assert.ok('targetNames' in no_modifier_mesh['extras']);
                }
                const primitive_no_modifier_mesh = no_modifier_mesh.primitives[0];
                assert.ok('targets' in primitive_no_modifier_mesh);

            });

            it('exports mesh instances', function () {
                let gltfPath = path.resolve(outDirPath, '25_mesh_instances.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));
                const original = asset.nodes.find(node => node.name === 'original');
                const original_instance = asset.nodes.find(node => node.name === 'original_instance');
                const with_object_material = asset.nodes.find(node => node.name === 'with_object_material');
                const with_object_material_other = asset.nodes.find(node => node.name === 'with_object_material_other');
                const modifier_1 = asset.nodes.find(node => node.name === 'modifier_1');
                const modifier_2 = asset.nodes.find(node => node.name === 'modifier_2');
                const skined_1 = asset.nodes.find(node => node.name === 'skined_1');
                const skined_2 = asset.nodes.find(node => node.name === 'skined_2');

                assert.strictEqual(original.mesh, original_instance.mesh);
                assert.strictEqual(original.mesh, original_instance.mesh);
                assert.notEqual(original.mesh, with_object_material.mesh);
                assert.notEqual(original.mesh, with_object_material_other.mesh);
                assert.notEqual(with_object_material.mesh, with_object_material_other.mesh);
                assert.strictEqual(asset.meshes[original.mesh].primitives[0].indices, asset.meshes[with_object_material.mesh].primitives[0].indices)
                assert.strictEqual(asset.meshes[original.mesh].primitives[0].attributes['POSITION'], asset.meshes[with_object_material.mesh].primitives[0].attributes['POSITION'])
                assert.strictEqual(asset.meshes[original.mesh].primitives[0].attributes['TEXCOORD_0'], asset.meshes[with_object_material.mesh].primitives[0].attributes['TEXCOORD_0'])
                assert.strictEqual(asset.meshes[original.mesh].primitives[0].attributes['NORMAL'], asset.meshes[with_object_material.mesh].primitives[0].attributes['NORMAL'])
                assert.strictEqual(asset.meshes[original.mesh].primitives[0].indices, asset.meshes[with_object_material_other.mesh].primitives[0].indices)
                assert.strictEqual(asset.meshes[original.mesh].primitives[0].attributes['POSITION'], asset.meshes[with_object_material_other.mesh].primitives[0].attributes['POSITION'])
                assert.strictEqual(asset.meshes[original.mesh].primitives[0].attributes['TEXCOORD_0'], asset.meshes[with_object_material_other.mesh].primitives[0].attributes['TEXCOORD_0'])
                assert.strictEqual(asset.meshes[original.mesh].primitives[0].attributes['NORMAL'], asset.meshes[with_object_material_other.mesh].primitives[0].attributes['NORMAL'])
                assert.strictEqual(original.mesh, modifier_1.mesh);
                assert.strictEqual(original.mesh, modifier_2.mesh);
                assert.notEqual(original.mesh, skined_1.mesh);
                assert.notEqual(original.mesh, skined_2.mesh);

            });

            it('exports mesh instances apply modifier', function () {
                let gltfPath = path.resolve(outDirPath, '25_mesh_instances_apply_modifier.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));
                const original = asset.nodes.find(node => node.name === 'original');
                const original_instance = asset.nodes.find(node => node.name === 'original_instance');
                const with_object_material = asset.nodes.find(node => node.name === 'with_object_material');
                const with_object_material_other = asset.nodes.find(node => node.name === 'with_object_material_other');
                const modifier_1 = asset.nodes.find(node => node.name === 'modifier_1');
                const modifier_2 = asset.nodes.find(node => node.name === 'modifier_2');
                const skined_1 = asset.nodes.find(node => node.name === 'skined_1');
                const skined_2 = asset.nodes.find(node => node.name === 'skined_2');

                assert.strictEqual(original.mesh, original_instance.mesh);
                assert.strictEqual(original.mesh, original_instance.mesh);
                assert.notEqual(original.mesh, with_object_material.mesh);
                assert.notEqual(original.mesh, with_object_material_other.mesh);
                assert.notEqual(with_object_material.mesh, with_object_material_other.mesh);
                assert.strictEqual(asset.meshes[original.mesh].primitives[0].indices, asset.meshes[with_object_material.mesh].primitives[0].indices)
                assert.strictEqual(asset.meshes[original.mesh].primitives[0].attributes['POSITION'], asset.meshes[with_object_material.mesh].primitives[0].attributes['POSITION'])
                assert.strictEqual(asset.meshes[original.mesh].primitives[0].attributes['TEXCOORD_0'], asset.meshes[with_object_material.mesh].primitives[0].attributes['TEXCOORD_0'])
                assert.strictEqual(asset.meshes[original.mesh].primitives[0].attributes['NORMAL'], asset.meshes[with_object_material.mesh].primitives[0].attributes['NORMAL'])
                assert.strictEqual(asset.meshes[original.mesh].primitives[0].indices, asset.meshes[with_object_material_other.mesh].primitives[0].indices)
                assert.strictEqual(asset.meshes[original.mesh].primitives[0].attributes['POSITION'], asset.meshes[with_object_material_other.mesh].primitives[0].attributes['POSITION'])
                assert.strictEqual(asset.meshes[original.mesh].primitives[0].attributes['TEXCOORD_0'], asset.meshes[with_object_material_other.mesh].primitives[0].attributes['TEXCOORD_0'])
                assert.strictEqual(asset.meshes[original.mesh].primitives[0].attributes['NORMAL'], asset.meshes[with_object_material_other.mesh].primitives[0].attributes['NORMAL'])
                assert.notEqual(original.mesh, modifier_1.mesh);
                assert.notEqual(original.mesh, modifier_2.mesh);
                assert.notEqual(original.mesh, skined_1.mesh);
                assert.notEqual(original.mesh, skined_2.mesh);

            });

            it('exports factor', function () {
                let gltfPath = path.resolve(outDirPath, '01_factors.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));
                const mat = asset.materials[0];
                const pbr = mat.pbrMetallicRoughness;

                assert.equalEpsilonArray(mat.extensions['KHR_materials_sheen']["sheenColorFactor"], [0.1, 0.2, 0.3]);
                assert.equalEpsilon(mat.extensions['KHR_materials_sheen']["sheenRoughnessFactor"], 0.5);
                assert.equalEpsilonArray(pbr.baseColorFactor, [0.5, 0.6, 0.7, 0.123]);
                assert.equalEpsilon(mat.extensions['KHR_materials_clearcoat']["clearcoatFactor"], 0.234);
                assert.equalEpsilon(mat.extensions['KHR_materials_clearcoat']["clearcoatRoughnessFactor"], 0.345);
                assert.equalEpsilon(mat.extensions['KHR_materials_transmission']["transmissionFactor"], 0.36);
                assert.equalEpsilonArray(mat.emissiveFactor, [0.4, 0.5, 0.6]);
                assert.equalEpsilon(pbr.metallicFactor, 0.2);
                assert.equalEpsilon(pbr.roughnessFactor, 0.3);
                assert.equalEpsilon(mat.extensions['KHR_materials_volume']["thicknessFactor"], 0.9);
                assert.equalEpsilon(mat.extensions['KHR_materials_specular']["specularFactor"], 0.5);
                assert.equalEpsilonArray(mat.extensions['KHR_materials_specular']["specularColorFactor"], [0.7, 0.6, 0.5]);

            });

            it('exports SK / SK anim', function () {
                let gltfPath_1 = path.resolve(outDirPath, '28_shapekeys_anim.gltf');
                const asset_1 = JSON.parse(fs.readFileSync(gltfPath_1));
                var anim_mesh = asset_1.meshes[asset_1.nodes.filter(m => m.name === 'AnimCube')[0].mesh];
                var driven_mesh = asset_1.meshes[asset_1.nodes.filter(m => m.name === 'DrivenCube')[0].mesh];

                assert.ok('weights' in anim_mesh);
                assert.ok('weights' in driven_mesh);

                assert.ok('targetNames' in anim_mesh['extras']);
                assert.ok('targetNames' in driven_mesh['extras']);

                assert.ok('targets' in anim_mesh.primitives[0]);
                assert.ok('targets' in driven_mesh.primitives[0]);

                assert.strictEqual(asset_1.animations[0].channels[0].target.path, 'weights');
                assert.strictEqual(asset_1.animations[1].channels[1].target.path, 'weights');

                let gltfPath_2 = path.resolve(outDirPath, '28_shapekeys_no_sk_anim_export.gltf');
                const asset_2 = JSON.parse(fs.readFileSync(gltfPath_2));
                anim_mesh = asset_2.meshes[asset_2.nodes.filter(m => m.name === 'AnimCube')[0].mesh];
                driven_mesh = asset_2.meshes[asset_2.nodes.filter(m => m.name === 'DrivenCube')[0].mesh];

                assert.ok('weights' in anim_mesh);
                assert.ok('weights' in driven_mesh);

                assert.ok('targetNames' in anim_mesh['extras']);
                assert.ok('targetNames' in driven_mesh['extras']);

                assert.ok('targets' in anim_mesh.primitives[0]);
                assert.ok('targets' in driven_mesh.primitives[0]);

                assert.strictEqual(asset_2.animations.length, 1);
                assert.strictEqual(asset_2.animations[0].channels.length, 3);

                let gltfPath_3 = path.resolve(outDirPath, '28_shapekeys_no_sk_export.gltf');
                const asset_3 = JSON.parse(fs.readFileSync(gltfPath_3));
                anim_mesh = asset_3.meshes[asset_3.nodes.filter(m => m.name === 'AnimCube')[0].mesh];
                driven_mesh = asset_3.meshes[asset_3.nodes.filter(m => m.name === 'DrivenCube')[0].mesh];

                assert.ok(!('weights' in anim_mesh));
                assert.ok(!('weights' in driven_mesh));

                if ("extras" in anim_mesh) {
                    assert.ok(!('targetNames' in anim_mesh['extras']));
                }
                if ("extras" in driven_mesh) {
                    assert.ok(!('targetNames' in driven_mesh['extras']));
                }

                assert.ok(!('targets' in anim_mesh.primitives[0]));
                assert.ok(!('targets' in driven_mesh.primitives[0]));

                assert.strictEqual(asset_2.animations.length, 1);
                assert.strictEqual(asset_2.animations[0].channels.length, 3);

            });

            it('exports using sk reset', function () {
                let gltfPath = path.resolve(outDirPath, '28_sk_reset.gltf');
                var asset = JSON.parse(fs.readFileSync(gltfPath));

                const obj1 = asset.animations.filter(a => a.name === 'Obj1')[0].channels.filter(a => a.target.path === "weights")[0].sampler;
                const obj2 = asset.animations.filter(a => a.name === 'Obj2')[0].channels.filter(a => a.target.path === "weights")[0].sampler;
                const obj2_2 = asset.animations.filter(a => a.name === 'Obj2_2')[0].channels.filter(a => a.target.path === "weights")[0].sampler;

                const anim1 = asset.animations.filter(a => a.name === 'Obj1')[0].samplers[obj1].output;
                const anim2 = asset.animations.filter(a => a.name === 'Obj2')[0].samplers[obj2].output;
                const anim2_2 = asset.animations.filter(a => a.name === 'Obj2_2')[0].samplers[obj2_2].output;

                let bufferCache = {};
                const outputData1 = getAccessorData(gltfPath, asset, anim1, bufferCache);
                const outputData2 = getAccessorData(gltfPath, asset, anim2, bufferCache);
                const outputData2_2 = getAccessorData(gltfPath, asset, anim2_2, bufferCache);

                assert.equal(outputData1[0], 0.5);
                assert.equal(outputData1[1], 0.0);

                assert.equal(outputData2[0], 0.5); // no reset for already active action
                assert.equal(outputData2[1], 0.0);

                assert.equal(outputData2_2[0], 0.0);
                assert.equal(outputData2_2[1], 0.0);

            });

            it('exports using sk no reset', function () {
                let gltfPath = path.resolve(outDirPath, '28_sk_no_reset.gltf');
                var asset = JSON.parse(fs.readFileSync(gltfPath));

                const obj1 = asset.animations.filter(a => a.name === 'Obj1')[0].channels.filter(a => a.target.path === "weights")[0].sampler;
                const obj2 = asset.animations.filter(a => a.name === 'Obj2')[0].channels.filter(a => a.target.path === "weights")[0].sampler;
                const obj2_2 = asset.animations.filter(a => a.name === 'Obj2_2')[0].channels.filter(a => a.target.path === "weights")[0].sampler;

                const anim1 = asset.animations.filter(a => a.name === 'Obj1')[0].samplers[obj1].output;
                const anim2 = asset.animations.filter(a => a.name === 'Obj2')[0].samplers[obj2].output;
                const anim2_2 = asset.animations.filter(a => a.name === 'Obj2_2')[0].samplers[obj2_2].output;

                let bufferCache = {};
                const outputData1 = getAccessorData(gltfPath, asset, anim1, bufferCache);
                const outputData2 = getAccessorData(gltfPath, asset, anim2, bufferCache);
                const outputData2_2 = getAccessorData(gltfPath, asset, anim2_2, bufferCache);

                assert.equal(outputData1[0], 0.5);
                assert.equal(outputData1[1], 0.0);

                assert.equal(outputData2[0], 0.5);
                assert.equal(outputData2[1], 0.0);

                assert.equal(outputData2_2[0], 0.0);
                assert.equal(outputData2_2[1], 1.0);

            });

            it('exports using sk sparse', function () {
                let gltfPath = path.resolve(outDirPath, '28_sparse_sk.gltf');
                var asset = JSON.parse(fs.readFileSync(gltfPath));

                const target_pos = asset.meshes[0].primitives[0].targets[0]['POSITION'];
                const output_count = asset.accessors[target_pos].sparse['count'];
                assert.equal(asset.accessors[target_pos].bufferView, null);
                assert.notEqual(asset.accessors[target_pos].sparse['indices']['bufferView'], null);
                assert.equal(output_count, 3);

            });

            it('exports using sk no sparse', function () {
                let gltfPath = path.resolve(outDirPath, '28_sparse_sk_no_sparse.gltf');
                var asset = JSON.parse(fs.readFileSync(gltfPath));

                const target_pos = asset.meshes[0].primitives[0].targets[0]['POSITION'];
                assert.equal(asset.accessors[target_pos].sparse, null);
                assert.notEqual(asset.accessors[target_pos].bufferView, null);

            });

            it('exports using sk sparse omit', function () {
                let gltfPath = path.resolve(outDirPath, '28_sparse_sk_omit.gltf');
                var asset = JSON.parse(fs.readFileSync(gltfPath));

                const target_pos = asset.meshes[0].primitives[0].targets[0]['POSITION'];
                assert.equal(asset.accessors[target_pos].sparse, null);
                assert.equal(asset.accessors[target_pos].bufferView, null);

            });

            it('exports using sk sparse size', function () {
                let gltfPath = path.resolve(outDirPath, '28_sparse_sk_no_sparse_size.gltf');
                var asset = JSON.parse(fs.readFileSync(gltfPath));

                const target_pos = asset.meshes[0].primitives[0].targets[0]['POSITION'];
                assert.equal(asset.accessors[target_pos].sparse, null);
                assert.notEqual(asset.accessors[target_pos].bufferView, null);

            });

            it('exports using armature rest pose', function () {
                let gltfPath_1 = path.resolve(outDirPath, '29_armature_use_current_pose.gltf');
                var asset = JSON.parse(fs.readFileSync(gltfPath_1));
                var cube = asset.nodes.filter(m => m.name === 'Bone')[0]
                assert.ok('rotation' in cube);

                let gltfPath_2 = path.resolve(outDirPath, '29_armature_use_rest_pose.gltf');
                asset = JSON.parse(fs.readFileSync(gltfPath_2));
                cube = asset.nodes.filter(m => m.name === 'Bone')[0]
                assert.ok(!('rotation' in cube));
            });

            it('exports interpolation when sampled, optimized, with keep', function () {
                let gltfPath_1 = path.resolve(outDirPath, '31_interpolation_sampled.gltf');
                var asset = JSON.parse(fs.readFileSync(gltfPath_1));

                const anim_cube = asset.animations.filter(a => a.name === 'CubeAction')[0];

                const cube_translation_channel = anim_cube.channels.filter(a => a.target.path === "translation")[0];
                const cube_rotation_channel = anim_cube.channels.filter(a => a.target.path === "rotation")[0];
                const cube_scale_channel = anim_cube.channels.filter(a => a.target.path === "scale")[0];

                const cube_translation_sampler = anim_cube.samplers[cube_translation_channel.sampler];
                const cube_rotation_sampler = anim_cube.samplers[cube_rotation_channel.sampler];
                const cube_scale_sampler = anim_cube.samplers[cube_scale_channel.sampler];

                assert.strictEqual(cube_translation_sampler.interpolation, "STEP");
                assert.strictEqual(cube_rotation_sampler.interpolation, "LINEAR");
                assert.strictEqual(cube_scale_sampler.interpolation, "LINEAR");

                assert.strictEqual(asset.accessors[cube_translation_sampler.input].count, 10);
                assert.strictEqual(asset.accessors[cube_rotation_sampler.input].count, 10);
                assert.strictEqual(asset.accessors[cube_scale_sampler.input].count, 10);

                const anim_armature = asset.animations.filter(a => a.name === 'ArmatureAction')[0];
                const bone_node = asset.nodes.filter(a => a.name === "Bone")[0];
                const armature_node = asset.nodes.filter(a => a.name === "Armature")[0];

                const bone_translation_channel = anim_armature.channels.filter(a => asset.nodes[a.target.node].name === bone_node.name).filter(a => a.target.path === "translation")[0];
                const bone_rotation_channel = anim_armature.channels.filter(a => asset.nodes[a.target.node].name === bone_node.name).filter(a => a.target.path === "rotation")[0];
                const bone_scale_channel = anim_armature.channels.filter(a => asset.nodes[a.target.node].name === bone_node.name).filter(a => a.target.path === "scale")[0];

                const bone_translation_sampler = anim_armature.samplers[bone_translation_channel.sampler];
                const bone_rotation_sampler = anim_armature.samplers[bone_rotation_channel.sampler];
                const bone_scale_sampler = anim_armature.samplers[bone_scale_channel.sampler];

                assert.strictEqual(bone_translation_sampler.interpolation, "LINEAR");
                assert.strictEqual(bone_rotation_sampler.interpolation, "STEP");
                assert.strictEqual(bone_scale_sampler.interpolation, "LINEAR");

                assert.strictEqual(asset.accessors[bone_translation_sampler.input].count, 10);
                assert.strictEqual(asset.accessors[bone_rotation_sampler.input].count, 10);
                assert.strictEqual(asset.accessors[bone_scale_sampler.input].count, 10);

                const arma_translation_channel = anim_armature.channels.filter(a => asset.nodes[a.target.node].name === armature_node.name).filter(a => a.target.path === "translation")[0];
                const arma_rotation_channel = anim_armature.channels.filter(a => asset.nodes[a.target.node].name === armature_node.name).filter(a => a.target.path === "rotation")[0];
                const arma_scale_channel = anim_armature.channels.filter(a => asset.nodes[a.target.node].name === armature_node.name).filter(a => a.target.path === "scale")[0];

                const arma_translation_sampler = anim_armature.samplers[arma_translation_channel.sampler];
                const arma_rotation_sampler = anim_armature.samplers[arma_rotation_channel.sampler];
                const arma_scale_sampler = anim_armature.samplers[arma_scale_channel.sampler];

                assert.strictEqual(arma_translation_sampler.interpolation, "LINEAR");
                assert.strictEqual(arma_rotation_sampler.interpolation, "STEP");
                assert.strictEqual(arma_scale_sampler.interpolation, "LINEAR");

                assert.strictEqual(asset.accessors[arma_translation_sampler.input].count, 10);
                assert.strictEqual(asset.accessors[arma_rotation_sampler.input].count, 10);
                assert.strictEqual(asset.accessors[arma_scale_sampler.input].count, 10);

                const anim_suzanne = asset.animations.filter(a => a.name === 'SuzanneAction')[0];

                const suzanne_translation_channel = anim_suzanne.channels.filter(a => a.target.path === "translation")[0];
                const suzanne_rotation_channel = anim_suzanne.channels.filter(a => a.target.path === "rotation")[0];
                const suzanne_scale_channel = anim_suzanne.channels.filter(a => a.target.path === "scale")[0];

                const suzanne_translation_sampler = anim_suzanne.samplers[suzanne_translation_channel.sampler];
                const suzanne_rotation_sampler = anim_suzanne.samplers[suzanne_rotation_channel.sampler];
                const suzanne_scale_sampler = anim_suzanne.samplers[suzanne_scale_channel.sampler];

                assert.strictEqual(suzanne_translation_sampler.interpolation, "LINEAR");
                assert.strictEqual(suzanne_rotation_sampler.interpolation, "STEP");
                assert.strictEqual(suzanne_scale_sampler.interpolation, "STEP");

                assert.strictEqual(asset.accessors[suzanne_translation_sampler.input].count, 1);
                assert.strictEqual(asset.accessors[suzanne_rotation_sampler.input].count, 1);
                assert.strictEqual(asset.accessors[suzanne_scale_sampler.input].count, 1);

                const anim_armature2 = asset.animations.filter(a => a.name === 'Armature.001Action')[0];
                const bone2_node = asset.nodes.filter(a => a.name === "Bone.001")[0];
                const armature2_node = asset.nodes.filter(a => a.name === "Armature.001")[0];

                const bone2_translation_channel = anim_armature2.channels.filter(a => asset.nodes[a.target.node].name === bone2_node.name).filter(a => a.target.path === "translation")[0];
                const bone2_rotation_channel = anim_armature2.channels.filter(a => asset.nodes[a.target.node].name === bone2_node.name).filter(a => a.target.path === "rotation")[0];
                const bone2_scale_channel = anim_armature2.channels.filter(a => asset.nodes[a.target.node].name === bone2_node.name).filter(a => a.target.path === "scale")[0];

                const bone2_translation_sampler = anim_armature2.samplers[bone2_translation_channel.sampler];
                const bone2_rotation_sampler = anim_armature2.samplers[bone2_rotation_channel.sampler];
                const bone2_scale_sampler = anim_armature2.samplers[bone2_scale_channel.sampler];

                assert.strictEqual(bone2_translation_sampler.interpolation, "LINEAR");
                assert.strictEqual(bone2_rotation_sampler.interpolation, "STEP");
                assert.strictEqual(bone2_scale_sampler.interpolation, "STEP");

                assert.strictEqual(asset.accessors[bone2_translation_sampler.input].count, 1);
                assert.strictEqual(asset.accessors[bone2_rotation_sampler.input].count, 1);
                assert.strictEqual(asset.accessors[bone2_scale_sampler.input].count, 1);

                const arma2_translation_channel = anim_armature2.channels.filter(a => asset.nodes[a.target.node].name === armature2_node.name).filter(a => a.target.path === "translation")[0];
                const arma2_rotation_channel = anim_armature2.channels.filter(a => asset.nodes[a.target.node].name === armature2_node.name).filter(a => a.target.path === "rotation")[0];
                const arma2_scale_channel = anim_armature2.channels.filter(a => asset.nodes[a.target.node].name === armature2_node.name).filter(a => a.target.path === "scale")[0];

                const arma2_translation_sampler = anim_armature2.samplers[arma2_translation_channel.sampler];
                const arma2_rotation_sampler = anim_armature2.samplers[arma2_rotation_channel.sampler];
                const arma2_scale_sampler = anim_armature2.samplers[arma2_scale_channel.sampler];

                assert.strictEqual(arma2_translation_sampler.interpolation, "LINEAR");
                assert.strictEqual(arma2_rotation_sampler.interpolation, "STEP");
                assert.strictEqual(arma2_scale_sampler.interpolation, "STEP");

                assert.strictEqual(asset.accessors[arma2_translation_sampler.input].count, 1);
                assert.strictEqual(asset.accessors[arma2_rotation_sampler.input].count, 1);
                assert.strictEqual(asset.accessors[arma2_scale_sampler.input].count, 1);

                const anim_sphere = asset.animations.filter(a => a.name === 'Sphere.001Action')[0];

                const sphere_translation_channel = anim_sphere.channels.filter(a => a.target.path === "translation")[0];
                const sphere_rotation_channel = anim_sphere.channels.filter(a => a.target.path === "rotation")[0];
                const sphere_scale_channel = anim_sphere.channels.filter(a => a.target.path === "scale")[0];

                const sphere_translation_sampler = anim_sphere.samplers[sphere_translation_channel.sampler];
                const sphere_rotation_sampler = anim_sphere.samplers[sphere_rotation_channel.sampler];
                const sphere_scale_sampler = anim_sphere.samplers[sphere_scale_channel.sampler];

                assert.strictEqual(sphere_translation_sampler.interpolation, "STEP");
                assert.strictEqual(sphere_rotation_sampler.interpolation, "STEP");
                assert.strictEqual(sphere_scale_sampler.interpolation, "STEP");

                assert.strictEqual(asset.accessors[sphere_translation_sampler.input].count, 2);
                assert.strictEqual(asset.accessors[sphere_rotation_sampler.input].count, 2);
                assert.strictEqual(asset.accessors[sphere_scale_sampler.input].count, 2);


            });


            it('exports interpolation when sampled, optimized, no keep', function () {
                let gltfPath_1 = path.resolve(outDirPath, '31_interpolation_sampled_no_keep.gltf');
                var asset = JSON.parse(fs.readFileSync(gltfPath_1));

                const anim_cube = asset.animations.filter(a => a.name === 'CubeAction')[0];

                const cube_translation_channel = anim_cube.channels.filter(a => a.target.path === "translation")[0];
                const cube_rotation_channel = anim_cube.channels.filter(a => a.target.path === "rotation")[0];
                const cube_scale_channel = anim_cube.channels.filter(a => a.target.path === "scale")[0];

                const cube_translation_sampler = anim_cube.samplers[cube_translation_channel.sampler];
                const cube_rotation_sampler = anim_cube.samplers[cube_rotation_channel.sampler];
                const cube_scale_sampler = anim_cube.samplers[cube_scale_channel.sampler];

                assert.strictEqual(cube_translation_sampler.interpolation, "STEP");
                assert.strictEqual(cube_rotation_sampler.interpolation, "LINEAR");
                assert.strictEqual(cube_scale_sampler.interpolation, "LINEAR");

                assert.strictEqual(asset.accessors[cube_translation_sampler.input].count, 10);
                assert.strictEqual(asset.accessors[cube_rotation_sampler.input].count, 10);
                assert.strictEqual(asset.accessors[cube_scale_sampler.input].count, 10);

                const anim_armature = asset.animations.filter(a => a.name === 'ArmatureAction')[0];
                const bone_node = asset.nodes.filter(a => a.name === "Bone")[0];
                const armature_node = asset.nodes.filter(a => a.name === "Armature")[0];

                const bone_translation_channel = anim_armature.channels.filter(a => asset.nodes[a.target.node].name === bone_node.name).filter(a => a.target.path === "translation")[0];
                const bone_rotation_channel = anim_armature.channels.filter(a => asset.nodes[a.target.node].name === bone_node.name).filter(a => a.target.path === "rotation")[0];
                const bone_scale_channel = anim_armature.channels.filter(a => asset.nodes[a.target.node].name === bone_node.name).filter(a => a.target.path === "scale")[0];

                const bone_translation_sampler = anim_armature.samplers[bone_translation_channel.sampler];
                const bone_rotation_sampler = anim_armature.samplers[bone_rotation_channel.sampler];
                const bone_scale_sampler = anim_armature.samplers[bone_scale_channel.sampler];

                assert.strictEqual(bone_translation_sampler.interpolation, "LINEAR");
                assert.strictEqual(bone_rotation_sampler.interpolation, "STEP");
                assert.strictEqual(bone_scale_sampler.interpolation, "LINEAR");

                assert.strictEqual(asset.accessors[bone_translation_sampler.input].count, 10);
                assert.strictEqual(asset.accessors[bone_rotation_sampler.input].count, 10);
                assert.strictEqual(asset.accessors[bone_scale_sampler.input].count, 10);

                const arma_translation_channel = anim_armature.channels.filter(a => asset.nodes[a.target.node].name === armature_node.name).filter(a => a.target.path === "translation")[0];
                const arma_rotation_channel = anim_armature.channels.filter(a => asset.nodes[a.target.node].name === armature_node.name).filter(a => a.target.path === "rotation")[0];
                const arma_scale_channel = anim_armature.channels.filter(a => asset.nodes[a.target.node].name === armature_node.name).filter(a => a.target.path === "scale")[0];

                const arma_translation_sampler = anim_armature.samplers[arma_translation_channel.sampler];
                const arma_rotation_sampler = anim_armature.samplers[arma_rotation_channel.sampler];
                const arma_scale_sampler = anim_armature.samplers[arma_scale_channel.sampler];

                assert.strictEqual(arma_translation_sampler.interpolation, "LINEAR");
                assert.strictEqual(arma_rotation_sampler.interpolation, "STEP");
                assert.strictEqual(arma_scale_sampler.interpolation, "LINEAR");

                assert.strictEqual(asset.accessors[arma_translation_sampler.input].count, 10);
                assert.strictEqual(asset.accessors[arma_rotation_sampler.input].count, 10);
                assert.strictEqual(asset.accessors[arma_scale_sampler.input].count, 10);

                const anim_suzanne = asset.animations.filter(a => a.name === 'SuzanneAction')[0];

                const suzanne_translation_channel = anim_suzanne.channels.filter(a => a.target.path === "translation")[0];
                const suzanne_translation_sampler = anim_suzanne.samplers[suzanne_translation_channel.sampler];

                assert.strictEqual(suzanne_translation_sampler.interpolation, "LINEAR");
                assert.strictEqual(asset.accessors[suzanne_translation_sampler.input].count, 1);

                assert.ok(anim_suzanne.channels.filter(a => a.target.path === "rotation").length == 0);
                assert.ok(anim_suzanne.channels.filter(a => a.target.path === "scale").length == 0);

                const anim_armature2 = asset.animations.filter(a => a.name === 'Armature.001Action')[0];
                const bone2_node = asset.nodes.filter(a => a.name === "Bone.001")[0];
                const armature2_node = asset.nodes.filter(a => a.name === "Armature.001")[0];

                const bone2_translation_channel = anim_armature2.channels.filter(a => asset.nodes[a.target.node].name === bone2_node.name).filter(a => a.target.path === "translation")[0];
                const bone2_translation_sampler = anim_armature2.samplers[bone2_translation_channel.sampler];

                assert.strictEqual(bone2_translation_sampler.interpolation, "LINEAR");
                assert.strictEqual(asset.accessors[bone2_translation_sampler.input].count, 1);

                assert.ok(anim_armature2.channels.filter(a => asset.nodes[a.target.node].name === bone2_node.name).filter(a => a.target.path === "rotation").length == 0);
                assert.ok(anim_armature2.channels.filter(a => asset.nodes[a.target.node].name === bone2_node.name).filter(a => a.target.path === "scale").length == 0);

                const arma2_translation_channel = anim_armature2.channels.filter(a => asset.nodes[a.target.node].name === armature2_node.name).filter(a => a.target.path === "translation")[0];
                const arma2_translation_sampler = anim_armature2.samplers[arma2_translation_channel.sampler];

                assert.strictEqual(arma2_translation_sampler.interpolation, "LINEAR");
                assert.strictEqual(asset.accessors[arma2_translation_sampler.input].count, 1);

                assert.ok(anim_armature2.channels.filter(a => asset.nodes[a.target.node].name === armature2_node.name).filter(a => a.target.path === "rotation").length == 0);
                assert.ok(anim_armature2.channels.filter(a => asset.nodes[a.target.node].name === armature2_node.name).filter(a => a.target.path === "scale").length == 0);


                const anim_sphere = asset.animations.filter(a => a.name === 'Sphere.001Action')[0];
                const sphere_translation_channel = anim_sphere.channels.filter(a => a.target.path === "translation")[0];
                const sphere_translation_sampler = anim_sphere.samplers[sphere_translation_channel.sampler];

                assert.strictEqual(sphere_translation_sampler.interpolation, "STEP");
                assert.strictEqual(asset.accessors[sphere_translation_sampler.input].count, 2);

                assert.ok(anim_sphere.channels.filter(a => a.target.path === "rotation").length == 0);
                assert.ok(anim_sphere.channels.filter(a => a.target.path === "scale").length == 0);


            });


            it('exports interpolation when sampled, no optimization, no keeping', function () {
                let gltfPath_1 = path.resolve(outDirPath, '31_interpolation_sampled_no_optimize.gltf');
                var asset = JSON.parse(fs.readFileSync(gltfPath_1));

                const anim_cube = asset.animations.filter(a => a.name === 'CubeAction')[0];

                const cube_translation_channel = anim_cube.channels.filter(a => a.target.path === "translation")[0];
                const cube_rotation_channel = anim_cube.channels.filter(a => a.target.path === "rotation")[0];
                const cube_scale_channel = anim_cube.channels.filter(a => a.target.path === "scale")[0];

                const cube_translation_sampler = anim_cube.samplers[cube_translation_channel.sampler];
                const cube_rotation_sampler = anim_cube.samplers[cube_rotation_channel.sampler];
                const cube_scale_sampler = anim_cube.samplers[cube_scale_channel.sampler];

                assert.strictEqual(cube_translation_sampler.interpolation, "STEP");
                assert.strictEqual(cube_rotation_sampler.interpolation, "LINEAR");
                assert.strictEqual(cube_scale_sampler.interpolation, "LINEAR");

                assert.strictEqual(asset.accessors[cube_translation_sampler.input].count, 10);
                assert.strictEqual(asset.accessors[cube_rotation_sampler.input].count, 10);
                assert.strictEqual(asset.accessors[cube_scale_sampler.input].count, 10);

                const anim_armature = asset.animations.filter(a => a.name === 'ArmatureAction')[0];
                const bone_node = asset.nodes.filter(a => a.name === "Bone")[0];
                const armature_node = asset.nodes.filter(a => a.name === "Armature")[0];

                const bone_translation_channel = anim_armature.channels.filter(a => asset.nodes[a.target.node].name === bone_node.name).filter(a => a.target.path === "translation")[0];
                const bone_rotation_channel = anim_armature.channels.filter(a => asset.nodes[a.target.node].name === bone_node.name).filter(a => a.target.path === "rotation")[0];
                const bone_scale_channel = anim_armature.channels.filter(a => asset.nodes[a.target.node].name === bone_node.name).filter(a => a.target.path === "scale")[0];

                const bone_translation_sampler = anim_armature.samplers[bone_translation_channel.sampler];
                const bone_rotation_sampler = anim_armature.samplers[bone_rotation_channel.sampler];
                const bone_scale_sampler = anim_armature.samplers[bone_scale_channel.sampler];

                assert.strictEqual(bone_translation_sampler.interpolation, "LINEAR");
                assert.strictEqual(bone_rotation_sampler.interpolation, "STEP");
                assert.strictEqual(bone_scale_sampler.interpolation, "LINEAR");

                assert.strictEqual(asset.accessors[bone_translation_sampler.input].count, 10);
                assert.strictEqual(asset.accessors[bone_rotation_sampler.input].count, 10);
                assert.strictEqual(asset.accessors[bone_scale_sampler.input].count, 10);

                const arma_translation_channel = anim_armature.channels.filter(a => asset.nodes[a.target.node].name === armature_node.name).filter(a => a.target.path === "translation")[0];
                const arma_rotation_channel = anim_armature.channels.filter(a => asset.nodes[a.target.node].name === armature_node.name).filter(a => a.target.path === "rotation")[0];
                const arma_scale_channel = anim_armature.channels.filter(a => asset.nodes[a.target.node].name === armature_node.name).filter(a => a.target.path === "scale")[0];

                const arma_translation_sampler = anim_armature.samplers[arma_translation_channel.sampler];
                const arma_rotation_sampler = anim_armature.samplers[arma_rotation_channel.sampler];
                const arma_scale_sampler = anim_armature.samplers[arma_scale_channel.sampler];

                assert.strictEqual(arma_translation_sampler.interpolation, "LINEAR");
                assert.strictEqual(arma_rotation_sampler.interpolation, "STEP");
                assert.strictEqual(arma_scale_sampler.interpolation, "LINEAR");

                assert.strictEqual(asset.accessors[arma_translation_sampler.input].count, 10);
                assert.strictEqual(asset.accessors[arma_rotation_sampler.input].count, 10);
                assert.strictEqual(asset.accessors[arma_scale_sampler.input].count, 10);

                const anim_suzanne = asset.animations.filter(a => a.name === 'SuzanneAction')[0];

                const suzanne_translation_channel = anim_suzanne.channels.filter(a => a.target.path === "translation")[0];
                const suzanne_translation_sampler = anim_suzanne.samplers[suzanne_translation_channel.sampler];

                assert.strictEqual(suzanne_translation_sampler.interpolation, "LINEAR");
                assert.strictEqual(asset.accessors[suzanne_translation_sampler.input].count, 1);

                assert.ok(anim_suzanne.channels.filter(a => a.target.path === "rotation").length == 0);
                assert.ok(anim_suzanne.channels.filter(a => a.target.path === "scale").length == 0);

                const anim_armature2 = asset.animations.filter(a => a.name === 'Armature.001Action')[0];
                const bone2_node = asset.nodes.filter(a => a.name === "Bone.001")[0];
                const armature2_node = asset.nodes.filter(a => a.name === "Armature.001")[0];

                const bone2_translation_channel = anim_armature2.channels.filter(a => asset.nodes[a.target.node].name === bone2_node.name).filter(a => a.target.path === "translation")[0];
                const bone2_translation_sampler = anim_armature2.samplers[bone2_translation_channel.sampler];
                assert.strictEqual(bone2_translation_sampler.interpolation, "LINEAR");
                assert.strictEqual(asset.accessors[bone2_translation_sampler.input].count, 1);

                assert.ok(anim_armature2.channels.filter(a => asset.nodes[a.target.node].name === bone2_node.name).filter(a => a.target.path === "rotation").length == 0);
                assert.ok(anim_armature2.channels.filter(a => asset.nodes[a.target.node].name === bone2_node.name).filter(a => a.target.path === "scale").length == 0);

                assert.ok(anim_armature2.channels.filter(a => asset.nodes[a.target.node].name === armature2_node.name).filter(a => a.target.path === "rotation").length == 0);
                assert.ok(anim_armature2.channels.filter(a => asset.nodes[a.target.node].name === armature2_node.name).filter(a => a.target.path === "scale").length == 0);


                const arma2_translation_channel = anim_armature2.channels.filter(a => asset.nodes[a.target.node].name === armature2_node.name).filter(a => a.target.path === "translation")[0];
                const arma2_translation_sampler = anim_armature2.samplers[arma2_translation_channel.sampler];
                assert.strictEqual(arma2_translation_sampler.interpolation, "LINEAR");
                assert.strictEqual(asset.accessors[arma2_translation_sampler.input].count, 1);


                const anim_sphere = asset.animations.filter(a => a.name === 'Sphere.001Action')[0];

                const sphere_translation_channel = anim_sphere.channels.filter(a => a.target.path === "translation")[0];
                const sphere_translation_sampler = anim_sphere.samplers[sphere_translation_channel.sampler];
                assert.strictEqual(sphere_translation_sampler.interpolation, "LINEAR");
                assert.strictEqual(asset.accessors[sphere_translation_sampler.input].count, 6);

                assert.ok(anim_sphere.channels.filter(a => a.target.path === "rotation").length == 0);
                assert.ok(anim_sphere.channels.filter(a => a.target.path === "scale").length == 0);

            });

            it('exports interpolation when sampled, not optimized, but keep', function () {
                let gltfPath_1 = path.resolve(outDirPath, '31_interpolation_sampled_no_optimize_but_keep.gltf');
                var asset = JSON.parse(fs.readFileSync(gltfPath_1));

                const anim_cube = asset.animations.filter(a => a.name === 'CubeAction')[0];

                const cube_translation_channel = anim_cube.channels.filter(a => a.target.path === "translation")[0];
                const cube_rotation_channel = anim_cube.channels.filter(a => a.target.path === "rotation")[0];
                const cube_scale_channel = anim_cube.channels.filter(a => a.target.path === "scale")[0];

                const cube_translation_sampler = anim_cube.samplers[cube_translation_channel.sampler];
                const cube_rotation_sampler = anim_cube.samplers[cube_rotation_channel.sampler];
                const cube_scale_sampler = anim_cube.samplers[cube_scale_channel.sampler];

                assert.strictEqual(cube_translation_sampler.interpolation, "STEP");
                assert.strictEqual(cube_rotation_sampler.interpolation, "LINEAR");
                assert.strictEqual(cube_scale_sampler.interpolation, "LINEAR");

                assert.strictEqual(asset.accessors[cube_translation_sampler.input].count, 10);
                assert.strictEqual(asset.accessors[cube_rotation_sampler.input].count, 10);
                assert.strictEqual(asset.accessors[cube_scale_sampler.input].count, 10);

                const anim_armature = asset.animations.filter(a => a.name === 'ArmatureAction')[0];
                const bone_node = asset.nodes.filter(a => a.name === "Bone")[0];
                const armature_node = asset.nodes.filter(a => a.name === "Armature")[0];

                const bone_translation_channel = anim_armature.channels.filter(a => asset.nodes[a.target.node].name === bone_node.name).filter(a => a.target.path === "translation")[0];
                const bone_rotation_channel = anim_armature.channels.filter(a => asset.nodes[a.target.node].name === bone_node.name).filter(a => a.target.path === "rotation")[0];
                const bone_scale_channel = anim_armature.channels.filter(a => asset.nodes[a.target.node].name === bone_node.name).filter(a => a.target.path === "scale")[0];

                const bone_translation_sampler = anim_armature.samplers[bone_translation_channel.sampler];
                const bone_rotation_sampler = anim_armature.samplers[bone_rotation_channel.sampler];
                const bone_scale_sampler = anim_armature.samplers[bone_scale_channel.sampler];

                assert.strictEqual(bone_translation_sampler.interpolation, "LINEAR");
                assert.strictEqual(bone_rotation_sampler.interpolation, "STEP");
                assert.strictEqual(bone_scale_sampler.interpolation, "LINEAR");

                assert.strictEqual(asset.accessors[bone_translation_sampler.input].count, 10);
                assert.strictEqual(asset.accessors[bone_rotation_sampler.input].count, 10);
                assert.strictEqual(asset.accessors[bone_scale_sampler.input].count, 10);

                const arma_translation_channel = anim_armature.channels.filter(a => asset.nodes[a.target.node].name === armature_node.name).filter(a => a.target.path === "translation")[0];
                const arma_rotation_channel = anim_armature.channels.filter(a => asset.nodes[a.target.node].name === armature_node.name).filter(a => a.target.path === "rotation")[0];
                const arma_scale_channel = anim_armature.channels.filter(a => asset.nodes[a.target.node].name === armature_node.name).filter(a => a.target.path === "scale")[0];

                const arma_translation_sampler = anim_armature.samplers[arma_translation_channel.sampler];
                const arma_rotation_sampler = anim_armature.samplers[arma_rotation_channel.sampler];
                const arma_scale_sampler = anim_armature.samplers[arma_scale_channel.sampler];

                assert.strictEqual(arma_translation_sampler.interpolation, "LINEAR");
                assert.strictEqual(arma_rotation_sampler.interpolation, "STEP");
                assert.strictEqual(arma_scale_sampler.interpolation, "LINEAR");

                assert.strictEqual(asset.accessors[arma_translation_sampler.input].count, 10);
                assert.strictEqual(asset.accessors[arma_rotation_sampler.input].count, 10);
                assert.strictEqual(asset.accessors[arma_scale_sampler.input].count, 10);

                const anim_suzanne = asset.animations.filter(a => a.name === 'SuzanneAction')[0];

                const suzanne_translation_channel = anim_suzanne.channels.filter(a => a.target.path === "translation")[0];
                const suzanne_rotation_channel = anim_suzanne.channels.filter(a => a.target.path === "rotation")[0];
                const suzanne_scale_channel = anim_suzanne.channels.filter(a => a.target.path === "scale")[0];

                const suzanne_translation_sampler = anim_suzanne.samplers[suzanne_translation_channel.sampler];
                const suzanne_rotation_sampler = anim_suzanne.samplers[suzanne_rotation_channel.sampler];
                const suzanne_scale_sampler = anim_suzanne.samplers[suzanne_scale_channel.sampler];

                assert.strictEqual(suzanne_translation_sampler.interpolation, "LINEAR");
                assert.strictEqual(suzanne_rotation_sampler.interpolation, "STEP");
                assert.strictEqual(suzanne_scale_sampler.interpolation, "STEP");

                assert.strictEqual(asset.accessors[suzanne_translation_sampler.input].count, 1);
                assert.strictEqual(asset.accessors[suzanne_rotation_sampler.input].count, 1);
                assert.strictEqual(asset.accessors[suzanne_scale_sampler.input].count, 1);

                const anim_armature2 = asset.animations.filter(a => a.name === 'Armature.001Action')[0];
                const bone2_node = asset.nodes.filter(a => a.name === "Bone.001")[0];
                const armature2_node = asset.nodes.filter(a => a.name === "Armature.001")[0];

                const bone2_translation_channel = anim_armature2.channels.filter(a => asset.nodes[a.target.node].name === bone2_node.name).filter(a => a.target.path === "translation")[0];
                const bone2_rotation_channel = anim_armature2.channels.filter(a => asset.nodes[a.target.node].name === bone2_node.name).filter(a => a.target.path === "rotation")[0];
                const bone2_scale_channel = anim_armature2.channels.filter(a => asset.nodes[a.target.node].name === bone2_node.name).filter(a => a.target.path === "scale")[0];

                const bone2_translation_sampler = anim_armature2.samplers[bone2_translation_channel.sampler];
                const bone2_rotation_sampler = anim_armature2.samplers[bone2_rotation_channel.sampler];
                const bone2_scale_sampler = anim_armature2.samplers[bone2_scale_channel.sampler];

                assert.strictEqual(bone2_translation_sampler.interpolation, "LINEAR");
                assert.strictEqual(bone2_rotation_sampler.interpolation, "STEP");
                assert.strictEqual(bone2_scale_sampler.interpolation, "STEP");

                assert.strictEqual(asset.accessors[bone2_translation_sampler.input].count, 1);
                assert.strictEqual(asset.accessors[bone2_rotation_sampler.input].count, 1);
                assert.strictEqual(asset.accessors[bone2_scale_sampler.input].count, 1);

                const arma2_translation_channel = anim_armature2.channels.filter(a => asset.nodes[a.target.node].name === armature2_node.name).filter(a => a.target.path === "translation")[0];
                const arma2_rotation_channel = anim_armature2.channels.filter(a => asset.nodes[a.target.node].name === armature2_node.name).filter(a => a.target.path === "rotation")[0];
                const arma2_scale_channel = anim_armature2.channels.filter(a => asset.nodes[a.target.node].name === armature2_node.name).filter(a => a.target.path === "scale")[0];

                const arma2_translation_sampler = anim_armature2.samplers[arma2_translation_channel.sampler];
                const arma2_rotation_sampler = anim_armature2.samplers[arma2_rotation_channel.sampler];
                const arma2_scale_sampler = anim_armature2.samplers[arma2_scale_channel.sampler];

                assert.strictEqual(arma2_translation_sampler.interpolation, "LINEAR");
                assert.strictEqual(arma2_rotation_sampler.interpolation, "STEP");
                assert.strictEqual(arma2_scale_sampler.interpolation, "STEP");

                assert.strictEqual(asset.accessors[arma2_translation_sampler.input].count, 1);
                assert.strictEqual(asset.accessors[arma2_rotation_sampler.input].count, 1);
                assert.strictEqual(asset.accessors[arma2_scale_sampler.input].count, 1);

                const anim_sphere = asset.animations.filter(a => a.name === 'Sphere.001Action')[0];

                const sphere_translation_channel = anim_sphere.channels.filter(a => a.target.path === "translation")[0];
                const sphere_rotation_channel = anim_sphere.channels.filter(a => a.target.path === "rotation")[0];
                const sphere_scale_channel = anim_sphere.channels.filter(a => a.target.path === "scale")[0];

                const sphere_translation_sampler = anim_sphere.samplers[sphere_translation_channel.sampler];
                const sphere_rotation_sampler = anim_sphere.samplers[sphere_rotation_channel.sampler];
                const sphere_scale_sampler = anim_sphere.samplers[sphere_scale_channel.sampler];

                assert.strictEqual(sphere_translation_sampler.interpolation, "LINEAR");
                assert.strictEqual(sphere_rotation_sampler.interpolation, "LINEAR");
                assert.strictEqual(sphere_scale_sampler.interpolation, "LINEAR");

                assert.strictEqual(asset.accessors[sphere_translation_sampler.input].count, 6);
                assert.strictEqual(asset.accessors[sphere_rotation_sampler.input].count, 6);
                assert.strictEqual(asset.accessors[sphere_rotation_sampler.input].count, 6);

            });

            it('exports without gpu instancing', function () {
                let gltfPath = path.resolve(outDirPath, '32_gpu_instancing_without_instancing.gltf');
                var asset = JSON.parse(fs.readFileSync(gltfPath));

                assert.strictEqual(asset.nodes.length, 13);
                assert.strictEqual(asset.meshes.length, 7);
                assert.ok(asset.extensionsUsed == null);

            });

            it('exports with gpu instancing', function () {
                let gltfPath = path.resolve(outDirPath, '32_gpu_instancing_with_instancing.gltf');
                var asset = JSON.parse(fs.readFileSync(gltfPath));

                assert.strictEqual(asset.nodes.length, 9);
                assert.strictEqual(asset.meshes.length, 7);
                assert.ok(!(asset.extensionsUsed == null));
                const holder_nodes = asset.nodes.filter(a => a.extensions != null);
                assert.strictEqual(holder_nodes.length, 2);

                const node_0 = holder_nodes.filter(a => a.name === "Empty.0")[0];
                const node_1 = holder_nodes.filter(a => a.name === "Empty.1")[0];

                const data_0_t = asset.accessors[node_0.extensions["EXT_mesh_gpu_instancing"]["attributes"]["TRANSLATION"]];
                const data_0_r = asset.accessors[node_0.extensions["EXT_mesh_gpu_instancing"]["attributes"]["ROTATION"]];
                const data_0_s = asset.accessors[node_0.extensions["EXT_mesh_gpu_instancing"]["attributes"]["SCALE"]];

                const data_1_t = asset.accessors[node_1.extensions["EXT_mesh_gpu_instancing"]["attributes"]["TRANSLATION"]];
                const data_1_r = asset.accessors[node_1.extensions["EXT_mesh_gpu_instancing"]["attributes"]["ROTATION"]];
                const data_1_s = asset.accessors[node_1.extensions["EXT_mesh_gpu_instancing"]["attributes"]["SCALE"]];

                assert.strictEqual(data_0_t.count, 3);
                assert.strictEqual(data_0_r.count, 3);
                assert.strictEqual(data_0_s.count, 3);

                assert.strictEqual(data_1_t.count, 4);
                assert.strictEqual(data_1_r.count, 4);
                assert.strictEqual(data_1_s.count, 4);


            });

            it('exports all influences', function () {

                let gltfPath = path.resolve(outDirPath, '32_weights_influence_all.gltf');
                var asset = JSON.parse(fs.readFileSync(gltfPath));

                let bufferCache = {};

                const m1 = asset.meshes.filter(m => m.name === 'Plane')[0].primitives[0];
                const m2 = asset.meshes.filter(m => m.name === 'Plane.001')[0].primitives[0];
                const m3 = asset.meshes.filter(m => m.name === 'Plane.002')[0].primitives[0];

                assert.ok("JOINTS_0" in m1['attributes']);
                assert.ok(!("JOINTS_1" in m1['attributes']));

                const m1_weights_0 = getAccessorData(gltfPath, asset, m1['attributes']['WEIGHTS_0'], bufferCache);
                assert.equalEpsilonArray(m1_weights_0, [1.0, 0.0, 0.0, 0.0]);


                assert.ok("JOINTS_0" in m2['attributes']);
                assert.ok("JOINTS_1" in m2['attributes']);
                assert.ok(!("JOINTS_2" in m2['attributes']));

                const m2_weights_0 = getAccessorData(gltfPath, asset, m2['attributes']['WEIGHTS_0'], bufferCache);
                const m2_weights_1 = getAccessorData(gltfPath, asset, m2['attributes']['WEIGHTS_1'], bufferCache);

                assert.equalEpsilonArray(m2_weights_0, [0.2, 0.2, 0.2, 0.2]);
                assert.equalEpsilonArray(m2_weights_1, [0.2, 0.0, 0.0, 0.0]);

                assert.ok("JOINTS_0" in m3['attributes']);
                assert.ok("JOINTS_1" in m3['attributes']);
                assert.ok("JOINTS_2" in m3['attributes']);
                assert.ok(!("JOINTS_3" in m3['attributes']));

                const m3_weights_0 = getAccessorData(gltfPath, asset, m3['attributes']['WEIGHTS_0'], bufferCache);
                const m3_weights_1 = getAccessorData(gltfPath, asset, m3['attributes']['WEIGHTS_1'], bufferCache);
                const m3_weights_2 = getAccessorData(gltfPath, asset, m3['attributes']['WEIGHTS_2'], bufferCache);

                assert.equalEpsilonArray(m3_weights_0, [0.1, 0.1, 0.1, 0.1]);
                assert.equalEpsilonArray(m3_weights_1, [0.1, 0.1, 0.1, 0.1]);
                assert.equalEpsilonArray(m3_weights_2, [0.1, 0.1, 0.0, 0.0]);

            });

            it('exports 4 influences', function () {

                let gltfPath = path.resolve(outDirPath, '32_weights_influence_4.gltf');
                var asset = JSON.parse(fs.readFileSync(gltfPath));

                let bufferCache = {};

                const m1 = asset.meshes.filter(m => m.name === 'Plane')[0].primitives[0];
                const m2 = asset.meshes.filter(m => m.name === 'Plane.001')[0].primitives[0];
                const m3 = asset.meshes.filter(m => m.name === 'Plane.002')[0].primitives[0];

                assert.ok("JOINTS_0" in m1['attributes']);
                assert.ok(!("JOINTS_1" in m1['attributes']));

                const m1_weights_0 = getAccessorData(gltfPath, asset, m1['attributes']['WEIGHTS_0'], bufferCache);
                assert.equalEpsilonArray(m1_weights_0, [1.0, 0.0, 0.0, 0.0]);


                assert.ok("JOINTS_0" in m2['attributes']);
                assert.ok(!("JOINTS_1" in m2['attributes']));

                const m2_weights_0 = getAccessorData(gltfPath, asset, m2['attributes']['WEIGHTS_0'], bufferCache);
                assert.equalEpsilonArray(m2_weights_0, [0.4, 0.3, 0.2, 0.1]);

                assert.ok("JOINTS_0" in m3['attributes']);
                assert.ok(!("JOINTS_1" in m3['attributes']));

                const m3_weights_0 = getAccessorData(gltfPath, asset, m3['attributes']['WEIGHTS_0'], bufferCache);

                assert.equalEpsilonArray(m3_weights_0, [0.4, 0.3, 0.2, 0.1]);

            });

            it('exports 6 influences', function () {

                let gltfPath = path.resolve(outDirPath, '32_weights_influence_6.gltf');
                var asset = JSON.parse(fs.readFileSync(gltfPath));

                let bufferCache = {};

                const m1 = asset.meshes.filter(m => m.name === 'Plane')[0].primitives[0];
                const m2 = asset.meshes.filter(m => m.name === 'Plane.001')[0].primitives[0];
                const m3 = asset.meshes.filter(m => m.name === 'Plane.002')[0].primitives[0];

                assert.ok("JOINTS_0" in m1['attributes']);
                assert.ok(!("JOINTS_1" in m1['attributes']));

                const m1_weights_0 = getAccessorData(gltfPath, asset, m1['attributes']['WEIGHTS_0'], bufferCache);
                assert.equalEpsilonArray(m1_weights_0, [1.0, 0.0, 0.0, 0.0]);


                assert.ok("JOINTS_0" in m2['attributes']);
                assert.ok("JOINTS_1" in m2['attributes']);
                assert.ok(!("JOINTS_2" in m2['attributes']));

                const m2_weights_0 = getAccessorData(gltfPath, asset, m2['attributes']['WEIGHTS_0'], bufferCache);
                const m2_weights_1 = getAccessorData(gltfPath, asset, m2['attributes']['WEIGHTS_1'], bufferCache);
                assert.equalEpsilonArray(m2_weights_0, [0.4, 0.3, 0.1, 0.1]);
                assert.equalEpsilonArray(m2_weights_1, [0.1, 0.0, 0.0, 0.0]);

                assert.ok("JOINTS_0" in m3['attributes']);
                assert.ok("JOINTS_1" in m3['attributes']);
                assert.ok(!("JOINTS_2" in m3['attributes']));

                const m3_weights_0 = getAccessorData(gltfPath, asset, m3['attributes']['WEIGHTS_0'], bufferCache);
                const m3_weights_1 = getAccessorData(gltfPath, asset, m3['attributes']['WEIGHTS_1'], bufferCache);

                assert.equalEpsilonArray(m3_weights_0, [0.2, 0.2, 0.2, 0.2]);
                assert.equalEpsilonArray(m3_weights_1, [0.1, 0.1, 0.0, 0.0]);

            });

            it('exports 9 influences', function () {

                let gltfPath = path.resolve(outDirPath, '32_weights_influence_9.gltf');
                var asset = JSON.parse(fs.readFileSync(gltfPath));

                let bufferCache = {};

                const m1 = asset.meshes.filter(m => m.name === 'Plane')[0].primitives[0];
                const m2 = asset.meshes.filter(m => m.name === 'Plane.001')[0].primitives[0];
                const m3 = asset.meshes.filter(m => m.name === 'Plane.002')[0].primitives[0];

                assert.ok("JOINTS_0" in m1['attributes']);
                assert.ok(!("JOINTS_1" in m1['attributes']));

                const m1_weights_0 = getAccessorData(gltfPath, asset, m1['attributes']['WEIGHTS_0'], bufferCache);
                assert.equalEpsilonArray(m1_weights_0, [1.0, 0.0, 0.0, 0.0]);


                assert.ok("JOINTS_0" in m2['attributes']);
                assert.ok("JOINTS_1" in m2['attributes']);
                assert.ok(!("JOINTS_2" in m2['attributes']));

                const m2_weights_0 = getAccessorData(gltfPath, asset, m2['attributes']['WEIGHTS_0'], bufferCache);
                const m2_weights_1 = getAccessorData(gltfPath, asset, m2['attributes']['WEIGHTS_1'], bufferCache);
                assert.equalEpsilonArray(m2_weights_0, [0.4, 0.3, 0.1, 0.1]);
                assert.equalEpsilonArray(m2_weights_1, [0.1, 0.0, 0.0, 0.0]);

                assert.ok("JOINTS_0" in m3['attributes']);
                assert.ok("JOINTS_1" in m3['attributes']);
                assert.ok("JOINTS_2" in m3['attributes']);
                assert.ok(!("JOINTS_3" in m3['attributes']));

                const m3_weights_0 = getAccessorData(gltfPath, asset, m3['attributes']['WEIGHTS_0'], bufferCache);
                const m3_weights_1 = getAccessorData(gltfPath, asset, m3['attributes']['WEIGHTS_1'], bufferCache);
                const m3_weights_2 = getAccessorData(gltfPath, asset, m3['attributes']['WEIGHTS_2'], bufferCache);

                assert.equalEpsilonArray(m3_weights_0, [0.2, 0.1, 0.1, 0.1]);
                assert.equalEpsilonArray(m3_weights_1, [0.1, 0.1, 0.1, 0.1]);
                assert.equalEpsilonArray(m3_weights_2, [0.1, 0.0, 0.0, 0.0]);

            });

            it('exports Custom Attribute UVMaps', function () {
                let gltfPath = path.resolve(outDirPath, '32_custom_uvmap_attribute.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));

                assert.strictEqual(asset.materials.length, 2);
                const material_0 = asset.materials[asset.meshes.filter(a => a.name == "Cube.001")[0].primitives[0]["material"]]
                const material_1 = asset.materials[asset.meshes.filter(a => a.name == "Cube.002")[0].primitives[0]["material"]]
                assert.strictEqual(material_0.pbrMetallicRoughness["baseColorTexture"]["index"], 0);
                assert.strictEqual(material_0.pbrMetallicRoughness["baseColorTexture"]["texCoord"], 5);
                assert.strictEqual(material_1.pbrMetallicRoughness["baseColorTexture"]["index"], 0);
                assert.strictEqual(material_1.pbrMetallicRoughness["baseColorTexture"]["texCoord"], 1);

            });

            it('exports UVMaps texcoord', function () {
                let gltfPath = path.resolve(outDirPath, '32_uvmap_indices.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));

                assert.strictEqual(asset.images.length, 1);
                assert.strictEqual(asset.meshes.length, 6);
                assert.strictEqual(asset.materials.length, 6);

                const material_0 = asset.materials[asset.meshes[asset.nodes.filter(a => a.name == "Cube")[0].mesh].primitives[0]["material"]]
                const material_1 = asset.materials[asset.meshes[asset.nodes.filter(a => a.name == "Cube.003")[0].mesh].primitives[0]["material"]]
                const material_2 = asset.materials[asset.meshes[asset.nodes.filter(a => a.name == "Cube.001")[0].mesh].primitives[0]["material"]]
                const material_3 = asset.materials[asset.meshes[asset.nodes.filter(a => a.name == "Cube.002")[0].mesh].primitives[0]["material"]]
                const material_4 = asset.materials[asset.meshes[asset.nodes.filter(a => a.name == "Plane")[0].mesh].primitives[0]["material"]]
                const material_5 = asset.materials[asset.meshes[asset.nodes.filter(a => a.name == "Plane.001")[0].mesh].primitives[0]["material"]]


                assert.ok(!("texCoord" in material_0.emissiveTexture));
                assert.strictEqual(material_1.emissiveTexture["texCoord"], 1);
                assert.strictEqual(material_2.emissiveTexture["texCoord"], 1);
                assert.ok(!("texCoord" in material_3.emissiveTexture));
                assert.strictEqual(material_4.pbrMetallicRoughness["baseColorTexture"]["texCoord"], 1);
                assert.ok(!("texCoord" in material_5.pbrMetallicRoughness["baseColorTexture"]));

            });

            it('exports WebP mode', function () {
                let gltfPath_1 = path.resolve(outDirPath, '32_webp_mode_webp.gltf');
                var asset = JSON.parse(fs.readFileSync(gltfPath_1));

                for (var i = 0; i < asset.images.length; i++) {
                    assert.strictEqual(asset.images[i].mimeType, 'image/webp');
                }

                for (var i = 0; i < asset.textures.length; i++) {
                    assert.strictEqual(asset.textures[i].source, undefined);
                    assert.ok("extensions" in asset.textures[i]);
                }

            });

            it('exports auto mode + webp fallback', function () {
                let gltfPath_1 = path.resolve(outDirPath, '32_webp_mode_auto_with_fallback.gltf');
                var asset = JSON.parse(fs.readFileSync(gltfPath_1));

                var texture_webp = asset.materials[0].pbrMetallicRoughness.baseColorTexture.index;

                for (var i = 0; i < asset.textures.length; i++) {
                    if (i == texture_webp) {
                        assert.ok("extensions" in asset.textures[i]);
                        assert.ok(asset.textures[i].source != undefined);
                    } else {
                        assert.ok(asset.textures[i].source != undefined);
                        assert.ok(!("extensions" in asset.textures[i]));
                    }
                }
            });

            it('exports auto mode + create WebP', function () {
                let gltfPath_1 = path.resolve(outDirPath, '32_webp_mode_auto_with_create_webp.gltf');
                var asset = JSON.parse(fs.readFileSync(gltfPath_1));

                var texture_webp = asset.materials[0].pbrMetallicRoughness.baseColorTexture.index;

                for (var i = 0; i < asset.textures.length; i++) {
                    if (i == texture_webp) {
                        assert.ok("extensions" in asset.textures[i]);
                        assert.strictEqual(asset.textures[i].source, undefined);
                    } else {
                        assert.ok(asset.textures[i].source != undefined);
                        assert.ok("extensions" in asset.textures[i]);
                    }
                }
            });

            it('exports auto mode + create WebP + fallback', function () {
                let gltfPath_1 = path.resolve(outDirPath, '32_webp_mode_auto_with_fallback_and_create_webp.gltf');
                var asset = JSON.parse(fs.readFileSync(gltfPath_1));

                for (var i = 0; i < asset.textures.length; i++) {
                    assert.ok("extensions" in asset.textures[i]);
                    assert.ok(asset.textures[i].source != undefined);
                }
            });

            it('exports UDIM', function () {
                let gltfPath_1 = path.resolve(outDirPath, '33_udim.gltf');
                var asset = JSON.parse(fs.readFileSync(gltfPath_1));

                assert.strictEqual(asset.images.length, 15);
                assert.strictEqual(asset.meshes.length, 1);
                assert.strictEqual(asset.meshes[0].primitives.length, 4);
                assert.strictEqual(asset.materials.length, 4);
                assert.strictEqual(asset.textures.length, 20);
            });

            // These tests are disabled because they require an user extension to be registered
            /*it('exports addtional textures & images', function() {
                let gltfPath_1 = path.resolve(outDirPath, '33_unused_texture_and_image.gltf');
                var asset = JSON.parse(fs.readFileSync(gltfPath_1));

                assert.strictEqual(asset.images.length, 3);
                assert.strictEqual(asset.textures.length, 2);
                assert.strictEqual(asset.materials.length, 1);
                assert.strictEqual(asset.extras['additionalTextures'].length, 1);
            });

            it('exports addtional textures', function() {
                let gltfPath_1 = path.resolve(outDirPath, '33_unused_texture.gltf');
                var asset = JSON.parse(fs.readFileSync(gltfPath_1));

                assert.strictEqual(asset.images.length, 2);
                assert.strictEqual(asset.textures.length, 2);
                assert.strictEqual(asset.materials.length, 1);
                assert.strictEqual(asset.extras['additionalTextures'].length, 1);
            });
            */

            it('exports addtional images', function () {
                let gltfPath_1 = path.resolve(outDirPath, '33_unused_image.gltf');
                var asset = JSON.parse(fs.readFileSync(gltfPath_1));

                assert.strictEqual(asset.images.length, 3);
                assert.strictEqual(asset.textures.length, 1);
                assert.strictEqual(asset.materials.length, 1);
                assert.ok(!("extras" in asset));
            });

            it('exports no addtional images & textures', function () {
                let gltfPath_1 = path.resolve(outDirPath, '33_no_unused_texture_and_image.gltf');
                var asset = JSON.parse(fs.readFileSync(gltfPath_1));

                assert.strictEqual(asset.images.length, 1);
                assert.strictEqual(asset.textures.length, 1);
                assert.strictEqual(asset.materials.length, 1);
                assert.ok(!("extras" in asset));
            });

            it('exports vertex color - None', function () {
                let gltfPath = path.resolve(outDirPath, '24_vertex_color_and_factor_none.gltf');
                var asset = JSON.parse(fs.readFileSync(gltfPath));

                // loop on each primitive, check if the vertex color is present
                for (var i = 0; i < asset.meshes.length; i++) {
                    assert.ok(!("COLOR_0" in asset.meshes[i].primitives[0].attributes));
                }
            });

            it('exports vertex color - Active - Not all - export without mat', function () {
                let gltfPath = path.resolve(outDirPath, '24_vertex_color_and_factor_active_not_all.gltf');
                var asset = JSON.parse(fs.readFileSync(gltfPath));

                let bufferCache = {};

                let primitive = asset.meshes[asset.nodes.filter(a => a.name == "no_mat_no_vc")[0].mesh].primitives[0];
                assert.ok(!("COLOR_0" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "no_mat_1_vc")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                assert.ok(!("COLOR_1" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "no_mat_2_vc_act0")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                assert.ok(!("COLOR_1" in primitive.attributes));
                let colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "no_mat_2_vc_act1")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                assert.ok(!("COLOR_1" in primitive.attributes));
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 1.0]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_wo_no_vc")[0].mesh].primitives[0];
                assert.ok(!("COLOR_0" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_wo_1_vc")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                assert.ok(!("COLOR_1" in primitive.attributes));
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_wo_2_vc_act0")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                assert.ok(!("COLOR_1" in primitive.attributes));
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_wo_2_vc_act1")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                assert.ok(!("COLOR_1" in primitive.attributes));
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 1.0]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_no_vc")[0].mesh].primitives[0];
                assert.ok(!("COLOR_0" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_1_vc_act")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                assert.ok(!("COLOR_1" in primitive.attributes));
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_2_vc_act0")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                assert.ok(!("COLOR_1" in primitive.attributes));
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_2_vc_act1")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                assert.ok(!("COLOR_1" in primitive.attributes));
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 1.0]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_1_vc_named")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                assert.ok(!("COLOR_1" in primitive.attributes));
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_2_vc_named0_act1")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                assert.ok(!("COLOR_1" in primitive.attributes));
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_2_vc_named1_act1")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                assert.ok(!("COLOR_1" in primitive.attributes));
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 1.0]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_2_vc_named0_act0")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                assert.ok(!("COLOR_1" in primitive.attributes));
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_2_vc_named1_act0")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                assert.ok(!("COLOR_1" in primitive.attributes));
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 1.0]);

            });

            it('exports vertex color - Active - Not all - no export without mat', function () {
                let gltfPath = path.resolve(outDirPath, '24_vertex_color_and_factor_active_not_all_no_nomat.gltf');
                var asset = JSON.parse(fs.readFileSync(gltfPath));

                let bufferCache = {};

                let primitive = asset.meshes[asset.nodes.filter(a => a.name == "no_mat_no_vc")[0].mesh].primitives[0];
                assert.ok(!("COLOR_0" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "no_mat_1_vc")[0].mesh].primitives[0];
                assert.ok(!("COLOR_0" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "no_mat_2_vc_act0")[0].mesh].primitives[0];
                assert.ok(!("COLOR_0" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "no_mat_2_vc_act1")[0].mesh].primitives[0];
                assert.ok(!("COLOR_0" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_wo_no_vc")[0].mesh].primitives[0];
                assert.ok(!("COLOR_0" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_wo_1_vc")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                assert.ok(!("COLOR_1" in primitive.attributes));
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_wo_2_vc_act0")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                assert.ok(!("COLOR_1" in primitive.attributes));
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_wo_2_vc_act1")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                assert.ok(!("COLOR_1" in primitive.attributes));
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 1.0]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_no_vc")[0].mesh].primitives[0];
                assert.ok(!("COLOR_0" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_1_vc_act")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                assert.ok(!("COLOR_1" in primitive.attributes));
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_2_vc_act0")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                assert.ok(!("COLOR_1" in primitive.attributes));
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_2_vc_act1")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                assert.ok(!("COLOR_1" in primitive.attributes));
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 1.0]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_1_vc_named")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                assert.ok(!("COLOR_1" in primitive.attributes));
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_2_vc_named0_act1")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                assert.ok(!("COLOR_1" in primitive.attributes));
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 0.1]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_2_vc_named1_act1")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                assert.ok(!("COLOR_1" in primitive.attributes));
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 1.0]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_2_vc_named0_act0")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                assert.ok(!("COLOR_1" in primitive.attributes));
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_2_vc_named1_act0")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                assert.ok(!("COLOR_1" in primitive.attributes));
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);

            });

            it('exports vertex color - Active - All - no export without mat', function () {
                let gltfPath = path.resolve(outDirPath, '24_vertex_color_and_factor_active_all_no_nomat.gltf');
                var asset = JSON.parse(fs.readFileSync(gltfPath));

                let bufferCache = {};

                let primitive = asset.meshes[asset.nodes.filter(a => a.name == "no_mat_no_vc")[0].mesh].primitives[0];
                assert.ok(!("COLOR_0" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "no_mat_1_vc")[0].mesh].primitives[0];
                assert.ok(!("COLOR_0" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "no_mat_2_vc_act0")[0].mesh].primitives[0];
                assert.ok(!("COLOR_0" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "no_mat_2_vc_act1")[0].mesh].primitives[0];
                assert.ok(!("COLOR_0" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_wo_no_vc")[0].mesh].primitives[0];
                assert.ok(!("COLOR_0" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_wo_1_vc")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                assert.ok(!("COLOR_1" in primitive.attributes));
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_wo_2_vc_act0")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                assert.ok("COLOR_1" in primitive.attributes);
                assert.ok(!("COLOR_2" in primitive.attributes));
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_1, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 1.0]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_wo_2_vc_act1")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                assert.ok("COLOR_1" in primitive.attributes);
                assert.ok(!("COLOR_2" in primitive.attributes));
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 1.0]);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_1, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_no_vc")[0].mesh].primitives[0];
                assert.ok(!("COLOR_0" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_1_vc_act")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                assert.ok(!("COLOR_1" in primitive.attributes));
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_2_vc_act0")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                assert.ok("COLOR_1" in primitive.attributes);
                assert.ok(!("COLOR_2" in primitive.attributes));
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_1, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 1.0]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_2_vc_act1")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                assert.ok("COLOR_1" in primitive.attributes);
                assert.ok(!("COLOR_2" in primitive.attributes));
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 1.0]);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_1, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_1_vc_named")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                assert.ok(!("COLOR_1" in primitive.attributes));
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_2_vc_named0_act1")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                assert.ok("COLOR_1" in primitive.attributes);
                assert.ok(!("COLOR_2" in primitive.attributes));
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 1.0]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_2_vc_named1_act1")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                assert.ok("COLOR_1" in primitive.attributes);
                assert.ok(!("COLOR_2" in primitive.attributes));
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 1.0]);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_1, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_2_vc_named0_act0")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                assert.ok("COLOR_1" in primitive.attributes);
                assert.ok(!("COLOR_2" in primitive.attributes));
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_1, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 1.0]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_2_vc_named1_act0")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                assert.ok("COLOR_1" in primitive.attributes);
                assert.ok(!("COLOR_2" in primitive.attributes));
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_1, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 1.0]);

            });

            it('exports vertex color - Active - All - with export without mat', function () {
                let gltfPath = path.resolve(outDirPath, '24_vertex_color_and_factor_active_all_with_nomat.gltf');
                var asset = JSON.parse(fs.readFileSync(gltfPath));

                let bufferCache = {};

                let primitive = asset.meshes[asset.nodes.filter(a => a.name == "no_mat_no_vc")[0].mesh].primitives[0];
                assert.ok(!("COLOR_0" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "no_mat_1_vc")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                assert.ok(!("COLOR_1" in primitive.attributes));
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "no_mat_2_vc_act0")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                assert.ok("COLOR_1" in primitive.attributes);
                assert.ok(!("COLOR_2" in primitive.attributes));
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "no_mat_2_vc_act1")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                assert.ok("COLOR_1" in primitive.attributes);
                assert.ok(!("COLOR_2" in primitive.attributes));
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 1.0]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_wo_no_vc")[0].mesh].primitives[0];
                assert.ok(!("COLOR_0" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_wo_1_vc")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                assert.ok(!("COLOR_1" in primitive.attributes));
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_wo_2_vc_act0")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                assert.ok("COLOR_1" in primitive.attributes);
                assert.ok(!("COLOR_2" in primitive.attributes));
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_1, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 1.0]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_wo_2_vc_act1")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                assert.ok("COLOR_1" in primitive.attributes);
                assert.ok(!("COLOR_2" in primitive.attributes));
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 1.0]);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_1, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_no_vc")[0].mesh].primitives[0];
                assert.ok(!("COLOR_0" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_1_vc_act")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                assert.ok(!("COLOR_1" in primitive.attributes));
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_2_vc_act0")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                assert.ok("COLOR_1" in primitive.attributes);
                assert.ok(!("COLOR_2" in primitive.attributes));
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_1, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 1.0]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_2_vc_act1")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                assert.ok("COLOR_1" in primitive.attributes);
                assert.ok(!("COLOR_2" in primitive.attributes));
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 1.0]);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_1, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_1_vc_named")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                assert.ok(!("COLOR_1" in primitive.attributes));
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_2_vc_named0_act1")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                assert.ok("COLOR_1" in primitive.attributes);
                assert.ok(!("COLOR_2" in primitive.attributes));
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 1.0]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_2_vc_named1_act1")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                assert.ok("COLOR_1" in primitive.attributes);
                assert.ok(!("COLOR_2" in primitive.attributes));
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 1.0]);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_1, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_2_vc_named0_act0")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                assert.ok("COLOR_1" in primitive.attributes);
                assert.ok(!("COLOR_2" in primitive.attributes));
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_1, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 1.0]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_2_vc_named1_act0")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                assert.ok("COLOR_1" in primitive.attributes);
                assert.ok(!("COLOR_2" in primitive.attributes));
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_1, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 1.0]);

            });

            it('exports vertex color - Material nodetree - All - without export without mat', function () {
                let gltfPath = path.resolve(outDirPath, '24_vertex_color_and_factor_nodetree_all_without_nomat.gltf');
                var asset = JSON.parse(fs.readFileSync(gltfPath));

                let bufferCache = {};

                let primitive = asset.meshes[asset.nodes.filter(a => a.name == "no_mat_no_vc")[0].mesh].primitives[0];
                assert.ok(!("COLOR_0" in primitive.attributes));
                assert.ok(!("COLOR_1" in primitive.attributes));
                assert.ok(!("COLOR_2" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "no_mat_1_vc")[0].mesh].primitives[0];
                assert.ok(!("COLOR_0" in primitive.attributes));
                assert.ok(!("COLOR_1" in primitive.attributes));
                assert.ok(!("COLOR_2" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "no_mat_2_vc_act0")[0].mesh].primitives[0];
                assert.ok(!("COLOR_0" in primitive.attributes));
                assert.ok(!("COLOR_1" in primitive.attributes));
                assert.ok(!("COLOR_2" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "no_mat_2_vc_act1")[0].mesh].primitives[0];
                assert.ok(!("COLOR_0" in primitive.attributes));
                assert.ok(!("COLOR_1" in primitive.attributes));
                assert.ok(!("COLOR_2" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_wo_no_vc")[0].mesh].primitives[0];
                assert.ok(!("COLOR_0" in primitive.attributes));
                assert.ok(!("COLOR_1" in primitive.attributes));
                assert.ok(!("COLOR_2" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_wo_1_vc")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 1.0, 1.0]);
                assert.ok("COLOR_1" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_1, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 1.0]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_wo_2_vc_act0")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 1.0, 1.0]);
                assert.ok("COLOR_1" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_1, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 1.0]);
                assert.ok("COLOR_2" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_2, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 1.0]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_wo_2_vc_act1")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 1.0, 1.0]);
                assert.ok("COLOR_1" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_1, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);
                assert.ok("COLOR_2" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_2, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 1.0]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_no_vc")[0].mesh].primitives[0];
                assert.ok(!("COLOR_0" in primitive.attributes));
                assert.ok(!("COLOR_1" in primitive.attributes));
                assert.ok(!("COLOR_2" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_1_vc_act")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);
                assert.ok(!("COLOR_1" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_2_vc_act0")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);
                assert.ok("COLOR_1" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_1, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 1.0]);
                assert.ok(!("COLOR_2" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_2_vc_act1")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 1.0]);
                assert.ok("COLOR_1" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_1, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);
                assert.ok(!("COLOR_2" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_1_vc_named")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);
                assert.ok(!("COLOR_1" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_2_vc_named0_act1")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);
                assert.ok("COLOR_1" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_1, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 1.0]);
                assert.ok(!("COLOR_2" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_2_vc_named1_act1")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 1.0]);
                assert.ok("COLOR_1" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_1, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);
                assert.ok(!("COLOR_2" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_2_vc_named0_act0")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);
                assert.ok("COLOR_1" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_1, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 1.0]);
                assert.ok(!("COLOR_2" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_2_vc_named1_act0")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 1.0]);
                assert.ok("COLOR_1" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_1, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);
                assert.ok(!("COLOR_2" in primitive.attributes));

            });

            it('exports vertex color - Material nodetree - All - with export without mat', function () {
                let gltfPath = path.resolve(outDirPath, '24_vertex_color_and_factor_nodetree_all_with_nomat.gltf');
                var asset = JSON.parse(fs.readFileSync(gltfPath));

                let bufferCache = {};

                let primitive = asset.meshes[asset.nodes.filter(a => a.name == "no_mat_no_vc")[0].mesh].primitives[0];
                assert.ok(!("COLOR_0" in primitive.attributes));
                assert.ok(!("COLOR_1" in primitive.attributes));
                assert.ok(!("COLOR_2" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "no_mat_1_vc")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);
                assert.ok(!("COLOR_1" in primitive.attributes));
                assert.ok(!("COLOR_2" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "no_mat_2_vc_act0")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);
                assert.ok("COLOR_1" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_1, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 1.0]);
                assert.ok(!("COLOR_2" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "no_mat_2_vc_act1")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 1.0]);
                assert.ok("COLOR_1" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_1, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);
                assert.ok(!("COLOR_2" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_wo_no_vc")[0].mesh].primitives[0];
                assert.ok(!("COLOR_0" in primitive.attributes));
                assert.ok(!("COLOR_1" in primitive.attributes));
                assert.ok(!("COLOR_2" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_wo_1_vc")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 1.0, 1.0]);
                assert.ok("COLOR_1" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_1, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 1.0]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_wo_2_vc_act0")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 1.0, 1.0]);
                assert.ok("COLOR_1" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_1, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 1.0]);
                assert.ok("COLOR_2" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_2, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 1.0]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_wo_2_vc_act1")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 1.0, 1.0]);
                assert.ok("COLOR_1" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_1, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);
                assert.ok("COLOR_2" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_2, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 1.0]);

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_no_vc")[0].mesh].primitives[0];
                assert.ok(!("COLOR_0" in primitive.attributes));
                assert.ok(!("COLOR_1" in primitive.attributes));
                assert.ok(!("COLOR_2" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_1_vc_act")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);
                assert.ok(!("COLOR_1" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_2_vc_act0")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);
                assert.ok("COLOR_1" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_1, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 1.0]);
                assert.ok(!("COLOR_2" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_2_vc_act1")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 1.0]);
                assert.ok("COLOR_1" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_1, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);
                assert.ok(!("COLOR_2" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_1_vc_named")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);
                assert.ok(!("COLOR_1" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_2_vc_named0_act1")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);
                assert.ok("COLOR_1" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_1, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 1.0]);
                assert.ok(!("COLOR_2" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_2_vc_named1_act1")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 1.0]);
                assert.ok("COLOR_1" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_1, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);
                assert.ok(!("COLOR_2" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_2_vc_named0_act0")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);
                assert.ok("COLOR_1" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_1, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 1.0]);
                assert.ok(!("COLOR_2" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_2_vc_named1_act0")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 1.0]);
                assert.ok("COLOR_1" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_1, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);
                assert.ok(!("COLOR_2" in primitive.attributes));

            });

            it('exports vertex color - Material nodetree - Not All - with export without mat', function () {
                let gltfPath = path.resolve(outDirPath, '24_vertex_color_and_factor_nodetree_not_all_with_nomat.gltf');
                var asset = JSON.parse(fs.readFileSync(gltfPath));

                let bufferCache = {};

                let primitive = asset.meshes[asset.nodes.filter(a => a.name == "no_mat_no_vc")[0].mesh].primitives[0];
                assert.ok(!("COLOR_0" in primitive.attributes));
                assert.ok(!("COLOR_1" in primitive.attributes));
                assert.ok(!("COLOR_2" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "no_mat_1_vc")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);
                assert.ok(!("COLOR_1" in primitive.attributes));
                assert.ok(!("COLOR_2" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "no_mat_2_vc_act0")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);
                assert.ok(!("COLOR_1" in primitive.attributes));
                assert.ok(!("COLOR_2" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "no_mat_2_vc_act1")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 1.0]);
                assert.ok(!("COLOR_1" in primitive.attributes));
                assert.ok(!("COLOR_2" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_wo_no_vc")[0].mesh].primitives[0];
                assert.ok(!("COLOR_0" in primitive.attributes));
                assert.ok(!("COLOR_1" in primitive.attributes));
                assert.ok(!("COLOR_2" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_wo_1_vc")[0].mesh].primitives[0];
                assert.ok(!("COLOR_0" in primitive.attributes));
                assert.ok(!("COLOR_1" in primitive.attributes));
                assert.ok(!("COLOR_2" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_wo_2_vc_act0")[0].mesh].primitives[0];
                assert.ok(!("COLOR_0" in primitive.attributes));
                assert.ok(!("COLOR_1" in primitive.attributes));
                assert.ok(!("COLOR_2" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_wo_2_vc_act1")[0].mesh].primitives[0];
                assert.ok(!("COLOR_0" in primitive.attributes));
                assert.ok(!("COLOR_1" in primitive.attributes));
                assert.ok(!("COLOR_2" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_no_vc")[0].mesh].primitives[0];
                assert.ok(!("COLOR_0" in primitive.attributes));
                assert.ok(!("COLOR_1" in primitive.attributes));
                assert.ok(!("COLOR_2" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_1_vc_act")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);
                assert.ok(!("COLOR_1" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_2_vc_act0")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);
                assert.ok(!("COLOR_1" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_2_vc_act1")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 1.0]);
                assert.ok(!("COLOR_1" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_1_vc_named")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);
                assert.ok(!("COLOR_1" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_2_vc_named0_act1")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);
                assert.ok(!("COLOR_1" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_2_vc_named1_act1")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 1.0]);
                assert.ok(!("COLOR_1" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_2_vc_named0_act0")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);
                assert.ok(!("COLOR_1" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_2_vc_named1_act0")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 1.0]);
                assert.ok(!("COLOR_1" in primitive.attributes));

            });

            it('exports vertex color - Material nodetree - Not All - without export without mat', function () {
                let gltfPath = path.resolve(outDirPath, '24_vertex_color_and_factor_nodetree_not_all_without_nomat.gltf');
                var asset = JSON.parse(fs.readFileSync(gltfPath));

                let bufferCache = {};

                let primitive = asset.meshes[asset.nodes.filter(a => a.name == "no_mat_no_vc")[0].mesh].primitives[0];
                assert.ok(!("COLOR_0" in primitive.attributes));
                assert.ok(!("COLOR_1" in primitive.attributes));
                assert.ok(!("COLOR_2" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "no_mat_1_vc")[0].mesh].primitives[0];
                assert.ok(!("COLOR_0" in primitive.attributes));
                assert.ok(!("COLOR_1" in primitive.attributes));
                assert.ok(!("COLOR_2" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "no_mat_2_vc_act0")[0].mesh].primitives[0];
                assert.ok(!("COLOR_0" in primitive.attributes));
                assert.ok(!("COLOR_1" in primitive.attributes));
                assert.ok(!("COLOR_2" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "no_mat_2_vc_act1")[0].mesh].primitives[0];
                assert.ok(!("COLOR_0" in primitive.attributes));
                assert.ok(!("COLOR_1" in primitive.attributes));
                assert.ok(!("COLOR_2" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_wo_no_vc")[0].mesh].primitives[0];
                assert.ok(!("COLOR_0" in primitive.attributes));
                assert.ok(!("COLOR_1" in primitive.attributes));
                assert.ok(!("COLOR_2" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_wo_1_vc")[0].mesh].primitives[0];
                assert.ok(!("COLOR_0" in primitive.attributes));
                assert.ok(!("COLOR_1" in primitive.attributes));
                assert.ok(!("COLOR_2" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_wo_2_vc_act0")[0].mesh].primitives[0];
                assert.ok(!("COLOR_0" in primitive.attributes));
                assert.ok(!("COLOR_1" in primitive.attributes));
                assert.ok(!("COLOR_2" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_wo_2_vc_act1")[0].mesh].primitives[0];
                assert.ok(!("COLOR_0" in primitive.attributes));
                assert.ok(!("COLOR_1" in primitive.attributes));
                assert.ok(!("COLOR_2" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_no_vc")[0].mesh].primitives[0];
                assert.ok(!("COLOR_0" in primitive.attributes));
                assert.ok(!("COLOR_1" in primitive.attributes));
                assert.ok(!("COLOR_2" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_1_vc_act")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);
                assert.ok(!("COLOR_1" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_2_vc_act0")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);
                assert.ok(!("COLOR_1" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_2_vc_act1")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 1.0]);
                assert.ok(!("COLOR_1" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_1_vc_named")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);
                assert.ok(!("COLOR_1" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_2_vc_named0_act1")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);
                assert.ok(!("COLOR_1" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_2_vc_named1_act1")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 1.0]);
                assert.ok(!("COLOR_1" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_2_vc_named0_act0")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [1.0, 0.0, 0.0]);
                assert.ok(!("COLOR_1" in primitive.attributes));

                primitive = asset.meshes[asset.nodes.filter(a => a.name == "mat_vc_2_vc_named1_act0")[0].mesh].primitives[0];
                assert.ok("COLOR_0" in primitive.attributes);
                colors = getAccessorData(gltfPath, asset, primitive.attributes.COLOR_0, bufferCache);
                assert.equalEpsilon(colors[0], [0.0, 0.0, 1.0]);
                assert.ok(!("COLOR_1" in primitive.attributes));

            });

        });
    });

    describe('Importer / Exporter (Roundtrip)', function () {
        blenderVersions.forEach(function (blenderVersion) {
            let variants = [
                ['', ''],
                ['_glb', '--glb']
            ];

            variants.forEach(function (variant) {
                const args = variant[1];
                describe(blenderVersion + '_roundtrip' + variant[0], function () {
                    let dirs = fs.readdirSync('roundtrip');
                    dirs.forEach((dir) => {
                        if (!fs.statSync('roundtrip/' + dir).isDirectory())
                            return;

                        it(dir, function (done) {
                            let outDirName = 'out' + blenderVersion + variant[0];
                            let gltfSrcPath = `roundtrip/${dir}/${dir}.gltf`;
                            let ext = args.indexOf('--glb') === -1 ? '.gltf' : '.glb';
                            let outDirPath = path.resolve(OUT_PREFIX, 'roundtrip', dir, outDirName);
                            let gltfDstPath = path.resolve(outDirPath, `${dir}${ext}`);
                            let gltfOptionsPath = `roundtrip/${dir}/${dir}_options.txt`;
                            let gltfnovalidatorPath = `roundtrip/${dir}/${dir}_noval.txt`;
                            let options = args;
                            if (fs.existsSync(gltfOptionsPath)) {
                                options += ' ' + fs.readFileSync(gltfOptionsPath).toString().replace(/\r?\n|\r/g, '');
                            }
                            //return done(); // uncomment to not roundtrip all files
                            blenderRoundtripGltf(blenderVersion, gltfSrcPath, outDirPath, (error) => {
                                if (error) {
                                    if (options.indexOf("--no-validate") !== -1) { return done(); }
                                    return done(error);
                                }

                                validateGltf(gltfSrcPath, (error, gltfSrcReport) => {
                                    if (error) {
                                        if (options.indexOf("--no-validate") !== -1) { return done(); }
                                        return done(error);
                                    }


                                    validateGltf(gltfDstPath, (error, gltfDstReport) => {
                                        if (error) {
                                            if (options.indexOf("--no-validate") !== -1) { return done(); }
                                            return done(error);
                                        }


                                        let reduceKeys = function (raw, allowed) {
                                            return Object.keys(raw)
                                                .filter(key => allowed.includes(key))
                                                .reduce((obj, key) => {
                                                    obj[key] = raw[key];
                                                    return obj;
                                                }, {});
                                        };

                                        let srcInfo = reduceKeys(gltfSrcReport.info, validator_info_keys);
                                        let dstInfo = reduceKeys(gltfDstReport.info, validator_info_keys);

                                        if (options.indexOf("--no-validate") !== -1) {
                                            if (!fs.existsSync(gltfnovalidatorPath)) {
                                                try {
                                                    assert.deepStrictEqual(dstInfo, srcInfo);
                                                } catch (ex) {
                                                    done(new Error("Validation summary mismatch.\nExpected summary:\n" +
                                                        JSON.stringify(srcInfo, null, '  ') +
                                                        "\n\nActual summary:\n" + JSON.stringify(dstInfo, null, '  ')));
                                                    return;
                                                }
                                            }
                                        }

                                        done();
                                    });
                                });
                            }, options);
                        });
                    });
                });
            });

            describe(blenderVersion + '_roundtrip_results', function () {
                let outDirName = 'out' + blenderVersion;

                it('roundtrips alpha blend mode', function () {
                    let dir = '01_alpha_blend';
                    let outDirPath = path.resolve(OUT_PREFIX, 'roundtrip', dir, outDirName);
                    let gltfPath = path.resolve(outDirPath, dir + '.gltf');
                    const asset = JSON.parse(fs.readFileSync(gltfPath));

                    assert.strictEqual(asset.materials.length, 2);

                    const opaqueMaterials = asset.materials.filter(m => m.name === 'Cube');
                    assert.strictEqual(opaqueMaterials.length, 1);
                    assert.strictEqual(opaqueMaterials[0].alphaMode, undefined);

                    const blendedMaterials = asset.materials.filter(m => m.name === 'Transparent_Plane');
                    assert.strictEqual(blendedMaterials.length, 1);
                    assert.strictEqual(blendedMaterials[0].alphaMode, 'BLEND');
                });

                it('roundtrips alpha mask mode', function () {
                    let dir = '01_alpha_mask';
                    let outDirPath = path.resolve(OUT_PREFIX, 'roundtrip', dir, outDirName);
                    let gltfPath = path.resolve(outDirPath, dir + '.gltf');
                    const asset = JSON.parse(fs.readFileSync(gltfPath));

                    assert.strictEqual(asset.materials.length, 1);
                    assert.strictEqual(asset.materials[0].alphaMode, 'MASK');
                    assert.equalEpsilon(asset.materials[0].alphaCutoff, 0.42);
                });

                it('roundtrips the doubleSided flag', function () {
                    let dir = '01_single_vs_double_sided';
                    let outDirPath = path.resolve(OUT_PREFIX, 'roundtrip', dir, outDirName);
                    let gltfPath = path.resolve(outDirPath, dir + '.gltf');
                    const asset = JSON.parse(fs.readFileSync(gltfPath));

                    assert.strictEqual(asset.materials.length, 2);

                    const singleSidedMaterials = asset.materials.filter(m => m.name === 'mat_single');
                    assert.strictEqual(singleSidedMaterials.length, 1);
                    assert.strictEqual(singleSidedMaterials[0].doubleSided, undefined);

                    const doubleSidedMaterials = asset.materials.filter(m => m.name === 'mat_double');
                    assert.strictEqual(doubleSidedMaterials.length, 1);
                    assert.strictEqual(doubleSidedMaterials[0].doubleSided, true);
                });

                it('roundtrips a morph target animation', function () {
                    let dir = '01_morphed_cube';
                    let outDirPath = path.resolve(OUT_PREFIX, 'roundtrip', dir, outDirName);
                    let gltfPath = path.resolve(outDirPath, dir + '.gltf');
                    const asset = JSON.parse(fs.readFileSync(gltfPath));
                    assert.strictEqual(asset.animations.length, 1);

                    const animation = asset.animations[0];
                    assert.strictEqual(animation.channels.length, 1);
                    assert.strictEqual(animation.samplers.length, 1);
                    assert.strictEqual(animation.channels[0].sampler, 0);
                    assert.strictEqual(animation.channels[0].target.path, 'weights');
                    assert.strictEqual(animation.samplers[0].interpolation, 'CUBICSPLINE');

                    const animatedNode = asset.nodes[animation.channels[0].target.node];
                    const animatedMesh = asset.meshes[animatedNode.mesh];
                    const targetNames = animatedMesh.extras.targetNames;
                    assert.strictEqual(targetNames.length, 2);
                    assert.notStrictEqual(targetNames.indexOf('Top'), -1);
                    assert.notStrictEqual(targetNames.indexOf('Bottom'), -1);

                    let bufferCache = {};
                    const inputData = getAccessorData(gltfPath, asset, animation.samplers[0].input, bufferCache);
                    const expectedInputData = [0, 1, 2];
                    assert.equalEpsilonArray(inputData, expectedInputData);

                    const outputData = getAccessorData(gltfPath, asset, animation.samplers[0].output, bufferCache);
                    const expectedOutputData = [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0];
                    assert.equalEpsilonArray(outputData, expectedOutputData);
                });

                it('roundtrips a base color', function () {
                    let dir = '01_principled_material';
                    let outDirPath = path.resolve(OUT_PREFIX, 'roundtrip', dir, outDirName);
                    let gltfPath = path.resolve(outDirPath, dir + '.gltf');
                    const asset = JSON.parse(fs.readFileSync(gltfPath));

                    assert.strictEqual(asset.materials.length, 1);
                    const textureIndex = asset.materials[0].pbrMetallicRoughness.baseColorTexture.index;
                    const imageIndex = asset.textures[textureIndex].source;

                    assert.strictEqual(asset.images[imageIndex].uri, '01_principled_baseColor.png');
                    assert(fs.existsSync(path.resolve(outDirPath, '01_principled_baseColor.png')));
                });

                it('roundtrips a normal map', function () {
                    let dir = '01_principled_material';
                    let outDirPath = path.resolve(OUT_PREFIX, 'roundtrip', dir, outDirName);
                    let gltfPath = path.resolve(outDirPath, dir + '.gltf');
                    const asset = JSON.parse(fs.readFileSync(gltfPath));

                    assert.strictEqual(asset.materials.length, 1);
                    const textureIndex = asset.materials[0].normalTexture.index;
                    const imageIndex = asset.textures[textureIndex].source;

                    assert.strictEqual(asset.images[imageIndex].uri, '01_principled_normal.png');
                    assert(fs.existsSync(path.resolve(outDirPath, '01_principled_normal.png')));
                });

                it('roundtrips an emissive map', function () {
                    let dir = '01_principled_material';
                    let outDirPath = path.resolve(OUT_PREFIX, 'roundtrip', dir, outDirName);
                    let gltfPath = path.resolve(outDirPath, dir + '.gltf');
                    const asset = JSON.parse(fs.readFileSync(gltfPath));

                    assert.strictEqual(asset.materials.length, 1);
                    const textureIndex = asset.materials[0].emissiveTexture.index;
                    const imageIndex = asset.textures[textureIndex].source;

                    assert.strictEqual(asset.images[imageIndex].uri, '01_principled_emissive.png');
                    assert.deepStrictEqual(asset.materials[0].emissiveFactor, [1, 1, 1]);
                    assert(fs.existsSync(path.resolve(outDirPath, '01_principled_emissive.png')));
                });

                it('roundtrips skin cylinder', function () {
                    let dir = '03_skinned_cylinder';
                    let outDirPath = path.resolve(OUT_PREFIX, 'roundtrip', dir, outDirName);
                    let gltfPath = path.resolve(outDirPath, dir + '.gltf');
                    const asset = JSON.parse(fs.readFileSync(gltfPath));

                    assert.strictEqual(asset.meshes.length, 1); // be sure bone shape are not re-exported

                });

                it('roundtrips an OcclusionRoughnessMetallic texture', function () {
                    let dir = '08_combine_orm';
                    let outDirPath = path.resolve(OUT_PREFIX, 'roundtrip', dir, outDirName);

                    assert(fs.existsSync(path.resolve(outDirPath, '08_tiny-box-rgb.png')));
                });

                it('references the OcclusionRoughnessMetallic texture', function () {
                    let dir = '08_combine_orm';
                    let outDirPath = path.resolve(OUT_PREFIX, 'roundtrip', dir, outDirName);
                    let gltfPath = path.resolve(outDirPath, dir + '.gltf');
                    const asset = JSON.parse(fs.readFileSync(gltfPath));

                    assert.strictEqual(asset.materials.length, 1);
                    assert.strictEqual(asset.materials[0].occlusionTexture.index, 0);
                    assert.strictEqual(asset.materials[0].pbrMetallicRoughness.metallicRoughnessTexture.index, 0);
                    assert.strictEqual(asset.textures.length, 1);
                    assert.strictEqual(asset.textures[0].source, 0);
                    assert.strictEqual(asset.images.length, 1);
                    assert.strictEqual(asset.images[0].uri, '08_tiny-box-rgb.png');
                });

                it('roundtrips occlusion strength', function () {
                    let dir = '13_occlusion_strength';
                    let outDirPath = path.resolve(OUT_PREFIX, 'roundtrip', dir, outDirName);
                    let gltfPath = path.resolve(outDirPath, dir + '.gltf');
                    const asset = JSON.parse(fs.readFileSync(gltfPath));

                    assert.strictEqual(asset.materials.length, 1);
                    assert.equalEpsilon(asset.materials[0].occlusionTexture.strength, 0.25);
                })

                it('roundtrips two different UV maps for the same texture', function () {
                    let dir = '12_orm_two_uvmaps';
                    let outDirPath = path.resolve(OUT_PREFIX, 'roundtrip', dir, outDirName);
                    let gltfPath = path.resolve(outDirPath, dir + '.gltf');
                    const asset = JSON.parse(fs.readFileSync(gltfPath));

                    assert.strictEqual(asset.materials.length, 1);
                    const material = asset.materials[0];
                    // Same texture
                    assert.strictEqual(material.occlusionTexture.index, 0);
                    assert.strictEqual(material.pbrMetallicRoughness.metallicRoughnessTexture.index, 0);
                    // Different UVMaps
                    assert.strictEqual(material.occlusionTexture.texCoord, 1);
                    assert.strictEqual(material.pbrMetallicRoughness.metallicRoughnessTexture.texCoord || 0, 0);
                });

                it('roundtrips baseColorFactor, etc. when used with textures', function () {
                    let dir = '11_factors_and_textures';
                    let outDirPath = path.resolve(OUT_PREFIX, 'roundtrip', dir, outDirName);
                    let gltfPath = path.resolve(outDirPath, dir + '.gltf');
                    const asset = JSON.parse(fs.readFileSync(gltfPath));

                    assert.strictEqual(asset.materials.length, 1);

                    const mat = asset.materials[0];
                    const pbr = mat.pbrMetallicRoughness;

                    assert.equalEpsilon(mat.emissiveFactor[0], 1);
                    assert.equalEpsilon(mat.emissiveFactor[1], 0);
                    assert.equalEpsilon(mat.emissiveFactor[2], 0);

                    assert.equalEpsilon(pbr.baseColorFactor[0], 0);
                    assert.equalEpsilon(pbr.baseColorFactor[1], 1);
                    assert.equalEpsilon(pbr.baseColorFactor[2], 0);
                    assert.equalEpsilon(pbr.baseColorFactor[3], 0.5);

                    assert.equalEpsilon(pbr.metallicFactor, 0.25);
                    assert.equalEpsilon(pbr.roughnessFactor, 0.75);
                });

                it('roundtrips unlit base colors', function () {
                    let dir = '01_unlit';
                    let outDirPath = path.resolve(OUT_PREFIX, 'roundtrip', dir, outDirName);
                    let gltfPath = path.resolve(outDirPath, dir + '.gltf');
                    const asset = JSON.parse(fs.readFileSync(gltfPath));

                    assert.strictEqual(asset.materials.length, 2);

                    const orange = asset.materials.find(mat => mat.name === 'Orange');
                    assert.ok('KHR_materials_unlit' in orange.extensions);
                    assert.equalEpsilon(orange.pbrMetallicRoughness.baseColorFactor[0], 1);
                    assert.equalEpsilon(orange.pbrMetallicRoughness.baseColorFactor[1], 0.217637640824031);
                    assert.equalEpsilon(orange.pbrMetallicRoughness.baseColorFactor[2], 0);
                    assert.equalEpsilon(orange.pbrMetallicRoughness.baseColorFactor[3], 1);

                    const blue = asset.materials.find(mat => mat.name === 'Blue');
                    assert.ok('KHR_materials_unlit' in blue.extensions);
                    assert.equalEpsilon(blue.pbrMetallicRoughness.baseColorFactor[0], 0);
                    assert.equalEpsilon(blue.pbrMetallicRoughness.baseColorFactor[1], 0.217637640824031);
                    assert.equalEpsilon(blue.pbrMetallicRoughness.baseColorFactor[2], 1);
                    assert.equalEpsilon(blue.pbrMetallicRoughness.baseColorFactor[3], 0.5);
                });

                it('roundtrips all texture transforms', function () {
                    let dir = '09_texture_transform';
                    let outDirPath = path.resolve(OUT_PREFIX, 'roundtrip', dir, outDirName);
                    let gltfPath = path.resolve(outDirPath, dir + '.gltf');
                    const asset = JSON.parse(fs.readFileSync(gltfPath));

                    assert.strictEqual(asset.materials.length, 1);

                    const baseTransform = asset.materials[0].pbrMetallicRoughness.baseColorTexture.extensions.KHR_texture_transform;
                    assert.equalEpsilon(baseTransform.offset[0], 0.1);
                    assert.equalEpsilon(baseTransform.offset[1], 0.2);
                    assert.equalEpsilon(baseTransform.rotation, 0.3);
                    assert.equalEpsilon(baseTransform.scale[0], 4);
                    assert.equalEpsilon(baseTransform.scale[1], 5);

                    const mrTransform = asset.materials[0].pbrMetallicRoughness.metallicRoughnessTexture.extensions.KHR_texture_transform;
                    assert.equalEpsilon(mrTransform.offset[0], 0.2);
                    assert.equalEpsilon(mrTransform.offset[1], 0.3);
                    assert.equalEpsilon(mrTransform.rotation, 0.4);
                    assert.equalEpsilon(mrTransform.scale[0], 5);
                    assert.equalEpsilon(mrTransform.scale[1], 6);

                    const normalTransform = asset.materials[0].normalTexture.extensions.KHR_texture_transform;
                    assert.equalEpsilon(normalTransform.offset[0], 0.3);
                    assert.equalEpsilon(normalTransform.offset[1], 0.4);
                    assert.equalEpsilon(normalTransform.rotation, 0.5);
                    assert.equalEpsilon(normalTransform.scale[0], 6);
                    assert.equalEpsilon(normalTransform.scale[1], 7);

                    const occlusionTransform = asset.materials[0].occlusionTexture.extensions.KHR_texture_transform;
                    assert.equalEpsilon(occlusionTransform.offset[0], 0.2);
                    assert.equalEpsilon(occlusionTransform.offset[1], 0.3);
                    assert.equalEpsilon(occlusionTransform.rotation, 0.4);
                    assert.equalEpsilon(occlusionTransform.scale[0], 5);
                    assert.equalEpsilon(occlusionTransform.scale[1], 6);

                    const emissiveTransform = asset.materials[0].emissiveTexture.extensions.KHR_texture_transform;
                    assert.equalEpsilon(emissiveTransform.offset[0], 0.5);
                    assert.equalEpsilon(emissiveTransform.offset[1], 0.6);
                    assert.equalEpsilon(emissiveTransform.rotation, 0.7);
                    assert.equalEpsilon(emissiveTransform.scale[0], 8);
                    assert.equalEpsilon(emissiveTransform.scale[1], 9);
                });

                it('roundtrips UNSIGNED_SHORT when count is 65535', function () {
                    let dir = '01_vertex_count_16bit';
                    let outDirPath = path.resolve(OUT_PREFIX, 'roundtrip', dir, outDirName);
                    let gltfPath = path.resolve(outDirPath, dir + '.gltf');
                    const asset = JSON.parse(fs.readFileSync(gltfPath));

                    assert.strictEqual(asset.meshes.length, 1);
                    assert.strictEqual(asset.meshes[0].primitives.length, 1);

                    const primitive = asset.meshes[0].primitives[0];

                    // There are 65535 vertices, numbered 0 to 65534, avoiding the
                    // primitive restart value at 65535 (the highest 16-bit unsigned integer value).
                    assert.strictEqual(asset.accessors[primitive.attributes.POSITION].count, 65535);

                    // The indices componentType should be 5123 (UNSIGNED_SHORT).
                    assert.strictEqual(asset.accessors[primitive.indices].componentType, 5123);
                });

                it('roundtrips UNSIGNED_INT when count is 65536', function () {
                    let dir = '01_vertex_count_32bit';
                    let outDirPath = path.resolve(OUT_PREFIX, 'roundtrip', dir, outDirName);
                    let gltfPath = path.resolve(outDirPath, dir + '.gltf');
                    const asset = JSON.parse(fs.readFileSync(gltfPath));

                    assert.strictEqual(asset.meshes.length, 1);
                    assert.strictEqual(asset.meshes[0].primitives.length, 1);

                    const primitive = asset.meshes[0].primitives[0];

                    // There are 65536 vertices, numbered 0 to 65535.  Because of the primitive
                    // restart value, 32-bit indicies are required at this point and beyond.
                    assert.strictEqual(asset.accessors[primitive.attributes.POSITION].count, 65536);

                    // The indices componentType should be 5125 (UNSIGNED_INT).
                    assert.strictEqual(asset.accessors[primitive.indices].componentType, 5125);
                });

                it('roundtrips some custom normals', function () {
                    let dir = '10_custom_normals';
                    let outDirPath = path.resolve(OUT_PREFIX, 'roundtrip', dir, outDirName);
                    let gltfPath = path.resolve(outDirPath, dir + '.gltf');
                    const asset = JSON.parse(fs.readFileSync(gltfPath));
                    assert.strictEqual(asset.meshes.length, 2);

                    let bufferCache = {};

                    const angleCubeMesh = asset.meshes.filter(m => m.name === 'AngleCube')[0];
                    const flatNormals = angleCubeMesh.primitives[0].attributes.NORMAL;
                    const flatNormalData = getAccessorData(gltfPath, asset, flatNormals, bufferCache);
                    const flatNormalHash = buildVectorHash(flatNormalData);

                    // In this mesh, the beveled cube has various angled edges.
                    // Several are not axis-aligned.
                    const expectedFlatNormalHash = {
                        "0.000,1.000,0.000": 4,
                        "-1.000,0.000,0.000": 4,
                        "0.000,0.000,-1.000": 4,
                        "0.000,-1.000,0.000": 4,
                        "1.000,0.000,0.000": 4,
                        "0.577,-0.577,0.577": 3,
                        "0.577,0.577,0.577": 3,
                        "0.577,-0.577,-0.577": 3,
                        "0.577,0.577,-0.577": 3,
                        "-0.577,-0.577,0.577": 3,
                        "-0.577,0.577,0.577": 3,
                        "-0.577,-0.577,-0.577": 3,
                        "-0.577,0.577,-0.577": 3,
                        "-0.707,0.707,0.000": 4,
                        "0.000,0.707,0.707": 4,
                        "0.707,0.000,0.707": 4,
                        "-0.707,0.000,-0.707": 4,
                        "0.707,0.000,-0.707": 4,
                        "-0.707,0.000,0.707": 4,
                        "0.000,-0.707,-0.707": 4,
                        "0.707,-0.707,0.000": 4,
                        "0.000,0.707,-0.707": 4,
                        "-0.707,-0.707,0.000": 4,
                        "0.000,-0.707,0.707": 4,
                        "0.707,0.707,0.000": 4,
                        "0.000,0.000,1.000": 4
                    };
                    assert.deepStrictEqual(flatNormalHash, expectedFlatNormalHash);

                    const smoothCubeMesh = asset.meshes.filter(m => m.name === 'SmoothCube')[0];
                    const customNormals = smoothCubeMesh.primitives[0].attributes.NORMAL;
                    const customNormalData = getAccessorData(gltfPath, asset, customNormals, bufferCache);
                    const customNormalHash = buildVectorHash(customNormalData);

                    // In this mesh, the beveled cube has custom normals that are all
                    // axis-aligned to the nearest cube face.
                    const expectedCustomNormalHash = {
                        "0.000,1.000,0.000": 16,
                        "-1.000,0.000,0.000": 16,
                        "0.000,0.000,-1.000": 16,
                        "0.000,-1.000,0.000": 16,
                        "1.000,0.000,0.000": 16,
                        "0.000,0.000,1.000": 16
                    };
                    assert.deepStrictEqual(customNormalHash, expectedCustomNormalHash);
                });

                it('roundtrips animation names', function () {
                    let dir = '07_nla-anim';
                    let outDirPath = path.resolve(OUT_PREFIX, 'roundtrip', dir, outDirName);
                    let gltfPath = path.resolve(outDirPath, dir + '.gltf');
                    const asset = JSON.parse(fs.readFileSync(gltfPath));

                    const expectedAnimNames = ["Action2", "Action1", "Action3"];
                    const animNames = asset.animations.map(anim => anim.name);
                    assert.deepStrictEqual(animNames.sort(), expectedAnimNames.sort());
                });

                it('roundtrips texture wrap modes', function () {
                    let dir = '13_texture_wrapping';
                    let outDirPath = path.resolve(OUT_PREFIX, 'roundtrip', dir, outDirName);
                    let gltfPath = path.resolve(outDirPath, dir + '.gltf');
                    const asset = JSON.parse(fs.readFileSync(gltfPath));

                    const materials = asset.materials;
                    assert.deepStrictEqual(materials.length, 2);

                    const mat1 = materials.find(mat => mat.name == 'Mirror x Mirror');
                    const tex1 = asset.textures[mat1.pbrMetallicRoughness.baseColorTexture.index];
                    const samp1 = asset.samplers[tex1.sampler];
                    assert.deepStrictEqual(samp1.wrapS, 33648);  // MIRRORED_REPEAT
                    assert.deepStrictEqual(samp1.wrapT, 33648);  // MIRRORED_REPEAT

                    const mat2 = materials.find(mat => mat.name == 'Repeat x Clamp');
                    const tex2 = asset.textures[mat2.pbrMetallicRoughness.baseColorTexture.index];
                    const samp2 = asset.samplers[tex2.sampler];
                    assert.deepStrictEqual(samp2.wrapS || 10497, 10497);  // REPEAT
                    assert.deepStrictEqual(samp2.wrapT, 33071);  // CLAMP_TO_EDGE
                });

                it('roundtrips emissive/emissive_strength', function () {
                    let dir = '14_emission_strength';
                    let outDirPath = path.resolve(OUT_PREFIX, 'roundtrip', dir, outDirName);
                    let gltfPath = path.resolve(outDirPath, dir + '.gltf');
                    const asset = JSON.parse(fs.readFileSync(gltfPath));

                    assert.strictEqual(asset.materials.length, 18);

                    const SpecGloss = asset.materials.filter(m => m.name === "SpecGloss");

                    const SpecGlossEmissive = asset.materials.filter(m => m.name === "SpecGlossEmissive")[0];
                    assert.equalEpsilonArray(SpecGlossEmissive.emissiveFactor, [0.2, 0.1, 0.0]);

                    const SpecGlossEmissiveGray = asset.materials.filter(m => m.name === "SpecGlossEmissiveGray")[0];
                    assert.equalEpsilonArray(SpecGlossEmissiveGray.emissiveFactor, [0.3, 0.3, 0.3]);

                    const SpecGlossEmissiveGrayStrength = asset.materials.filter(m => m.name === "SpecGlossEmissiveGrayStrength")[0];
                    assert.equalEpsilon(SpecGlossEmissiveGrayStrength.extensions["KHR_materials_emissive_strength"]["emissiveStrength"], 4.5);

                    const SpecGlossEmissiveStrength = asset.materials.filter(m => m.name === "SpecGlossEmissiveStrength")[0];
                    assert.equalEpsilonArray(SpecGlossEmissiveStrength.emissiveFactor, [1.0, 0.88888888, 0.7777777777]);
                    assert.equalEpsilon(SpecGlossEmissiveStrength.extensions["KHR_materials_emissive_strength"]["emissiveStrength"], 4.5);

                    const pbrMetallicRoughness = asset.materials.filter(m => m.name === "pbrMetallicRoughness")[0];

                    const pbrEmissive = asset.materials.filter(m => m.name === "pbrEmissive")[0];
                    assert.equalEpsilonArray(pbrEmissive.emissiveFactor, [0.9, 0.8, 0.7]);

                    const pbrEmissiveGray = asset.materials.filter(m => m.name === "pbrEmissiveGray")[0];
                    assert.equalEpsilonArray(pbrEmissiveGray.emissiveFactor, [0.9, 0.9, 0.9]);

                    const pbrEmissiveGrayStrength = asset.materials.filter(m => m.name === "pbrEmissiveGrayStrength")[0];
                    assert.equalEpsilonArray(pbrEmissiveGrayStrength.emissiveFactor, [1.0, 1.0, 1.0]);
                    assert.equalEpsilon(pbrEmissiveGrayStrength.extensions["KHR_materials_emissive_strength"]["emissiveStrength"], 4.5);

                    const pbrEmissiveStrength = asset.materials.filter(m => m.name === "pbrEmissiveStrength")[0];
                    assert.equalEpsilonArray(pbrEmissiveStrength.emissiveFactor, [1.0, 0.88888888, 0.7777777777]);
                    assert.equalEpsilon(pbrEmissiveStrength.extensions["KHR_materials_emissive_strength"]["emissiveStrength"], 4.5);

                    const pbrEmissiveStrengthTexture = asset.materials.filter(m => m.name === "pbrEmissiveStrengthTexture")[0];
                    assert.equalEpsilonArray(pbrEmissiveStrengthTexture.emissiveFactor, [1.0, 0.88888888, 0.7777777777]);
                    assert.equalEpsilon(pbrEmissiveStrengthTexture.extensions["KHR_materials_emissive_strength"]["emissiveStrength"], 4.5);

                    const pbrEmissiveGrayStrengthTexture = asset.materials.filter(m => m.name === "pbrEmissiveGrayStrengthTexture")[0];
                    assert.equalEpsilonArray(pbrEmissiveGrayStrengthTexture.emissiveFactor, [1.0, 1.0, 1.0]);
                    assert.equalEpsilon(pbrEmissiveGrayStrengthTexture.extensions["KHR_materials_emissive_strength"]["emissiveStrength"], 4.5);

                    const pbrEmissiveTexture = asset.materials.filter(m => m.name === "pbrEmissiveTexture")[0];
                    assert.equalEpsilonArray(pbrEmissiveTexture.emissiveFactor, [0.9, 0.8, 0.7]);

                    const pbrEmissiveGrayTexture = asset.materials.filter(m => m.name === "pbrEmissiveGrayTexture")[0];
                    assert.equalEpsilonArray(pbrEmissiveGrayTexture.emissiveFactor, [0.9, 0.9, 0.9]);

                    const SpecGlossEmissiveTexture = asset.materials.filter(m => m.name === "SpecGlossEmissiveTexture")[0];
                    assert.equalEpsilonArray(SpecGlossEmissiveTexture.emissiveFactor, [0.9, 0.8, 0.7]);

                    const SpecGlossEmissiveGrayTexture = asset.materials.filter(m => m.name === "SpecGlossEmissiveGrayTexture")[0];
                    assert.equalEpsilonArray(SpecGlossEmissiveGrayTexture.emissiveFactor, [0.9, 0.9, 0.9]);

                    const SpecGlossEmissiveGrayStrengthTexture = asset.materials.filter(m => m.name === "SpecGlossEmissiveGrayStrengthTexture")[0];
                    assert.equalEpsilonArray(SpecGlossEmissiveGrayStrengthTexture.emissiveFactor, [1.0, 1.0, 1.0]);
                    assert.equalEpsilon(SpecGlossEmissiveGrayStrengthTexture.extensions["KHR_materials_emissive_strength"]["emissiveStrength"], 4.5);

                    const SpecGlossEmissiveStrengthTexture = asset.materials.filter(m => m.name === "SpecGlossEmissiveStrengthTexture")[0];
                    assert.equalEpsilonArray(SpecGlossEmissiveStrengthTexture.emissiveFactor, [1.0, 0.88888888, 0.7777777777]);
                    assert.equalEpsilon(SpecGlossEmissiveStrengthTexture.extensions["KHR_materials_emissive_strength"]["emissiveStrength"], 4.5);

                });

                it('roundtrips transmission', function () {
                    let dir = '15_transmission';
                    let outDirPath = path.resolve(OUT_PREFIX, 'roundtrip', dir, outDirName);
                    let gltfPath = path.resolve(outDirPath, dir + '.gltf');
                    const asset = JSON.parse(fs.readFileSync(gltfPath));

                    assert.strictEqual(asset.materials.length, 5);

                    const pbr = asset.materials.filter(m => m.name === "pbr")[0];

                    const transmissionFactor = asset.materials.filter(m => m.name === "transmissionFactor")[0];
                    assert.equalEpsilon(transmissionFactor.extensions["KHR_materials_transmission"]["transmissionFactor"], 0.8);

                    const transmissionTexture = asset.materials.filter(m => m.name === "transmissionTexture")[0];
                    assert.equalEpsilon(transmissionTexture.extensions["KHR_materials_transmission"]["transmissionFactor"], 1.0);
                    assert.ok(transmissionTexture.extensions["KHR_materials_transmission"]["transmissionTexture"]["index"] <= 1);

                    const transmissionFactorTexture = asset.materials.filter(m => m.name === "transmissionFactorTexture")[0];
                    assert.equalEpsilon(transmissionFactorTexture.extensions["KHR_materials_transmission"]["transmissionFactor"], 0.7);
                    assert.ok(transmissionFactorTexture.extensions["KHR_materials_transmission"]["transmissionTexture"]["index"] <= 1);

                });

                it('roundtrips volume', function () {
                    let dir = '16_volume';
                    let outDirPath = path.resolve(OUT_PREFIX, 'roundtrip', dir, outDirName);
                    let gltfPath = path.resolve(outDirPath, dir + '.gltf');
                    const asset = JSON.parse(fs.readFileSync(gltfPath));

                    assert.strictEqual(asset.materials.length, 20);

                    const thickness_025 = asset.materials.filter(m => m.name === "R2_ThicknessFac_0.25")[0];
                    assert.equalEpsilon(thickness_025.extensions['KHR_materials_volume']["thicknessFactor"], 0.25);
                    assert.equalEpsilon(thickness_025.extensions['KHR_materials_volume']["attenuationDistance"], 1.0);
                    assert.equalEpsilonArray(thickness_025.extensions['KHR_materials_volume']["attenuationColor"], [0.1, 0.5, 0.9]);
                    assert.ok(!("thicknessTexture" in thickness_025.extensions['KHR_materials_volume']));

                    const thickness_050 = asset.materials.filter(m => m.name === "R2_ThicknessFac_0.50")[0];
                    assert.equalEpsilon(thickness_050.extensions['KHR_materials_volume']["thicknessFactor"], 0.5);
                    assert.equalEpsilon(thickness_050.extensions['KHR_materials_volume']["attenuationDistance"], 1.0);
                    assert.equalEpsilonArray(thickness_050.extensions['KHR_materials_volume']["attenuationColor"], [0.1, 0.5, 0.9]);
                    assert.ok(!("thicknessTexture" in thickness_050.extensions['KHR_materials_volume']));

                    const thickness_10 = asset.materials.filter(m => m.name === "R2_and_R4_ThicknessFac_1.0")[0];
                    assert.equalEpsilon(thickness_10.extensions['KHR_materials_volume']["thicknessFactor"], 1.0);
                    assert.equalEpsilon(thickness_10.extensions['KHR_materials_volume']["attenuationDistance"], 1.0);
                    assert.equalEpsilonArray(thickness_10.extensions['KHR_materials_volume']["attenuationColor"], [0.1, 0.5, 0.9]);
                    assert.ok(!("thicknessTexture" in thickness_10.extensions['KHR_materials_volume']));

                    const thickness_15 = asset.materials.filter(m => m.name === "R2_ThicknessFac_1.5")[0];
                    assert.equalEpsilon(thickness_15.extensions['KHR_materials_volume']["thicknessFactor"], 1.5);
                    assert.equalEpsilon(thickness_15.extensions['KHR_materials_volume']["attenuationDistance"], 1.0);
                    assert.equalEpsilonArray(thickness_15.extensions['KHR_materials_volume']["attenuationColor"], [0.1, 0.5, 0.9]);
                    assert.ok(!("thicknessTexture" in thickness_15.extensions['KHR_materials_volume']));

                    const thickness_20 = asset.materials.filter(m => m.name === "R2_ThicknessFac_2.0")[0];
                    assert.equalEpsilon(thickness_20.extensions['KHR_materials_volume']["thicknessFactor"], 2.0);
                    assert.equalEpsilon(thickness_20.extensions['KHR_materials_volume']["attenuationDistance"], 1.0);
                    assert.equalEpsilonArray(thickness_20.extensions['KHR_materials_volume']["attenuationColor"], [0.1, 0.5, 0.9]);
                    assert.ok(!("thicknessTexture" in thickness_20.extensions['KHR_materials_volume']));

                    const tick_2_text = asset.materials.filter(m => m.name === "R3_ThicknessTex_Mat")[0];
                    assert.equalEpsilon(tick_2_text.extensions['KHR_materials_volume']["thicknessFactor"], 2);
                    assert.equalEpsilon(tick_2_text.extensions['KHR_materials_volume']["attenuationDistance"], 1.0);
                    assert.equalEpsilonArray(tick_2_text.extensions['KHR_materials_volume']["attenuationColor"], [0.1, 0.5, 0.9]);
                    assert.ok("thicknessTexture" in tick_2_text.extensions['KHR_materials_volume']);

                    const dist_025 = asset.materials.filter(m => m.name === "R5_Attenuation_0.25")[0];
                    assert.equalEpsilon(dist_025.extensions['KHR_materials_volume']["thicknessFactor"], 1);
                    assert.equalEpsilon(dist_025.extensions['KHR_materials_volume']["attenuationDistance"], 4.0);
                    assert.equalEpsilonArray(dist_025.extensions['KHR_materials_volume']["attenuationColor"], [0.1, 0.5, 0.9]);
                    assert.ok(!("thicknessTexture" in dist_025.extensions['KHR_materials_volume']));

                    const dist_05 = asset.materials.filter(m => m.name === "R5_Attenuation_0.50")[0];
                    assert.equalEpsilon(dist_05.extensions['KHR_materials_volume']["thicknessFactor"], 1);
                    assert.equalEpsilon(dist_05.extensions['KHR_materials_volume']["attenuationDistance"], 2.0);
                    assert.equalEpsilonArray(dist_05.extensions['KHR_materials_volume']["attenuationColor"], [0.1, 0.5, 0.9]);
                    assert.ok(!("thicknessTexture" in dist_05.extensions['KHR_materials_volume']));

                    const dist_10 = asset.materials.filter(m => m.name === "R5_Attenuation_1.0")[0];
                    assert.equalEpsilon(dist_10.extensions['KHR_materials_volume']["thicknessFactor"], 1);
                    assert.equalEpsilon(dist_10.extensions['KHR_materials_volume']["attenuationDistance"], 1.0);
                    assert.equalEpsilonArray(dist_10.extensions['KHR_materials_volume']["attenuationColor"], [0.1, 0.5, 0.9]);
                    assert.ok(!("thicknessTexture" in dist_10.extensions['KHR_materials_volume']));

                    const dist_15 = asset.materials.filter(m => m.name === "R5_Attenuation_1.5")[0];
                    assert.equalEpsilon(dist_15.extensions['KHR_materials_volume']["thicknessFactor"], 1);
                    assert.equalEpsilon(dist_15.extensions['KHR_materials_volume']["attenuationDistance"], 0.6666666666666666);
                    assert.equalEpsilonArray(dist_15.extensions['KHR_materials_volume']["attenuationColor"], [0.1, 0.5, 0.9]);
                    assert.ok(!("thicknessTexture" in dist_15.extensions['KHR_materials_volume']));

                    const dist_20 = asset.materials.filter(m => m.name === "R5_Attenuation_2.0")[0];
                    assert.equalEpsilon(dist_20.extensions['KHR_materials_volume']["thicknessFactor"], 1);
                    assert.equalEpsilon(dist_20.extensions['KHR_materials_volume']["attenuationDistance"], 0.5);
                    assert.equalEpsilonArray(dist_20.extensions['KHR_materials_volume']["attenuationColor"], [0.1, 0.5, 0.9]);
                    assert.ok(!("thicknessTexture" in dist_20.extensions['KHR_materials_volume']));

                    const NoThickness = asset.materials.filter(m => m.name === "NoThickness")[0];
                    assert.ok(!("KHR_materials_volume" in NoThickness.extensions));

                    const Thicknesszero = asset.materials.filter(m => m.name === "Thicknesszero")[0];
                    assert.ok(!("KHR_materials_volume" in Thicknesszero.extensions));

                });

                it('roundtrips ior', function () {
                    let dir = '17_ior';
                    let outDirPath = path.resolve(OUT_PREFIX, 'roundtrip', dir, outDirName);
                    let gltfPath = path.resolve(outDirPath, dir + '.gltf');
                    const asset = JSON.parse(fs.readFileSync(gltfPath));

                    const pbr = asset.materials.find(mat => mat.name === 'pbr');
                    assert.strictEqual(pbr.extensions, undefined);

                    const ior_2_no_transmission = asset.materials.find(mat => mat.name === 'ior_2_no_transmission');
                    assert.strictEqual(ior_2_no_transmission.extensions, undefined);

                    const ior_2 = asset.materials.find(mat => mat.name === 'ior_2');
                    assert.ok("KHR_materials_ior" in ior_2.extensions);

                    const ior_145 = asset.materials.find(mat => mat.name === 'ior_1.45');
                    assert.ok("KHR_materials_ior" in ior_145.extensions);

                    const ior_15 = asset.materials.find(mat => mat.name === 'ior_1.5');
                    assert.ok(!("KHR_materials_ior" in ior_15.extensions));

                });

                it('roundtrips Variants', function () {
                    let dir = '18_variants';
                    let outDirPath = path.resolve(OUT_PREFIX, 'roundtrip', dir, outDirName);
                    let gltfPath = path.resolve(outDirPath, dir + '.gltf');
                    const asset = JSON.parse(fs.readFileSync(gltfPath));

                    const variant_blue_index = asset.extensions['KHR_materials_variants']['variants'].findIndex(variant => variant.name === "Variant_Blue");
                    const variant_red_index = asset.extensions['KHR_materials_variants']['variants'].findIndex(variant => variant.name === "Variant_Red");


                    const mat_blue_index = asset.materials.findIndex(mat => mat.name === "Blue");
                    const mat_green_index = asset.materials.findIndex(mat => mat.name === "Green");
                    const mat_white_index = asset.materials.findIndex(mat => mat.name === "White");
                    const mat_orange_index = asset.materials.findIndex(mat => mat.name === "Orange");
                    const mat_red_index = asset.materials.findIndex(mat => mat.name === "Red");
                    const prim_blue = asset.meshes[0].primitives.find(prim => prim.material === mat_blue_index);
                    const prim_green = asset.meshes[0].primitives.find(prim => prim.material === mat_green_index);
                    const prim_white = asset.meshes[0].primitives.find(prim => prim.material === mat_white_index);

                    assert.strictEqual(asset.extensions['KHR_materials_variants']['variants'].length, 2);

                    assert.strictEqual(prim_blue.extensions['KHR_materials_variants']['mappings'].length, 2);
                    prim_blue.extensions['KHR_materials_variants']['mappings'].forEach(function (mapping) {
                        assert.strictEqual(mapping.variants.length, 1);
                    });
                    const map_1 = prim_blue.extensions['KHR_materials_variants']['mappings'].find(mapping => mapping.material === mat_red_index);
                    assert.strictEqual(map_1.variants[0], variant_red_index);
                    const map_2 = prim_blue.extensions['KHR_materials_variants']['mappings'].find(mapping => mapping.material === mat_blue_index);
                    assert.strictEqual(map_2.variants[0], variant_blue_index);

                    assert.strictEqual(prim_green.extensions['KHR_materials_variants']['mappings'].length, 2);
                    prim_green.extensions['KHR_materials_variants']['mappings'].forEach(function (mapping) {
                        assert.strictEqual(mapping.variants.length, 1);
                    });
                    const map_3 = prim_green.extensions['KHR_materials_variants']['mappings'].find(mapping => mapping.material === mat_orange_index);
                    assert.strictEqual(map_3.variants[0], variant_red_index);
                    const map_4 = prim_green.extensions['KHR_materials_variants']['mappings'].find(mapping => mapping.material === mat_green_index);
                    assert.strictEqual(map_4.variants[0], variant_blue_index);

                    assert.strictEqual(prim_white.extensions['KHR_materials_variants']['mappings'].length, 1);
                    prim_white.extensions['KHR_materials_variants']['mappings'].forEach(function (mapping) {
                        assert.strictEqual(mapping.variants.length, 2);
                    });
                    const map_5 = prim_white.extensions['KHR_materials_variants']['mappings'].find(mapping => mapping.material === mat_white_index);
                    assert.ok(variant_red_index in map_5.variants);
                    assert.ok(variant_blue_index in map_5.variants);

                });

                it('roundtrips Sheen', function () {

                    let dir = '19_sheen';
                    let outDirPath = path.resolve(OUT_PREFIX, 'roundtrip', dir, outDirName);
                    let gltfPath = path.resolve(outDirPath, dir + '.gltf');
                    const asset = JSON.parse(fs.readFileSync(gltfPath));

                    const mat_NoSheen = asset.materials.find(mat => mat.name === "NoSheen");
                    const mat_SheenDefault = asset.materials.find(mat => mat.name === "SheenDefault");
                    const mat_SheenSigma = asset.materials.find(mat => mat.name === "SheenSigma");
                    const mat_SheenTexture = asset.materials.find(mat => mat.name === "SheenTexture");
                    const mat_SheenTextureFactor = asset.materials.find(mat => mat.name === "SheenTextureFactor");
                    const mat_SheenSigmaTexture = asset.materials.find(mat => mat.name === "SheenSigmaTexture");
                    const mat_SheenSigmaTextureFactor = asset.materials.find(mat => mat.name === "SheenSigmaTextureFactor");

                    assert.strictEqual(mat_NoSheen.extensions, undefined);

                    assert.ok(!("sheenRoughnessFactor" in mat_SheenDefault.extensions['KHR_materials_sheen']));
                    assert.ok(!("sheenColorTexture" in mat_SheenDefault.extensions['KHR_materials_sheen']));
                    assert.ok(!("sheenRoughnessTexture" in mat_SheenDefault.extensions['KHR_materials_sheen']));
                    assert.equalEpsilonArray(mat_SheenDefault.extensions['KHR_materials_sheen']["sheenColorFactor"], [0.1, 0.2, 0.3]);

                    assert.ok(!("sheenColorTexture" in mat_SheenSigma.extensions['KHR_materials_sheen']));
                    assert.ok(!("sheenRoughnessTexture" in mat_SheenSigma.extensions['KHR_materials_sheen']));
                    assert.equalEpsilonArray(mat_SheenSigma.extensions['KHR_materials_sheen']["sheenColorFactor"], [0.8, 0.8, 0.8]);
                    assert.equalEpsilon(mat_SheenSigma.extensions['KHR_materials_sheen']['sheenRoughnessFactor'], 0.8);

                    assert.ok("sheenColorTexture" in mat_SheenTexture.extensions['KHR_materials_sheen']);
                    assert.ok(!("sheenColorFactor" in mat_SheenTexture.extensions['KHR_materials_sheen']));
                    assert.ok(!("sheenRoughnessTexture" in mat_SheenTexture.extensions['KHR_materials_sheen']));

                    assert.equalEpsilonArray(mat_SheenTextureFactor.extensions['KHR_materials_sheen']['sheenColorFactor'], [0.6, 0.7, 0.8]);
                    assert.ok("sheenColorTexture" in mat_SheenTextureFactor.extensions['KHR_materials_sheen']);
                    assert.ok(!("sheenRoughnessTexture" in mat_SheenTextureFactor.extensions['KHR_materials_sheen']));

                    assert.ok("sheenRoughnessTexture" in mat_SheenSigmaTexture.extensions['KHR_materials_sheen']);
                    assert.ok(!("sheenRoughnessFactor" in mat_SheenSigmaTexture.extensions['KHR_materials_sheen']));

                    assert.ok("sheenRoughnessTexture" in mat_SheenSigmaTextureFactor.extensions['KHR_materials_sheen']);
                    assert.equalEpsilon(mat_SheenSigmaTextureFactor.extensions['KHR_materials_sheen']['sheenRoughnessFactor'], 0.75);

                });

                it('roundtrips Specular Original', function () {

                    let dir = '20_specular_original';
                    let outDirPath = path.resolve(OUT_PREFIX, 'roundtrip', dir, outDirName);
                    let gltfPath = path.resolve(outDirPath, dir + '.gltf');
                    const asset = JSON.parse(fs.readFileSync(gltfPath));

                    const mat_SpecDefault = asset.materials.find(mat => mat.name === "SpecDefault");
                    const mat_Factor = asset.materials.find(mat => mat.name === "Factor");
                    const mat_Color = asset.materials.find(mat => mat.name === "Color");
                    const mat_SpecTex = asset.materials.find(mat => mat.name === "SpecTex");
                    const mat_SpecTexFac = asset.materials.find(mat => mat.name === "SpecTexFac");
                    const mat_SpecColorTex = asset.materials.find(mat => mat.name === "SpecColorTex");
                    const mat_SpecColorTexFac = asset.materials.find(mat => mat.name === "SpecColorTexFac");

                    assert.strictEqual(mat_SpecDefault.extensions, undefined);

                    if ('specularColorFactor' in mat_Factor.extensions['KHR_materials_specular']) {
                        assert.equalEpsilonArray(mat_Factor.extensions['KHR_materials_specular']['specularColorFactor'], [1.0, 1.0, 1.0]);
                    } else {
                        assert.ok(!("specularColorFactor" in mat_Factor.extensions['KHR_materials_specular']));
                    }
                    assert.ok(!("specularTexture" in mat_Factor.extensions['KHR_materials_specular']));
                    assert.ok(!("specularColorTexture" in mat_Factor.extensions['KHR_materials_specular']));
                    assert.equalEpsilon(mat_Factor.extensions['KHR_materials_specular']['specularFactor'], 0.8);

                    if ('specularFactor' in mat_Color.extensions['KHR_materials_specular']) {
                        assert.equalEpsilon(mat_Color.extensions['KHR_materials_specular']['specularFactor'], 1.0);
                    } else {
                        assert.ok(!("specularFactor" in mat_Color.extensions['KHR_materials_specular']));
                    }
                    assert.equalEpsilonArray(mat_Color.extensions['KHR_materials_specular']['specularColorFactor'], [0.1, 0.2, 0.3]);
                    assert.ok(!("specularTexture" in mat_Color.extensions['KHR_materials_specular']));
                    assert.ok(!("specularColorTexture" in mat_Color.extensions['KHR_materials_specular']));

                    if ('specularFactor' in mat_SpecTex.extensions['KHR_materials_specular']) {
                        assert.equalEpsilon(mat_SpecTex.extensions['KHR_materials_specular']['specularFactor'], 1.0);
                    } else {
                        assert.ok(!("specularFactor" in mat_SpecTex.extensions['KHR_materials_specular']));
                    }
                    assert.ok("specularTexture" in mat_SpecTex.extensions['KHR_materials_specular']);
                    assert.ok(!("specularColorTexture" in mat_SpecTex.extensions['KHR_materials_specular']));


                    assert.equalEpsilon(mat_SpecTexFac.extensions['KHR_materials_specular']['specularFactor'], 0.75);
                    assert.ok("specularTexture" in mat_SpecTexFac.extensions['KHR_materials_specular']);
                    assert.ok(!("specularColorTexture" in mat_SpecTexFac.extensions['KHR_materials_specular']));

                    if ('specularFactor' in mat_SpecColorTex.extensions['KHR_materials_specular']) {
                        assert.equalEpsilon(mat_SpecColorTex.extensions['KHR_materials_specular']['specularFactor'], 1.0);
                    } else {
                        assert.ok(!("specularFactor" in mat_SpecColorTex.extensions['KHR_materials_specular']));
                    }
                    assert.ok(!("specularTexture" in mat_SpecColorTex.extensions['KHR_materials_specular']));
                    assert.ok("specularColorTexture" in mat_SpecColorTex.extensions['KHR_materials_specular']);
                    if ('specularColorFactor' in mat_SpecColorTex.extensions['KHR_materials_specular']) {
                        assert.equalEpsilonArray(mat_SpecColorTex.extensions['KHR_materials_specular']['specularColorFactor'], [1.0, 1.0, 1.0]);
                    } else {
                        assert.ok(!("specularColorFactor" in mat_SpecColorTex.extensions['KHR_materials_specular']));
                    }

                    if ('specularFactor' in mat_SpecColorTexFac.extensions['KHR_materials_specular']) {
                        assert.equalEpsilon(mat_SpecColorTexFac.extensions['KHR_materials_specular']['specularFactor'], 1.0);
                    } else {
                        assert.ok(!("specularFactor" in mat_SpecColorTexFac.extensions['KHR_materials_specular']));
                    }
                    assert.ok(!("specularTexture" in mat_SpecColorTexFac.extensions['KHR_materials_specular']));
                    assert.ok("specularColorTexture" in mat_SpecColorTexFac.extensions['KHR_materials_specular']);
                    assert.equalEpsilonArray(mat_SpecColorTexFac.extensions['KHR_materials_specular']['specularColorFactor'], [0.2, 0.3, 0.4]);

                });

                it('roundtrips factors', function () {
                    let dir = '22_factors';
                    let outDirPath = path.resolve(OUT_PREFIX, 'roundtrip', dir, outDirName);
                    let gltfPath = path.resolve(outDirPath, dir + '.gltf');
                    const asset = JSON.parse(fs.readFileSync(gltfPath));

                    const mat = asset.materials[0];
                    const pbr = mat.pbrMetallicRoughness;

                    assert.equalEpsilonArray(mat.extensions['KHR_materials_sheen']["sheenColorFactor"], [0.1, 0.2, 0.3]);
                    assert.equalEpsilon(mat.extensions['KHR_materials_sheen']["sheenRoughnessFactor"], 0.5);
                    assert.equalEpsilonArray(pbr.baseColorFactor, [0.5, 0.6, 0.7, 0.123]);
                    assert.equalEpsilon(mat.extensions['KHR_materials_clearcoat']["clearcoatFactor"], 0.234);
                    assert.equalEpsilon(mat.extensions['KHR_materials_clearcoat']["clearcoatRoughnessFactor"], 0.345);
                    assert.equalEpsilon(mat.extensions['KHR_materials_transmission']["transmissionFactor"], 0.36);
                    assert.equalEpsilonArray(mat.emissiveFactor, [0.4, 0.5, 0.6]);
                    assert.equalEpsilon(pbr.metallicFactor, 0.2);
                    assert.equalEpsilon(pbr.roughnessFactor, 0.3);
                    assert.equalEpsilon(mat.extensions['KHR_materials_volume']["thicknessFactor"], 0.9);
                    assert.equalEpsilon(mat.extensions['KHR_materials_specular']["specularFactor"], 0.25);
                    assert.equalEpsilonArray(mat.extensions['KHR_materials_specular']["specularColorFactor"], [0.7, 0.6, 0.5]);

                });

                it('roundtrips multi prim vertex attribute', function () {
                    let dir = '23_multi_prim_vertex_attribute';
                    let outDirPath = path.resolve(OUT_PREFIX, 'roundtrip', dir, outDirName);
                    let gltfPath = path.resolve(outDirPath, dir + '.gltf');
                    const asset = JSON.parse(fs.readFileSync(gltfPath));

                    assert.strictEqual(asset.meshes.length, 1);
                    assert.strictEqual(asset.meshes[0].primitives.length, 2);
                    const primitive1 = asset.meshes[0].primitives[0];
                    assert.strictEqual(asset.accessors[primitive1.attributes['_PRESSURE']].count, 12);
                    const primitive2 = asset.meshes[0].primitives[1];
                    assert.strictEqual(asset.accessors[primitive2.attributes['_PRESSURE']].count, 4);
                });

                it('roundtrips gpu instances', function () {
                    let dir = '24_gpu_instancing';
                    let outDirPath = path.resolve(OUT_PREFIX, 'roundtrip', dir, outDirName);
                    let gltfPath = path.resolve(outDirPath, dir + '.gltf');
                    const asset = JSON.parse(fs.readFileSync(gltfPath));

                    assert.strictEqual(asset.meshes.length, 2);
                    assert.strictEqual(asset.nodes.length, 6);

                });

                it('roundtrips anisotropy', function () {
                    let dir = '25_anisotropy';
                    let outDirPath = path.resolve(OUT_PREFIX, 'roundtrip', dir, outDirName);
                    let gltfPath = path.resolve(outDirPath, dir + '.gltf');
                    const asset = JSON.parse(fs.readFileSync(gltfPath));

                    const mat_roughness_0_5 = asset.materials.find(mat => mat.name === "roughness 0.5");
                    assert.equalEpsilon(mat_roughness_0_5.extensions['KHR_materials_anisotropy']["anisotropyStrength"], 1.0);
                    assert.ok("anisotropyTexture" in mat_roughness_0_5.extensions['KHR_materials_anisotropy']);
                    assert.ok(!("anisotropyRotation" in mat_roughness_0_5.extensions['KHR_materials_anisotropy']));

                    const mat_roughness_1_0 = asset.materials.find(mat => mat.name === "roughness 1.0");
                    assert.equalEpsilon(mat_roughness_1_0.extensions['KHR_materials_anisotropy']["anisotropyStrength"], 1.0);
                    assert.equalEpsilon(mat_roughness_1_0.extensions['KHR_materials_anisotropy']["anisotropyRotation"], 0.349);
                    assert.ok("anisotropyTexture" in mat_roughness_1_0.extensions['KHR_materials_anisotropy']);

                    const tan_text = asset.materials.find(mat => mat.name === "Aniso Tan + Texture");
                    assert.equalEpsilon(tan_text.extensions['KHR_materials_anisotropy']["anisotropyStrength"], 0.8);
                    assert.ok(!("anisotropyRotation" in tan_text.extensions['KHR_materials_anisotropy']));
                    assert.ok("anisotropyTexture" in tan_text.extensions['KHR_materials_anisotropy']);

                    const tan_rot = asset.materials.find(mat => mat.name === "Aniso Tan + Rotation + Texture");
                    assert.equalEpsilon(tan_rot.extensions['KHR_materials_anisotropy']["anisotropyStrength"], 1.0);
                    assert.equalEpsilon(tan_rot.extensions['KHR_materials_anisotropy']["anisotropyRotation"], 0.349065840);
                    assert.ok("anisotropyTexture" in tan_rot.extensions['KHR_materials_anisotropy']);

                });

            });
        });
    });
});
