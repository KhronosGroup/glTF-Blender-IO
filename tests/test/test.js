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

function blenderFileToGltf(blenderVersion, blenderPath, outDirName, done, options='') {
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

function blenderRoundtripGltf(blenderVersion, gltfPath, outDirName, done, options='') {
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
assert.equalEpsilon = function(actual, expected) {
    if (typeof actual !== 'number') {
        throw new Error("Expected " + actual + " to be a number.");
    }
    let epsilon = 1e-6;
    epsilon = Math.max(epsilon, Math.abs(expected * epsilon));
    if (Math.abs(actual - expected) > epsilon) {
        throw new Error("Expected " + actual + " to equal " + expected);
    }
};

assert.equalEpsilonArray = function(actual, expected) {
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
    default:
        throw new Error("Untested accessor componentType " + accessor.componentType);
    }

    let numElements;
    switch (accessor.type) {
    case 'SCALAR':
        numElements = 1;
        break;
    case 'VEC3':
        numElements = 3;
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
            accessorData.push(bufferViewData.readFloatLE(o + (j * componentSize)));
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

describe('General', function() {
    describe('gltf_validator', function() {
        it('should verify a simple glTF file without errors', function(done) {
            validateGltf('gltf/Box.gltf', done);
        });
        it('should verify a simple glTF binary file without errors', function(done) {
            validateGltf('gltf/Box.glb', done);
        });
    });
});

describe('Exporter', function() {
    let blenderSampleScenes = fs.readdirSync('scenes').filter(f => f.endsWith('.blend')).map(f => f.substring(0, f.length - 6));

    blenderVersions.forEach(function(blenderVersion) {
        let variants = [
            ['', ''],
            ['_glb', '--glb']
        ];

        variants.forEach(function(variant) {
            const args = variant[1];
            describe(blenderVersion + '_export' + variant[0], function() {
                blenderSampleScenes.forEach((scene) => {
                    it(scene, function(done) {
                        let outDirName = 'out' + blenderVersion + variant[0];
                        let blenderPath = `scenes/${scene}.blend`;
                        let ext = args.indexOf('--glb') === -1 ? '.gltf' : '.glb';
                        let outDirPath = path.resolve(OUT_PREFIX, 'scenes', outDirName);
                        let dstPath = path.resolve(outDirPath, `${scene}${ext}`);
                        blenderFileToGltf(blenderVersion, blenderPath, outDirPath, (error) => {
                            if (error)
                                return done(error);

                            validateGltf(dstPath, done);
                        }, args);
                    });
                });
            });
        });

        describe(blenderVersion + '_export_results', function() {
            let outDirName = 'out' + blenderVersion;
            let outDirPath = path.resolve(OUT_PREFIX, 'scenes', outDirName);

            it('can export a base color', function() {
                let gltfPath = path.resolve(outDirPath, '01_principled_material.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));

                assert.strictEqual(asset.materials.length, 1);
                const textureIndex = asset.materials[0].pbrMetallicRoughness.baseColorTexture.index;
                const imageIndex = asset.textures[textureIndex].source;

                assert.strictEqual(asset.images[imageIndex].uri, '01_principled_baseColor.png');
                assert(fs.existsSync(path.resolve(outDirPath, '01_principled_baseColor.png')));
            });

            it('can export a normal map', function() {
                let gltfPath = path.resolve(outDirPath, '01_principled_material.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));

                assert.strictEqual(asset.materials.length, 1);
                const textureIndex = asset.materials[0].normalTexture.index;
                const imageIndex = asset.textures[textureIndex].source;

                assert.strictEqual(asset.images[imageIndex].uri, '01_principled_normal.png');
                assert(fs.existsSync(path.resolve(outDirPath, '01_principled_normal.png')));
            });

            it('can export an emissive map from the Emission node', function() {
                let gltfPath = path.resolve(outDirPath, '01_principled_material.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));

                assert.strictEqual(asset.materials.length, 1);
                const textureIndex = asset.materials[0].emissiveTexture.index;
                const imageIndex = asset.textures[textureIndex].source;

                assert.strictEqual(asset.images[imageIndex].uri, '01_principled_emissive.png');
                assert.deepStrictEqual(asset.materials[0].emissiveFactor, [1, 1, 1]);
                assert(fs.existsSync(path.resolve(outDirPath, '01_principled_emissive.png')));
            });

            it('can export an emissive map from the Principled BSDF node', function() {
                let gltfPath = path.resolve(outDirPath, '01_principled_material_280.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));

                assert.strictEqual(asset.materials.length, 1);
                const textureIndex = asset.materials[0].emissiveTexture.index;
                const imageIndex = asset.textures[textureIndex].source;

                assert.strictEqual(asset.images[imageIndex].uri, '01_principled_emissive.png');
                assert.deepStrictEqual(asset.materials[0].emissiveFactor, [1, 1, 1]);
                assert(fs.existsSync(path.resolve(outDirPath, '01_principled_emissive.png')));
            });

            it('can create instances of a mesh with different materials', function() {
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

            it('exports UNSIGNED_SHORT when count is 65535', function() {
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

            it('exports UNSIGNED_INT when count is 65536', function() {
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

            it('produces a Roughness texture', function() {
                // Expect magenta (inverted green) square
                let resultName = path.resolve(outDirPath, '08_img_rough.png');
                let expectedRgbBuffer = fs.readFileSync('scenes/08_tiny-box-_g_.png');
                let testBuffer = fs.readFileSync(resultName);
                assert(testBuffer.equals(expectedRgbBuffer));
            });

            it('references the Roughness texture', function() {
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

            it('produces a Metallic texture', function() {
                // Expect yellow (inverted blue) square
                let resultName = path.resolve(outDirPath, '08_img_metal.png');
                let expectedRgbBuffer = fs.readFileSync('scenes/08_tiny-box-__b.png');
                let testBuffer = fs.readFileSync(resultName);
                assert(testBuffer.equals(expectedRgbBuffer));
            });

            it('references the Metallic texture', function() {
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

            it('combines two images into a RoughnessMetallic texture', function() {
                // Expect magenta (inverted green) and yellow (inverted blue) squares
                let resultName = path.resolve(outDirPath, '08_metallic-08_roughness.png');
                let expectedRgbBuffer = fs.readFileSync('scenes/08_tiny-box-_gb.png');
                let testBuffer = fs.readFileSync(resultName);
                assert(testBuffer.equals(expectedRgbBuffer));
            });

            it('references the RoughnessMetallic texture', function() {
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

            it('produces an Occlusion texture', function() {
                // Expect upper-left black square.  This is a special case because when R/M are not
                // present, occlusion may take all channels.  This test now "expects" the
                // grayscale PNG to be preserved exactly.
                let resultName = path.resolve(outDirPath, '08_img_occlusion.png');
                let expectedRgbBuffer = fs.readFileSync('scenes/08_img_occlusion.png');
                let testBuffer = fs.readFileSync(resultName);
                assert(testBuffer.equals(expectedRgbBuffer));
            });

            it('references the Occlusion texture', function() {
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

            it('combines two images into an OcclusionRoughness texture', function() {
                // Expect cyan (inverted red) and magenta (inverted green) squares
                let resultName = path.resolve(outDirPath, '08_occlusion-08_roughness.png');
                let expectedRgbBuffer = fs.readFileSync('scenes/08_tiny-box-rg_.png');
                let testBuffer = fs.readFileSync(resultName);
                assert(testBuffer.equals(expectedRgbBuffer));
            });

            it('references the OcclusionRoughness texture', function() {
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

            it('combines two images into an OcclusionMetallic texture', function() {
                // Expect cyan (inverted red) and yellow (inverted blue) squares
                let resultName = path.resolve(outDirPath, '08_occlusion-08_metallic.png');
                let expectedRgbBuffer = fs.readFileSync('scenes/08_tiny-box-r_b.png');
                let testBuffer = fs.readFileSync(resultName);
                assert(testBuffer.equals(expectedRgbBuffer));
            });

            it('references the OcclusionMetallic texture', function() {
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

            it('combines three images into an OcclusionRoughnessMetallic texture', function() {
                // Expect cyan (inverted red), magenta (inverted green), and yellow (inverted blue) squares
                let resultName = path.resolve(outDirPath, '08_occlusion-08_roughness-08_metallic.png');
                let expectedRgbBuffer = fs.readFileSync('scenes/08_tiny-box-rgb.png');
                let testBuffer = fs.readFileSync(resultName);
                assert(testBuffer.equals(expectedRgbBuffer));
            });

            it('references the OcclusionRoughnessMetallic texture', function() {
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

            it('can share a normal map and a Clearcoat normal map', function() {
                let gltfPath = path.resolve(outDirPath, '08_clearcoat.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));

                assert.strictEqual(asset.materials.length, 1);
                assert.strictEqual(asset.images.length, 1);
                const clearcoat = asset.materials[0].extensions.KHR_materials_clearcoat;
                assert.equalEpsilon(clearcoat.clearcoatFactor, 0.9);
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

            it('combines two images into a Clearcoat strength and roughness texture', function() {
                // Expect cyan (inverted red) and magenta (inverted green) squares
                let resultName = path.resolve(outDirPath, '08_cc_strength-08_cc_roughness.png');
                let expectedRgbBuffer = fs.readFileSync('scenes/08_tiny-box-rg_.png');
                let testBuffer = fs.readFileSync(resultName);
                assert(testBuffer.equals(expectedRgbBuffer));
            });

            it('references the Clearcoat texture', function() {
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

            it('exports texture transform from mapping type point', function() {
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

            it('exports texture transform from mapping type texture', function() {
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

            it('exports texture transform from mapping type vector', function() {
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

            it('exports custom normals', function() {
                let gltfPath = path.resolve(outDirPath, '10_custom_normals.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));
                assert.strictEqual(asset.meshes.length, 2);

                let bufferCache = {};

                const angleCubeMesh = asset.meshes.filter(m => m.name === 'AngleCube')[0];
                const flatNormals = angleCubeMesh.primitives[0].attributes.NORMAL;
                const flatNormalData = getAccessorData(gltfPath, asset, flatNormals, bufferCache);
                const flatNormalHash = buildVectorHash(flatNormalData);

                // In this mesh, the beveled cube has various angled edges.  Custom normals
                // exist but are not enabled via the auto-smooth flag.  So, many exported
                // normals are not axis-aligned.
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

            it('exports custom normals with Apply Modifiers', function() {
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

            it('exports loose edges/points', function() {
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

            it('exports custom range sampled', function() {
                let gltfPath = path.resolve(outDirPath, '12_anim_range_sampled.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));
                const ranged = asset.animations.filter(a => a.name === 'Ranged')[0];
                const no_ranged = asset.animations.filter(a => a.name === 'NoRange')[0];

                assert.strictEqual(asset.accessors[ranged.samplers[ranged.channels[0].sampler].input].count, 13);
                assert.strictEqual(asset.accessors[no_ranged.samplers[no_ranged.channels[0].sampler].input].count, 15);

                assert.strictEqual(asset.accessors[ranged.samplers[ranged.channels[0].sampler].input].count, asset.accessors[ranged.samplers[ranged.channels[0].sampler].output].count);
                assert.strictEqual(asset.accessors[no_ranged.samplers[no_ranged.channels[0].sampler].input].count, asset.accessors[no_ranged.samplers[no_ranged.channels[0].sampler].output].count);
            });

            it('exports custom range not sampled', function() {
                let gltfPath = path.resolve(outDirPath, '12_anim_range_not_sampled.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));
                const ranged = asset.animations.filter(a => a.name === 'Ranged')[0];
                const no_ranged = asset.animations.filter(a => a.name === 'NoRange')[0];

                assert.strictEqual(asset.accessors[ranged.samplers[ranged.channels[0].sampler].input].count, 2);
                assert.strictEqual(asset.accessors[no_ranged.samplers[no_ranged.channels[0].sampler].input].count, 4);

                assert.strictEqual(asset.accessors[ranged.samplers[ranged.channels[0].sampler].input].count * 3, asset.accessors[ranged.samplers[ranged.channels[0].sampler].output].count);
                assert.strictEqual(asset.accessors[no_ranged.samplers[no_ranged.channels[0].sampler].input].count * 3, asset.accessors[no_ranged.samplers[no_ranged.channels[0].sampler].output].count);
            });

            it('exports custom range with driver', function() {
                let gltfPath = path.resolve(outDirPath, '12_anim_range_driver.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));
                const anim = asset.animations.filter(a => a.name === 'ArmatureAction')[0];

                assert.strictEqual(asset.accessors[anim.samplers[anim.channels[0].sampler].input].count, 7);
                assert.strictEqual(asset.accessors[anim.samplers[anim.channels[1].sampler].input].count, asset.accessors[anim.samplers[anim.channels[0].sampler].input].count);
                assert.strictEqual(anim.samplers[anim.channels[0].sampler].input, anim.samplers[anim.channels[1].sampler].input);
                assert.strictEqual(asset.accessors[anim.samplers[anim.channels[0].sampler].input].count, asset.accessors[anim.samplers[anim.channels[0].sampler].output].count);
                assert.strictEqual(asset.accessors[anim.samplers[anim.channels[0].sampler].output].count, asset.accessors[anim.samplers[anim.channels[1].sampler].output].count);
              })
        });
    });
});

describe('Importer / Exporter (Roundtrip)', function() {
    blenderVersions.forEach(function(blenderVersion) {
        let variants = [
            ['', ''],
            ['_glb', '--glb']
        ];

        variants.forEach(function(variant) {
            const args = variant[1];
            describe(blenderVersion + '_roundtrip' + variant[0], function() {
                let dirs = fs.readdirSync('roundtrip');
                dirs.forEach((dir) => {
                    if (!fs.statSync('roundtrip/' + dir).isDirectory())
                        return;

                    it(dir, function(done) {
                        let outDirName = 'out' + blenderVersion + variant[0];
                        let gltfSrcPath = `roundtrip/${dir}/${dir}.gltf`;
                        let ext = args.indexOf('--glb') === -1 ? '.gltf' : '.glb';
                        let outDirPath = path.resolve(OUT_PREFIX, 'roundtrip', dir, outDirName);
                        let gltfDstPath = path.resolve(outDirPath, `${dir}${ext}`);
                        let gltfOptionsPath = `roundtrip/${dir}/${dir}_options.txt`;
                        let options = args;
                        if (fs.existsSync(gltfOptionsPath)) {
                            options += ' ' + fs.readFileSync(gltfOptionsPath).toString().replace(/\r?\n|\r/g, '');
                        }
                        blenderRoundtripGltf(blenderVersion, gltfSrcPath, outDirPath, (error) => {
                            if (error)
                                return done(error);

                            validateGltf(gltfSrcPath, (error, gltfSrcReport) => {
                                if (error)
                                    return done(error);

                                validateGltf(gltfDstPath, (error, gltfDstReport) => {
                                    if (error)
                                        return done(error);

                                    let reduceKeys = function(raw, allowed) {
                                        return Object.keys(raw)
                                            .filter(key => allowed.includes(key))
                                            .reduce((obj, key) => {
                                                obj[key] = raw[key];
                                                return obj;
                                            }, {});
                                    };

                                    let srcInfo = reduceKeys(gltfSrcReport.info, validator_info_keys);
                                    let dstInfo = reduceKeys(gltfDstReport.info, validator_info_keys);

                                    try {
                                        assert.deepStrictEqual(dstInfo, srcInfo);
                                    } catch (ex) {
                                        done(new Error("Validation summary mismatch.\nExpected summary:\n" +
                                            JSON.stringify(srcInfo, null, '  ') +
                                            "\n\nActual summary:\n" + JSON.stringify(dstInfo, null, '  ')));
                                        return;
                                    }

                                    done();
                                });
                            });
                        }, options);
                    });
                });
            });
        });

        describe(blenderVersion + '_roundtrip_results', function() {
            let outDirName = 'out' + blenderVersion;

            it('roundtrips alpha blend mode', function() {
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

            it('roundtrips alpha mask mode', function() {
                let dir = '01_alpha_mask';
                let outDirPath = path.resolve(OUT_PREFIX, 'roundtrip', dir, outDirName);
                let gltfPath = path.resolve(outDirPath, dir + '.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));

                assert.strictEqual(asset.materials.length, 1);
                assert.strictEqual(asset.materials[0].alphaMode, 'MASK');
                assert.equalEpsilon(asset.materials[0].alphaCutoff, 0.42);
            });

            it('roundtrips the doubleSided flag', function() {
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

            it('roundtrips a morph target animation', function() {
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

            it('roundtrips a base color', function() {
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

            it('roundtrips a normal map', function() {
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

            it('roundtrips an emissive map', function() {
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

            it('roundtrips an OcclusionRoughnessMetallic texture', function() {
                let dir = '08_combine_orm';
                let outDirPath = path.resolve(OUT_PREFIX, 'roundtrip', dir, outDirName);

                assert(fs.existsSync(path.resolve(outDirPath, '08_tiny-box-rgb.png')));
            });

            it('references the OcclusionRoughnessMetallic texture', function() {
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

            it ('roundtrips occlusion strength', function() {
                let dir = '13_occlusion_strength';
                let outDirPath = path.resolve(OUT_PREFIX, 'roundtrip', dir, outDirName);
                let gltfPath = path.resolve(outDirPath, dir + '.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));

                assert.strictEqual(asset.materials.length, 1);
                assert.equalEpsilon(asset.materials[0].occlusionTexture.strength, 0.25);
            })

            it('roundtrips two different UV maps for the same texture', function() {
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

            it('roundtrips baseColorFactor, etc. when used with textures', function() {
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

            it('roundtrips unlit base colors', function() {
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

            it('roundtrips all texture transforms', function() {
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

            it('roundtrips UNSIGNED_SHORT when count is 65535', function() {
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

            it('roundtrips UNSIGNED_INT when count is 65536', function() {
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

            it('roundtrips some custom normals', function() {
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

            it('roundtrips animation names', function() {
                let dir = '07_nla-anim';
                let outDirPath = path.resolve(OUT_PREFIX, 'roundtrip', dir, outDirName);
                let gltfPath = path.resolve(outDirPath, dir + '.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));

                const expectedAnimNames = ["Action2", "Action1", "Action3"];
                const animNames = asset.animations.map(anim => anim.name);
                assert.deepStrictEqual(animNames.sort(), expectedAnimNames.sort());
            });

            it('roundtrips texture wrap modes', function() {
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
            })
        });
    });
});
