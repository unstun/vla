const fs = require('fs');
const path = require('path');

const dir = __dirname;
const core = fs.readFileSync(path.join(dir, 'refine_core.js'), 'utf8');
const tmpl = fs.readFileSync(path.join(dir, 'film.template.html'), 'utf8');
const out = tmpl.replace('/*__CORE__*/', core);

const repoOut = path.resolve(dir, '..', 'scan_time_refine_animation.html');
fs.writeFileSync(repoOut, out, 'utf8');
console.log('Built:', repoOut, 'bytes:', Buffer.byteLength(out));
