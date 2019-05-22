const fs = require('fs');
const path = require('path');
const assert = require('assert');

function readBuffer(buffer, gltfPath) {
    if (buffer.uri && !buffer.uri.startsWith('data:')) {
        if (buffer.uri.startsWith('data:')) {
            return Buffer.from(buffer.uri.split(',')[1], 'base64');
        } else {
            return fs.readFileSync(
                path.resolve(path.dirname(gltfPath), buffer.uri)
            );
        }
    }
    throw new Error('Unable to read buffer');
}

// abstract away some differences in ordering for buffers and bufferViews
function parseGltf(gltf, gltfPath) {
    const buffers = [];
    if (gltf.buffers) {
        for (buffer of gltf.buffers) {
            buffers.push(readBuffer(buffer, gltfPath));
        }
    }

    const bufferViews = [];
    if (gltf.bufferViews) {
        for (const view of gltf.bufferViews) {
            const offset = view.byteOffset || 0;
            bufferViews.push(
                buffers[view.buffer].slice(offset, offset + view.byteLength)
            );
        }
    }

    if (gltf.accessors) {
        for (const accessor of gltf.accessors) {
            accessor.bufferView = bufferViews[accessor.bufferView];
        }
    }

    const parsed = {};
    const exclude = ['buffers', 'bufferViews'];
    for (key of Object.keys(gltf)) {
        if (exclude.indexOf(key) < 0) {
            parsed[key] = gltf[key];
        }
    }

    return parsed;
}

// check .gltf file against expected result
function compareGltf(gltfPath, expectedGltfPath, options = {}) {
    if (!fs.existsSync(expectedGltfPath)) {
        // no expected file to compare to
        return;
    }
    const gltf = JSON.parse(fs.readFileSync(gltfPath));
    const expectedGltf = JSON.parse(fs.readFileSync(expectedGltfPath));
    assert.deepEqual(
        parseGltf(gltf, gltfPath),
        parseGltf(expectedGltf, gltfPath)
    );
}

module.exports = compareGltf;
