const { solve } = require('./scan_core.js');
const sf = parseFloat(process.argv[2] || '1.5');
const r = solve(sf);
const f = a => a.map(v => v.toFixed(2)).join(',');
console.log('segments', JSON.stringify(r.seg.segs), 'in', r.inId, 'out', r.outId);
console.log('Q0 occ', r.Q0.map(q => r.occAt(q[0], q[1]) ? 1 : 0).join(''));
console.log('astar len', r.as.path.length, 'expanded', r.as.expanded.length);
console.log('path ys', r.as.path.map(p => p[1].toFixed(1)).join(' '));
for (const p of r.pairs) {
  const q = r.Q0[p.j];
  const d = (q[0] - p.base[0]) * p.v[0] + (q[1] - p.base[1]) * p.v[1];
  console.log(`Q${p.j + 1} Q=(${f(q)}) P=(${f(p.P)}) base=(${f(p.base)}) v=(${f(p.v)}) L=${p.L.toFixed(2)} steps=${p.steps.length} d=${d.toFixed(2)}`);
}
console.log('final Q', r.opt.Q.map(q => '(' + f(q) + ')').join(' '));
for (const p of r.pairs) { const q = r.opt.Q[p.j]; console.log(`Q${p.j + 1} final d=${((q[0] - p.base[0]) * p.v[0] + (q[1] - p.base[1]) * p.v[1]).toFixed(2)}`); }
console.log('final control pts occ', r.opt.Q.map(q => r.occAt(q[0], q[1]) ? 1 : 0).join(''));
console.log('curve hits initial', r.curve0.filter(p => r.occAt(p[0], p[1])).length, 'final', r.hits, 'hist', r.opt.hist.length);
// ascii map
for (let j = r.H - 1; j >= 0; j--) {
  let s = '';
  for (let i = 0; i < r.W; i++) {
    const onPath = r.as.path.some(p => Math.floor(p[0]) === i && Math.floor(p[1]) === j);
    const qi = r.opt.Q.findIndex(q => Math.floor(q[0]) === i && Math.floor(q[1]) === j);
    const q0 = r.Q0.findIndex(q => Math.floor(q[0]) === i && Math.floor(q[1]) === j);
    s += q0 >= 0 ? String(q0 + 1) : qi >= 0 ? 'F' : onPath ? '*' : r.raw[i][j] ? '#' : r.infl[i][j] ? '+' : '.';
  }
  console.log(s);
}
