// Core numerical engine for SCAN Step 4: checkFeasibility, lengthenTime, reparamBspline, and BsplineOptimizeTrajRefine.
// Mirrors uniform_bspline.cpp (L14-L279), planner_manager.cpp (L282-L304, L423-L508), and bspline_optimizer.cpp (L443-L716, L951-L1199).
(function (root) {
  const W = 48, H = 27, RES = 1.0, ORDER = 3;
  const smooth = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
  function topProfile(x) {
    let t = 19.0;
    t -= 7.0 * (1 - smooth(15.8, 19.8, x));
    t -= 7.0 * smooth(28.2, 32.2, x);
    t -= 4.0 * (smooth(20.6, 21.7, x) - smooth(26.3, 27.4, x));
    return t;
  }
  function rawOcc(i, j) {
    const x = i + 0.5, y = j + 0.5;
    return x > 15.5 && x < 32.5 && y > 3.0 && y < topProfile(x);
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

  // Dense Gaussian elimination with partial pivoting for solving A * x = b (or A^T A x = A^T b)
  function solveLinear(A, b) {
    const m = A.length, n = A[0].length;
    // Normal equations (A^T A) x = A^T b (matches QR least-squares when overdetermined, exact when square)
    const ATA = Array.from({ length: n }, () => new Float64Array(n + 1));
    for (let i = 0; i < n; i++) {
      for (let j = 0; j < n; j++) {
        let s = 0; for (let k = 0; k < m; k++) s += A[k][i] * A[k][j];
        ATA[i][j] = s;
      }
      let sb = 0; for (let k = 0; k < m; k++) sb += A[k][i] * b[k];
      ATA[i][n] = sb;
    }
    for (let col = 0; col < n; col++) {
      let piv = col;
      for (let r = col + 1; r < n; r++) if (Math.abs(ATA[r][col]) > Math.abs(ATA[piv][col])) piv = r;
      const tmp = ATA[col]; ATA[col] = ATA[piv]; ATA[piv] = tmp;
      const d = ATA[col][col];
      for (let j = col; j <= n; j++) ATA[col][j] /= d;
      for (let r = 0; r < n; r++) if (r !== col) {
        const f = ATA[r][col];
        for (let j = col; j <= n; j++) ATA[r][j] -= f * ATA[col][j];
      }
    }
    return ATA.map(row => row[n]);
  }

  // Mirrors UniformBspline::setUniformBspline (uniform_bspline.cpp L14-L41)
  function makeUniformKnots(numCtrlPts, p, interval) {
    const n = numCtrlPts - 1, m = n + p + 1;
    const u = new Array(m + 1).fill(0);
    for (let i = 0; i <= m; i++) {
      if (i <= p) u[i] = (-p + i) * interval;
      else u[i] = u[i - 1] + interval;
    }
    return u;
  }

  // Mirrors UniformBspline::evaluateDeBoor (uniform_bspline.cpp L60-L93)
  function evaluateDeBoor(ctrlPts, knots, p, uVal) {
    const n = ctrlPts.length - 1, m = n + p + 1;
    const um = knots[p], ump = knots[m - p];
    const ub = Math.min(Math.max(um, uVal), ump);
    let k = p;
    while (k + 1 < m - p && knots[k + 1] < ub) k++;
    const d = [];
    for (let i = 0; i <= p; i++) d.push(ctrlPts[k - p + i].slice());
    for (let r = 1; r <= p; r++) {
      for (let i = p; i >= r; i--) {
        const denom = knots[i + 1 + k - r] - knots[i + k - p];
        const alpha = Math.abs(denom) < 1e-12 ? 0 : (ub - knots[i + k - p]) / denom;
        d[i] = [(1 - alpha) * d[i - 1][0] + alpha * d[i][0], (1 - alpha) * d[i - 1][1] + alpha * d[i][1]];
      }
    }
    return d[p];
  }
  function evaluateDeBoorT(ctrlPts, knots, p, t) {
    return evaluateDeBoor(ctrlPts, knots, p, t + knots[p]);
  }

  // Mirrors UniformBspline::getDerivativeControlPoints & getDerivative (uniform_bspline.cpp L99-L123)
  function getDerivative(ctrlPts, knots, p) {
    const ctp = [];
    for (let i = 0; i < ctrlPts.length - 1; i++) {
      const dt = knots[i + p + 1] - knots[i + 1];
      ctp.push([p * (ctrlPts[i + 1][0] - ctrlPts[i][0]) / dt, p * (ctrlPts[i + 1][1] - ctrlPts[i][1]) / dt]);
    }
    const dKnots = knots.slice(1, knots.length - 1);
    return { ctrlPts: ctp, knots: dKnots, p: p - 1 };
  }

  // Mirrors UniformBspline::parameterizeToBspline (uniform_bspline.cpp L209-L279)
  function parameterizeToBspline(ts, pointSet, startEndDeriv) {
    const K = pointSet.length; // ctrl_pts has K + 2 points
    const rows = K + 4, cols = K + 2;
    const A = Array.from({ length: rows }, () => new Array(cols).fill(0));
    const prow = [1 / 6, 4 / 6, 1 / 6];
    const vrow = [-1 / (2 * ts), 0, 1 / (2 * ts)];
    const arow = [1 / (ts * ts), -2 / (ts * ts), 1 / (ts * ts)];
    for (let i = 0; i < K; i++) for (let j = 0; j < 3; j++) A[i][i + j] = prow[j];
    for (let j = 0; j < 3; j++) {
      A[K][j] = vrow[j];
      A[K + 1][K - 1 + j] = vrow[j];
      A[K + 2][j] = arow[j];
      A[K + 3][K - 1 + j] = arow[j];
    }
    const bx = new Array(rows), by = new Array(rows);
    for (let i = 0; i < K; i++) { bx[i] = pointSet[i][0]; by[i] = pointSet[i][1]; }
    for (let i = 0; i < 4; i++) { bx[K + i] = startEndDeriv[i][0]; by[K + i] = startEndDeriv[i][1]; }
    const px = solveLinear(A, bx), py = solveLinear(A, by);
    return px.map((x, i) => [x, py[i]]);
  }

  // Mirrors UniformBspline::checkFeasibility (uniform_bspline.cpp L134-L192)
  function checkFeasibility(ctrlPts, knots, p, limitVel, limitAcc, tol) {
    let fea = true, maxVel = -1, maxAcc = -1;
    const enlargedVel = limitVel * (1 + tol) + 1e-4;
    const enlargedAcc = limitAcc * (1 + tol) + 1e-4;
    const velCtrl = [], accCtrl = [];
    for (let i = 0; i < ctrlPts.length - 1; i++) {
      const dt = knots[i + p + 1] - knots[i + 1];
      const vx = p * (ctrlPts[i + 1][0] - ctrlPts[i][0]) / dt;
      const vy = p * (ctrlPts[i + 1][1] - ctrlPts[i][1]) / dt;
      const vmag = Math.hypot(vx, vy);
      const overAxis = Math.abs(vx) > enlargedVel || Math.abs(vy) > enlargedVel;
      if (overAxis) {
        fea = false;
        maxVel = Math.max(maxVel, Math.abs(vx), Math.abs(vy));
      }
      velCtrl.push({ i, v: [vx, vy], vmag, overAxis, maxAxis: Math.max(Math.abs(vx), Math.abs(vy)) });
    }
    for (let i = 0; i < ctrlPts.length - 2; i++) {
      const dt2 = knots[i + p + 2] - knots[i + 2];
      const dt1 = knots[i + p + 1] - knots[i + 1];
      const dtM = knots[i + p + 1] - knots[i + 2];
      const ax = p * (p - 1) * ((ctrlPts[i + 2][0] - ctrlPts[i + 1][0]) / dt2 - (ctrlPts[i + 1][0] - ctrlPts[i][0]) / dt1) / dtM;
      const ay = p * (p - 1) * ((ctrlPts[i + 2][1] - ctrlPts[i + 1][1]) / dt2 - (ctrlPts[i + 1][1] - ctrlPts[i][1]) / dt1) / dtM;
      const amag = Math.hypot(ax, ay);
      const overAxis = Math.abs(ax) > enlargedAcc || Math.abs(ay) > enlargedAcc;
      if (overAxis) {
        fea = false;
        maxAcc = Math.max(maxAcc, Math.abs(ax), Math.abs(ay));
      }
      accCtrl.push({ i, a: [ax, ay], amag, overAxis, maxAxis: Math.max(Math.abs(ax), Math.abs(ay)) });
    }
    const velRatio = maxVel > 0 ? maxVel / limitVel : 1.0;
    const accRatio = maxAcc > 0 ? Math.sqrt(Math.abs(maxAcc) / limitAcc) : 1.0;
    const ratio = Math.max(velRatio, accRatio);
    return { fea, ratio, velRatio, accRatio, maxVel, maxAcc, velCtrl, accCtrl };
  }

  // Mirrors UniformBspline::lengthenTime (uniform_bspline.cpp L194-L205)
  function lengthenTime(knotsIn, ratio) {
    const u = knotsIn.slice();
    const num1 = 5;
    const num2 = u.length - 1 - 5;
    const deltaT = (ratio - 1.0) * (u[num2] - u[num1]);
    const tInc = deltaT / (num2 - num1);
    for (let i = num1 + 1; i <= num2; i++) u[i] += (i - num1) * tInc;
    for (let i = num2 + 1; i < u.length; i++) u[i] += deltaT;
    return { knots: u, num1, num2, deltaT, tInc };
  }

  // Sample continuous trajectory profile (pos, vel, acc) over [0, duration]
  function sampleProfile(ctrlPts, knots, p, numSamples) {
    const d1 = getDerivative(ctrlPts, knots, p);
    const d2 = getDerivative(d1.ctrlPts, d1.knots, d1.p);
    const n = ctrlPts.length - 1, m = n + p + 1;
    const duration = knots[m - p] - knots[p];
    const pts = [];
    for (let k = 0; k <= numSamples; k++) {
      const t = duration * k / numSamples;
      const pos = evaluateDeBoorT(ctrlPts, knots, p, t);
      const vel = evaluateDeBoorT(d1.ctrlPts, d1.knots, d1.p, t);
      const acc = evaluateDeBoorT(d2.ctrlPts, d2.knots, d2.p, t);
      pts.push({
        t, pos, vel, acc,
        vmag: Math.hypot(vel[0], vel[1]),
        amag: Math.hypot(acc[0], acc[1]),
        vmaxAxis: Math.max(Math.abs(vel[0]), Math.abs(vel[1])),
        amaxAxis: Math.max(Math.abs(acc[0]), Math.abs(acc[1]))
      });
    }
    return { duration, pts };
  }

  // Mirrors BsplineOptimizer::combineCostRefine (L1173-L1199):
  //   calcSmoothnessCost (L473-L512) + calcFitnessCost (L443-L471) + calcFeasibilityCost (L640-L715)
  function optimizeRefine(initCtrlPts, dt, refPts, maxVel, maxAcc, opts) {
    const o = Object.assign({ lam1: 1.0, lam4: 12.0, lam3: 2.5, iters: 500, lr: 0.002 }, opts || {});
    const Q = initCtrlPts.map(q => q.slice());
    const n = Q.length, endIdx = n - ORDER;
    const hist = [Q.map(q => q.slice())];
    const tsInv2 = 1 / (dt * dt);
    const a2 = 25.0, b2 = 1.0;

    for (let it = 0; it < o.iters; it++) {
      const G = Q.map(() => [0, 0]);
      // 1. Jerk smoothness cost (L479-L495)
      for (let i = 0; i < n - 3; i++) {
        const jx = Q[i + 3][0] - 3 * Q[i + 2][0] + 3 * Q[i + 1][0] - Q[i][0];
        const jy = Q[i + 3][1] - 3 * Q[i + 2][1] + 3 * Q[i + 1][1] - Q[i][1];
        const c = [-1, 3, -3, 1];
        for (let k = 0; k < 4; k++) {
          G[i + k][0] += o.lam1 * 2 * c[k] * jx;
          G[i + k][1] += o.lam1 * 2 * c[k] * jy;
        }
      }
      // 2. Anisotropic Fitness cost (L443-L471): f = (x.v)^2 / a^2 + |x x v|^2 / b^2
      for (let i = ORDER - 1; i < endIdx + 1; i++) {
        const px = (Q[i - 1][0] + 4 * Q[i][0] + Q[i + 1][0]) / 6 - refPts[i - 1][0];
        const py = (Q[i - 1][1] + 4 * Q[i][1] + Q[i + 1][1]) / 6 - refPts[i - 1][1];
        const dx = refPts[i][0] - refPts[i - 2][0], dy = refPts[i][1] - refPts[i - 2][1];
        const dl = Math.hypot(dx, dy) || 1;
        const vx = dx / dl, vy = dy / dl;
        const nx = -vy, ny = vx;
        const xdotv = px * vx + py * vy;
        const xdotn = px * nx + py * ny;
        const dfx = 2 * (xdotv / a2) * vx + 2 * (xdotn / b2) * nx;
        const dfy = 2 * (xdotv / a2) * vy + 2 * (xdotn / b2) * ny;
        G[i - 1][0] += o.lam4 * dfx / 6; G[i - 1][1] += o.lam4 * dfy / 6;
        G[i][0] += o.lam4 * 4 * dfx / 6; G[i][1] += o.lam4 * 4 * dfy / 6;
        G[i + 1][0] += o.lam4 * dfx / 6; G[i + 1][1] += o.lam4 * dfy / 6;
      }
      // 3. Soft Feasibility cost (L650-L714)
      for (let i = 0; i < n - 1; i++) {
        const vx = (Q[i + 1][0] - Q[i][0]) / dt, vy = (Q[i + 1][1] - Q[i][1]) / dt;
        const vArr = [vx, vy];
        for (let d = 0; d < 2; d++) {
          if (vArr[d] > maxVel) {
            const g = 2 * (vArr[d] - maxVel) / dt * tsInv2;
            G[i][d] += -o.lam3 * g; G[i + 1][d] += o.lam3 * g;
          } else if (vArr[d] < -maxVel) {
            const g = 2 * (vArr[d] + maxVel) / dt * tsInv2;
            G[i][d] += -o.lam3 * g; G[i + 1][d] += o.lam3 * g;
          }
        }
      }
      for (let i = 0; i < n - 2; i++) {
        const ax = (Q[i + 2][0] - 2 * Q[i + 1][0] + Q[i][0]) * tsInv2;
        const ay = (Q[i + 2][1] - 2 * Q[i + 1][1] + Q[i][1]) * tsInv2;
        const aArr = [ax, ay];
        for (let d = 0; d < 2; d++) {
          if (aArr[d] > maxAcc) {
            const g = 2 * (aArr[d] - maxAcc) * tsInv2;
            G[i][d] += o.lam3 * g; G[i + 1][d] += -o.lam3 * 2 * g; G[i + 2][d] += o.lam3 * g;
          } else if (aArr[d] < -maxAcc) {
            const g = 2 * (aArr[d] + maxAcc) * tsInv2;
            G[i][d] += o.lam3 * g; G[i + 1][d] += -o.lam3 * 2 * g; G[i + 2][d] += o.lam3 * g;
          }
        }
      }
      // First `order_` (3) and last `order_` (3) control points are fixed in refine_optimize (L1078-L1079)
      for (let i = ORDER; i < n - ORDER; i++) {
        Q[i][0] -= o.lr * G[i][0];
        Q[i][1] -= o.lr * G[i][1];
      }
      if (it % 3 === 2) hist.push(Q.map(q => q.slice()));
    }
    return { Q, hist };
  }

  function solve() {
    // 9 initial path waypoints -> K = 9 -> N = K + 2 = 11 control points (8 active segments)
    const ts0 = 0.50;
    const limitVel = 10.5, limitAcc = 13.5, tol = 0.0, velTol = 1.0, accTol = 1.0;
    const initPts = [];
    for (let k = 0; k <= 8; k++) {
      const x = 3.2 + 41.6 * (k / 8);
      const y = 12.2 + 1.0 * Math.sin(Math.PI * k / 8);
      initPts.push([x, y]);
    }
    const startEndDeriv = [[8.6, 0.2], [8.6, -0.2], [0.0, 0.0], [0.0, 0.0]];
    const Qinit = parameterizeToBspline(ts0, initPts, startEndDeriv);

    // Rebound trajectory: middle control points (indices 3..7) pushed safely above the obstacle
    const Qreb = Qinit.map(q => q.slice());
    Qreb[3] = [15.0, 16.2];
    Qreb[4] = [19.4, 23.0];
    Qreb[5] = [24.0, 24.5];
    Qreb[6] = [28.6, 23.0];
    Qreb[7] = [33.0, 16.2];

    const knots0 = makeUniformKnots(Qreb.length, ORDER, ts0);
    const fea0 = checkFeasibility(Qreb, knots0, ORDER, limitVel, limitAcc, tol);
    const prof0 = sampleProfile(Qreb, knots0, ORDER, 160);

    // Step 4.2: lengthenTime(ratio) -> non-uniform knots
    const lengthened = lengthenTime(knots0, fea0.ratio);
    const profNonUni = sampleProfile(Qreb, lengthened.knots, ORDER, 160);

    // Step 4.3: reparamBspline -> sample at uniform dt = duration / seg_num and solve A * Q = b
    const segNum = Qreb.length - ORDER; // 8 segments
    const duration0 = knots0[Qreb.length] - knots0[ORDER];
    const duration1 = lengthened.knots[Qreb.length] - lengthened.knots[ORDER];
    const dt1 = duration1 / segNum;
    const pointSet = [];
    for (let k = 0; k <= segNum; k++) {
      const t = Math.min(duration1, k * dt1);
      pointSet.push(evaluateDeBoorT(Qreb, lengthened.knots, ORDER, t));
    }
    const Qreparam = parameterizeToBspline(dt1, pointSet, startEndDeriv);
    const knots1 = makeUniformKnots(Qreparam.length, ORDER, dt1);
    const feaReparam = checkFeasibility(Qreparam, knots1, ORDER, limitVel, limitAcc, tol);
    const profReparam = sampleProfile(Qreparam, knots1, ORDER, 160);

    // Step 4.4: ref_pts_ sampled on Qreparam (planner_manager.cpp L434-L437) + BsplineOptimizeTrajRefine
    const refPts = [];
    for (let k = 0; k <= segNum; k++) {
      const t = Math.min(duration1, k * dt1);
      refPts.push(evaluateDeBoorT(Qreparam, knots1, ORDER, t));
    }
    const refined = optimizeRefine(Qreparam, dt1, refPts, limitVel * 0.72, limitAcc * 0.76, { lam1: 1.0, lam4: 11.0, lam3: 3.2, iters: 540, lr: 0.002 });
    const Qref = refined.Q;
    const feaRef = checkFeasibility(Qref, knots1, ORDER, limitVel, limitAcc, tol);
    const profRef = sampleProfile(Qref, knots1, ORDER, 160);

    // Precompute knot points P_hat_i = (Q_{i-1} + 4 Q_i + Q_{i+1}) / 6 and tangents v_i for fitness ellipses
    const fitnessItems = [];
    for (let i = ORDER - 1; i <= Qref.length - ORDER; i++) {
      const ref = refPts[i - 1];
      const dx = refPts[i][0] - refPts[i - 2][0], dy = refPts[i][1] - refPts[i - 2][1];
      const dl = Math.hypot(dx, dy) || 1;
      const v = [dx / dl, dy / dl], n = [-v[1], v[0]];
      const pHatRep = [(Qreparam[i - 1][0] + 4 * Qreparam[i][0] + Qreparam[i + 1][0]) / 6, (Qreparam[i - 1][1] + 4 * Qreparam[i][1] + Qreparam[i + 1][1]) / 6];
      const pHatRef = [(Qref[i - 1][0] + 4 * Qref[i][0] + Qref[i + 1][0]) / 6, (Qref[i - 1][1] + 4 * Qref[i][1] + Qref[i + 1][1]) / 6];
      fitnessItems.push({ i, ref, v, n, pHatRep, pHatRef });
    }

    return {
      W, H, RES, ORDER, raw, infl, occAt,
      ts0, dt1, duration0, duration1, segNum, limitVel, limitAcc,
      Qinit, Qreb, Qreparam, Qref, refPts, pointSet,
      knots0, lengthened, knots1,
      fea0, feaReparam, feaRef,
      prof0, profNonUni, profReparam, profRef,
      refined, fitnessItems,
      evaluateDeBoorT, sampleProfile, makeUniformKnots
    };
  }

  const api = { solve, sampleProfile, evaluateDeBoorT, makeUniformKnots };
  if (typeof module !== 'undefined') module.exports = api; else root.REFINECORE = api;
})(this);
