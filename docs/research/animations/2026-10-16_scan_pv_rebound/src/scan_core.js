// Core geometry for the SCAN/EGO (p_j, v_j) animation.
// Mirrors bspline_optimizer.cpp: initControlPoints (L61-L297) and calcDistanceCostRebound (L405-L441).
// 2-D, resolution = 1 cell. Exported for node testing and inlined into the HTML.
(function (root) {
  const W = 48, H = 27, RES = 1.0;
  const smooth = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
  function topProfile(x) {
    let t = 19.0;
    t -= 7.0 * (1 - smooth(14.5, 19.0, x));      // rounded left flank
    t -= 7.0 * smooth(29.0, 33.5, x);            // rounded right flank
    t -= 4.2 * (smooth(20.2, 21.4, x) - smooth(26.6, 27.8, x)); // concave notch on top
    return t;
  }
  function rawOcc(i, j) {
    const x = i + 0.5, y = j + 0.5;
    return x > 14.0 && x < 34.0 && y > 3.0 && y < topProfile(x);
  }
  const raw = [], infl = [];
  for (let i = 0; i < W; i++) { raw.push([]); for (let j = 0; j < H; j++) raw[i].push(rawOcc(i, j)); }
  for (let i = 0; i < W; i++) {
    infl.push([]);
    for (let j = 0; j < H; j++) {
      let o = false;
      for (let di = -1; di <= 1 && !o; di++) for (let dj = -1; dj <= 1 && !o; dj++) {
        const a = i + di, b = j + dj;
        if (a >= 0 && a < W && b >= 0 && b < H && raw[a][b]) o = true;
      }
      infl[i].push(o);
    }
  }
  const occAt = (x, y) => { const i = Math.floor(x), j = Math.floor(y); if (i < 0 || j < 0 || i >= W || j >= H) return true; return infl[i][j]; };

  // Initial control points (uniform cubic B-spline, order 3)
  const Q0 = [[3, 12.2], [8, 12.8], [13, 13.3], [18.5, 13.7], [24, 13.9], [29.5, 13.6], [35, 13.1], [40, 12.6], [45, 12.1]];
  const ORDER = 3;

  // --- collision segmentation along control polygon (L72-L130) ---
  function segment(Q) {
    const n = Q.length;
    const avg = Math.hypot(Q[0][0] - Q[n - 1][0], Q[0][1] - Q[n - 1][1]) / (n - 1);
    const step = RES / avg / 2;
    const ENOUGH = 2; let same = ENOUGH + 1, last = false, gotS = false, gotE = false, maybe = false, inId = -1, outId = -1;
    const segs = [], samples = [];
    const iEnd = n - ORDER - Math.floor((n - 2 * ORDER) / 3);
    for (let i = ORDER - 2; i <= n - 1; i++) { // demo: scan whole polygon (code scans i in [order, i_end])
      if (i < 1) continue;
      for (let a = 1.0; a >= 0.0; a -= step) {
        const x = a * Q[i - 1][0] + (1 - a) * Q[i][0], y = a * Q[i - 1][1] + (1 - a) * Q[i][1];
        const occ = occAt(x, y);
        samples.push({ x, y, occ, i });
        if (occ && !last) { if (same > ENOUGH || i === ORDER) { inId = i - 1; gotS = true; } same = 0; maybe = false; }
        else if (!occ && last) { outId = i; maybe = true; same = 0; }
        else same++;
        if (maybe && (same > ENOUGH || i === n - ORDER)) { maybe = false; gotE = true; }
        last = occ;
        if (gotS && gotE) { gotS = gotE = false; segs.push([inId, outId]); }
      }
    }
    return { segs, samples, iEnd };
  }

  // --- 8-connected A* on inflated grid (stand-in for dyn_a_star) ---
  function astar(s, g) {
    const key = (i, j) => i * H + j;
    const si = Math.floor(s[0]), sj = Math.floor(s[1]), gi = Math.floor(g[0]), gj = Math.floor(g[1]);
    const h = (i, j) => { const dx = Math.abs(i - gi), dy = Math.abs(j - gj); return (dx + dy) + (Math.SQRT2 - 2) * Math.min(dx, dy); };
    const gS = new Map(), parent = new Map(), closed = new Set(), order = [];
    const open = [[h(si, sj), 0, si, sj]]; gS.set(key(si, sj), 0);
    while (open.length) {
      open.sort((a, b) => a[0] - b[0] || b[1] - a[1]);
      const [, gc, i, j] = open.shift();
      const k = key(i, j); if (closed.has(k)) continue; closed.add(k); order.push([i, j]);
      if (i === gi && j === gj) break;
      for (let di = -1; di <= 1; di++) for (let dj = -1; dj <= 1; dj++) {
        if (!di && !dj) continue;
        const a = i + di, b = j + dj;
        if (a < 0 || b < 0 || a >= W || b >= H || infl[a][b]) continue;
        if (di && dj && (infl[i + di][j] || infl[i][j + dj])) continue;
        const ng = gc + (di && dj ? Math.SQRT2 : 1), kk = key(a, b);
        if (ng < (gS.has(kk) ? gS.get(kk) : Infinity)) { gS.set(kk, ng); parent.set(kk, k); open.push([ng + h(a, b) * 1.0001, ng, a, b]); }
      }
    }
    const path = []; let k = key(gi, gj);
    while (k !== undefined) { const i = Math.floor(k / H), j = k % H; path.push([i + 0.5, j + 0.5]); k = parent.get(k); }
    path.reverse();
    path[0] = s.slice(); path[path.length - 1] = g.slice(); // code uses exact in/out endpoints
    return { path, expanded: order };
  }

  // --- normal-plane intersection + ray stepping (L236-L297) ---
  const sub = (a, b) => [a[0] - b[0], a[1] - b[1]], dot = (a, b) => a[0] * b[0] + a[1] * b[1];
  function pv(Q, j, path) {
    const law = sub(Q[j + 1], Q[j - 1]);
    let id = Math.floor(path.length / 2), lastId, val = dot(sub(path[id], Q[j]), law), lastVal = val, P = null;
    const walk = [id];
    while (id >= 0 && id < path.length) {
      lastId = id; lastVal = val;
      id += val >= 0 ? -1 : 1;
      if (id < 0 || id >= path.length) break;
      walk.push(id);
      val = dot(sub(path[id], Q[j]), law);
      if (val * lastVal <= 0 && (Math.abs(val) > 0 || Math.abs(lastVal) > 0)) {
        const d = sub(path[id], path[lastId]), den = dot(law, d);
        const t = dot(law, sub(Q[j], path[id])) / den;
        P = [path[id][0] + d[0] * t, path[id][1] + d[1] * t];
        break;
      }
    }
    if (!P) return null;
    const L = Math.hypot(P[0] - Q[j][0], P[1] - Q[j][1]);
    const steps = []; let base = null;
    for (let a = L; a >= 0; a -= RES) {
      const s = [(a / L) * P[0] + (1 - a / L) * Q[j][0], (a / L) * P[1] + (1 - a / L) * Q[j][1]];
      const occ = occAt(s[0], s[1]);
      steps.push({ p: s, occ, a });
      if (occ || a < RES) {
        const aa = occ ? a + RES : a;
        base = [(aa / L) * P[0] + (1 - aa / L) * Q[j][0], (aa / L) * P[1] + (1 - aa / L) * Q[j][1]];
        break;
      }
    }
    const v = [(P[0] - Q[j][0]) / L, (P[1] - Q[j][1]) / L];
    return { j, law, P, walk, steps, base, v, L };
  }

  // --- optimisation: jerk smoothness + rebound distance cost (L405-L441) ---
  function optimise(Qinit, pairs, sf, opts) {
    const o = Object.assign({ lamS: 1.0, lamD: 20.0, iters: 600, lr: 0.004, fixed: 2 }, opts || {});
    const Q = Qinit.map(q => q.slice()); const n = Q.length; const hist = [Q.map(q => q.slice())];
    const a3 = 3 * sf, b3 = -3 * sf * sf, c3 = sf ** 3;
    for (let it = 0; it < o.iters; it++) {
      const G = Q.map(() => [0, 0]);
      for (let i = 0; i + 3 < n; i++) {
        const jx = Q[i + 3][0] - 3 * Q[i + 2][0] + 3 * Q[i + 1][0] - Q[i][0];
        const jy = Q[i + 3][1] - 3 * Q[i + 2][1] + 3 * Q[i + 1][1] - Q[i][1];
        const c = [-1, 3, -3, 1];
        for (let k = 0; k < 4; k++) { G[i + k][0] += o.lamS * 2 * c[k] * jx; G[i + k][1] += o.lamS * 2 * c[k] * jy; }
      }
      for (const pr of pairs) {
        const q = Q[pr.j]; const d = (q[0] - pr.base[0]) * pr.v[0] + (q[1] - pr.base[1]) * pr.v[1];
        const e = sf - d; let g = 0;
        if (e < 0) g = 0; else if (e < sf) g = -3 * e * e; else g = -(2 * a3 * e + b3);
        G[pr.j][0] += o.lamD * g * pr.v[0]; G[pr.j][1] += o.lamD * g * pr.v[1];
      }
      for (let i = o.fixed; i < n - o.fixed; i++) { Q[i][0] -= o.lr * G[i][0]; Q[i][1] -= o.lr * G[i][1]; }
      if (it % 4 === 3) hist.push(Q.map(q => q.slice()));
    }
    return { Q, hist };
  }

  // Uniform cubic B-spline sample (with phantom end points so the curve spans Q[0]..Q[n-1])
  function bspline(Q, perSeg) {
    const n = Q.length, P = [[2 * Q[0][0] - Q[1][0], 2 * Q[0][1] - Q[1][1]], ...Q, [2 * Q[n - 1][0] - Q[n - 2][0], 2 * Q[n - 1][1] - Q[n - 2][1]]];
    const out = [];
    for (let s = 0; s + 3 < P.length; s++) for (let k = 0; k <= perSeg; k++) {
      if (k === perSeg && s + 4 < P.length) continue;
      const u = k / perSeg, u2 = u * u, u3 = u2 * u;
      const b0 = (1 - u) ** 3 / 6, b1 = (3 * u3 - 6 * u2 + 4) / 6, b2 = (-3 * u3 + 3 * u2 + 3 * u + 1) / 6, b3 = u3 / 6;
      out.push([b0 * P[s][0] + b1 * P[s + 1][0] + b2 * P[s + 2][0] + b3 * P[s + 3][0], b0 * P[s][1] + b1 * P[s + 1][1] + b2 * P[s + 2][1] + b3 * P[s + 3][1]]);
    }
    return out;
  }

  function solve(sf, opts) {
    const seg = segment(Q0);
    const [inId, outId] = seg.segs[0];
    const as = astar(Q0[inId], Q0[outId]);
    const pairs = [];
    for (let j = inId + 1; j < outId; j++) { const r = pv(Q0, j, as.path); if (r) pairs.push(r); }
    const opt = optimise(Q0, pairs, sf, opts);
    const curve0 = bspline(Q0, 24), curve1 = bspline(opt.Q, 24);
    const hits = curve1.filter(p => occAt(p[0], p[1])).length;
    return { W, H, RES, raw, infl, occAt, Q0, seg, inId, outId, as, pairs, opt, curve0, curve1, hits, bspline, topProfile };
  }
  const api = { solve };
  if (typeof module !== 'undefined') module.exports = api; else root.SCANCORE = api;
})(this);
