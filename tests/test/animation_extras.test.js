const { execFileSync } = require('child_process');
const path = require('path');
const fs = require('fs');
const assert = require('assert');
const validator = require('gltf-validator');

describe('animation extras', function () {
    it('imports extras on shared Actions and preserves ordinary animation extras on export', async function () {
        this.timeout(60000);
        const root = path.resolve(__dirname, '../..');
        const output = path.resolve(process.env.OUT_PREFIX || '../tests_out', 'animation-extras-synthetic');
        execFileSync(process.env.BLENDER_BIN || 'blender', [
            '-b', '--python-exit-code', '1', '--python',
            path.join(root, 'tests/check_animation_extras.py'), '--', root, output
        ], { stdio: 'pipe' });
        const filename = '03_all_animations_roundtrip.gltf';
        const result = await validator.validateBytes(new Uint8Array(fs.readFileSync(path.join(output, filename))), {
            uri: filename,
            externalResourceFunction: async uri => new Uint8Array(fs.readFileSync(path.resolve(output, decodeURIComponent(uri))))
        });
        assert.strictEqual(result.issues.numErrors, 0);
        assert.strictEqual(result.issues.numWarnings, 0);
    });
});
