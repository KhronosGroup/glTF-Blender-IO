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
    let epsilon = Math.abs(expected * 1e-6);
    if (Math.abs(actual - expected) > epsilon) {
        throw new Error("Expected " + actual + " to equal " + expected);
    }
};

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

            it('produces an Occlusion texture', function() {
                let resultName = path.resolve(outDirPath, '08_tiny-box-upper-left.png');
                assert(fs.existsSync(resultName));
            });

            it('references the Occlusion texture', function() {
                let gltfPath = path.resolve(outDirPath, '08_only_occlusion.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));

                assert.strictEqual(asset.materials.length, 1);
                assert.strictEqual(asset.materials[0].occlusionTexture.index, 0);
                assert.strictEqual(asset.materials[0].pbrMetallicRoughness.metallicRoughnessTexture, undefined);
                assert.strictEqual(asset.textures.length, 1);
                assert.strictEqual(asset.textures[0].source, 0);
                assert.strictEqual(asset.images.length, 1);
                assert.strictEqual(asset.images[0].uri, '08_tiny-box-upper-left.png');
            });

            it('produces a RoughnessMetallic texture', function() {
                let resultName = path.resolve(outDirPath, '08_tiny-box-lower-left-08_tiny-box-upper-right.png');
                assert(fs.existsSync(resultName));
            });

            it('combines two images into a RoughnessMetallic texture', function() {
                let resultName = path.resolve(outDirPath, '08_tiny-box-lower-left-08_tiny-box-upper-right.png');
                let expectedRgbBuffer = fs.readFileSync('scenes/08_tiny-box-_gb.png');
                let testBuffer = fs.readFileSync(resultName);
                assert(testBuffer.equals(expectedRgbBuffer));
            });

            it('references the RoughnessMetallic texture', function() {
                let gltfPath = path.resolve(outDirPath, '08_only_roughMetal.gltf');
                const asset = JSON.parse(fs.readFileSync(gltfPath));

                assert.strictEqual(asset.materials.length, 1);
                assert.strictEqual(asset.materials[0].occlusionTexture, undefined);
                assert.strictEqual(asset.materials[0].pbrMetallicRoughness.metallicRoughnessTexture.index, 0);
                assert.strictEqual(asset.textures.length, 1);
                assert.strictEqual(asset.textures[0].source, 0);
                assert.strictEqual(asset.images.length, 1);
                assert.strictEqual(asset.images[0].uri, '08_tiny-box-lower-left-08_tiny-box-upper-right.png');
            });

            it('produces an OcclusionRoughnessMetallic texture', function() {
                let resultName = path.resolve(outDirPath, '08_tiny-box-upper-left-08_tiny-box-upper-right-08_tiny-box-lower-left.png');
                assert(fs.existsSync(resultName));
            });

            it('combines three images into an OcclusionRoughnessMetallic texture', function() {
                let resultName = path.resolve(outDirPath, '08_tiny-box-upper-left-08_tiny-box-upper-right-08_tiny-box-lower-left.png');
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
                assert.strictEqual(asset.textures.length, 1);
                assert.strictEqual(asset.textures[0].source, 0);
                assert.strictEqual(asset.images.length, 1);
                assert.strictEqual(asset.images[0].uri, '08_tiny-box-upper-left-08_tiny-box-upper-right-08_tiny-box-lower-left.png');
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
        });
    });
});
