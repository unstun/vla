const fs = require('fs'), path = require('path');
const dir = __dirname;
const core = fs.readFileSync(path.join(dir, 'scan_core.js'), 'utf8').replace('})(this);', '})(window);');
const tpl = fs.readFileSync(path.join(dir, 'film.template.html'), 'utf8');
const out = path.join(dir, '..', 'scan_pv_rebound_animation.html');
fs.writeFileSync(out, tpl.replace('/*__CORE__*/', () => core));
console.log('wrote', out, fs.statSync(out).size, 'bytes');
