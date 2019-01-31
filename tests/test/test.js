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

var blenderSampleScenes = ["01_alpha_blend", "01_alpha_mask", "01_color_attribute", "01_cs_morph", "01_cs_rotate", "01_cs_scale", "01_cs_translate", "01_cube", "01_cube_no_material", "01_metallic_sphere", "01_morphed_cube", "01_morphed_cube_no_uv", "01_morphed_triangle", "01_plane", "01_sphere", "01_textured_sphere", "01_textured_sphere_principled_bsdf", "01_triangle", "01_two_sided_plane", "02_node_hierarchy", "02_shared_mesh", "02_suzanne", "03_all_animations", "03_animated_cube", "03_skinned_cylinder", "04_common_materials", "04_lenna", "04_lights", "04_sphere_specular_glossiness", "05_metallic_sphere_light", "05_node_material", "06_parent-inverse-anim", "07_nla-anim"];

const OUT_PREFIX = process.env.OUT_PREFIX

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
    let blenderVersions = [
        "blender28",
        "blender279b"
    ]
    
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
                        let dstPath = `scenes/${outDirName}/${scene}${ext}`;
                        if (OUT_PREFIX) {
                            outDirName = path.resolve(OUT_PREFIX, 'scenes', outDirName)
                            dstPath = path.resolve(OUT_PREFIX, dstPath)
                        }                    
                        blenderFileToGltf(blenderVersion, blenderPath, outDirName, (error) => {
                            if (error)
                                return done(error);
    
                            validateGltf(dstPath, done);
                        }, args);
                    });
                });
            });
        });
    });    
});

describe('Importer / Exporter (Roundtrip)', function() {
    let blenderVersions = [
        //"blender28",
        "blender279b"
    ]
    
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
                        let gltfDstPath = `roundtrip/${dir}/${outDirName}/${dir}${ext}`;
                        if (OUT_PREFIX) {
                            outDirName = path.resolve(OUT_PREFIX, 'roundtrip', dir, outDirName)
                            gltfDstPath = path.resolve(OUT_PREFIX, gltfDstPath)
                        }                    
                        blenderRoundtripGltf(blenderVersion, gltfSrcPath, outDirName, (error) => {
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
    });
});
