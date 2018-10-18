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


// TODO: move this to environment variables
var gltfValidatorCommand = 'dart /opt/glTF-Validator/build/bin/gltf_validator.snapshot -r -a -p';

var blenderSampleScenes = ["01_alpha_blend", "01_alpha_mask", "01_color_attribute", "01_cs_morph", "01_cs_rotate", "01_cs_scale", "01_cs_translate", "01_cube", "01_cube_no_material", "01_metallic_sphere", "01_morphed_cube", "01_morphed_cube_no_uv", "01_morphed_triangle", "01_plane", "01_sphere", "01_textured_sphere", "01_triangle", "01_two_sided_plane", "02_node_hierarchy", "02_shared_mesh", "02_suzanne", "03_all_animations", "03_animated_cube", "03_skinned_cylinder", "04_common_materials", "04_lenna", "04_lights", "04_sphere_specular_glossiness", "05_metallic_sphere_light", "05_node_material", "06_parent-inverse-anim", "07_nla-anim"];

function blenderFileToGltf(blenderPath, done, options='') {
    const { exec } = require('child_process');
    const cmd = `blender -b --addons io_scene_gltf2 -noaudio ${blenderPath} --python export_gltf.py -- ${options}`;
    var prc = exec(cmd, (error, stdout, stderr) => {
        if (error) {
            done(error);
            return;
        }
        done();
    });
}

function validateGltf(gltfPath, done) {
    const { exec } = require('child_process');
    const cmd = `${gltfValidatorCommand} ${gltfPath}`;
    var prc = exec(cmd, (error, stdout, stderr) => {
        if (error) {
            //console.error(`exec error: ${error}`);
            done(error);
            return;
        }
        //console.log(`stdout: ${stdout}`);
        //console.log(`stderr: ${stderr}`);
        done();
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
    describe('blender_export', function() {
        blenderSampleScenes.forEach((scene) => {
            it(scene, function(done) {
                var blenderPath = `scenes/${scene}.blend`;
                var gltfPath = `scenes/${scene}.gltf`;
                blenderFileToGltf(blenderPath, (error) => {
                    if (error)
                        return done(error);

                    validateGltf(gltfPath, done);
                });
            });
        });
    });
    describe('blender_export_glb', function() {
        blenderSampleScenes.forEach((scene) => {
            it(scene, function(done) {
                var blenderPath = `scenes/${scene}.blend`;
                var glbPath = `scenes/glb/${scene}.glb`;
                blenderFileToGltf(blenderPath, (error) => {
                    if (error)
                        return done(error);

                    validateGltf(glbPath, done);
                }, '--glb');
            });
        });
    });
    /*describe('blender_export_experimental', function() {
        blenderSampleScenes.forEach((scene) => {
            it(scene, function(done) {
                var blenderPath = `scenes/${scene}.blend`;
                var gltfPath = `scenes/${scene}.gltf`;
                blenderFileToGltf(blenderPath, (error) => {
                    if (error)
                        return done(error);

                    validateGltf(gltfPath, done);
                }, '--experimental');
            });
        });
    });
    describe('blender_export_experimental_glb', function() {
        blenderSampleScenes.forEach((scene) => {
            it(scene, function(done) {
                var blenderPath = `scenes/${scene}.blend`;
                var glbPath = `scenes/glb/${scene}.glb`;
                blenderFileToGltf(blenderPath, (error) => {
                    if (error)
                        return done(error);

                    validateGltf(glbPath, done);
                }, '--experimental --glb');
            });
        });
    });*/
});
