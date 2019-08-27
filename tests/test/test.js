// Copyright (c) 2018 The Khronos Group Inc.
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
    "blender28",
    "blender279b"
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

        if (vectorHashTable.hasOwnProperty(key)) {
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

            it('can export an emissive map', function() {
                let gltfPath = path.resolve(outDirPath, '01_principled_material.gltf');
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
                        let gltfSrcReport = JSON.parse(fs.readFileSync(`roundtrip/${dir}/${dir}_report.json`, 'utf8'));
                        let ext = args.indexOf('--glb') === -1 ? '.gltf' : '.glb';
                        let outDirPath = path.resolve(OUT_PREFIX, 'roundtrip', dir, outDirName);
                        let gltfDstPath = path.resolve(outDirPath, `${dir}${ext}`);
                        blenderRoundtripGltf(blenderVersion, gltfSrcPath, outDirPath, (error) => {
                            if (error)
                                return done(error);

                            validateGltf(gltfDstPath, (error, gltfDstReport) => {
                                if (error)
                                    return done(error);

                                const info_keys = ['version', 'hasAnimations', 'hasMaterials', 'hasMorphTargets', 'hasSkins', 'hasTextures', 'hasDefaultScene', 'primitivesCount'/*, 'maxAttributesUsed'*/];
                                let reduceKeys = function(raw, allowed) {
                                    return Object.keys(raw)
                                        .filter(key => allowed.includes(key))
                                        .reduce((obj, key) => {
                                            obj[key] = raw[key];
                                            return obj;
                                        }, {});
                                };

                                let srcInfo = reduceKeys(gltfSrcReport.info, info_keys);
                                let dstInfo = reduceKeys(gltfDstReport.info, info_keys);

                                assert.deepStrictEqual(dstInfo, srcInfo);

                                done();
                            });
                        }, args);
                    });
                });
            });
        });

        describe(blenderVersion + '_roundtrip_results', function() {
            let outDirName = 'out' + blenderVersion;

            if (blenderVersion !== 'blender279b') {
                // Only Blender 2.80 and above will roundtrip alpha blend mode.
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

                // Only Blender 2.80 and above will roundtrip alpha mask mode.
                it('roundtrips alpha mask mode', function() {
                    let dir = '01_alpha_mask';
                    let outDirPath = path.resolve(OUT_PREFIX, 'roundtrip', dir, outDirName);
                    let gltfPath = path.resolve(outDirPath, dir + '.gltf');
                    const asset = JSON.parse(fs.readFileSync(gltfPath));

                    assert.strictEqual(asset.materials.length, 1);
                    assert.strictEqual(asset.materials[0].alphaMode, 'MASK');
                    assert.equalEpsilon(asset.materials[0].alphaCutoff, 0.42);
                });

                // Only Blender 2.80 and above will roundtrip the doubleSided flag.
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
            }

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

            it('roundtrips a texture transform', function() {
                let dir = '09_texture_transform';
                let outDirPath = path.resolve(OUT_PREFIX, 'roundtrip', dir, outDirName);
                let gltfPath = path.resolve(outDirPath, dir + '.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));

                assert.strictEqual(asset.materials.length, 1);
                const transform = asset.materials[0].pbrMetallicRoughness.baseColorTexture.extensions.KHR_texture_transform;

                assert.equalEpsilon(transform.offset[0], 0.1);
                assert.equalEpsilon(transform.offset[1], 0.2);
                assert.equalEpsilon(transform.rotation, 0.3);
                assert.equalEpsilon(transform.scale[0], 4);
                assert.equalEpsilon(transform.scale[1], 5);
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
        });
    });
});
