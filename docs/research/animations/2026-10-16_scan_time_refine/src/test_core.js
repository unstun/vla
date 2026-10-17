const R = require('./refine_core.js').solve();
console.log('--- Step 4.1: Initial Rebound Trajectory ---');
console.log('ts0 =', R.ts0, 'duration0 =', R.duration0.toFixed(3));
console.log('fea0:', {
  fea: R.fea0.fea,
  ratio: R.fea0.ratio.toFixed(3),
  velRatio: R.fea0.velRatio.toFixed(3),
  accRatio: R.fea0.accRatio.toFixed(3),
  maxVel: R.fea0.maxVel.toFixed(2),
  maxAcc: R.fea0.maxAcc.toFixed(2),
  limitVel: R.limitVel,
  limitAcc: R.limitAcc
});
console.log('velCtrl overAxis:', R.fea0.velCtrl.filter(v => v.overAxis).map(v => `V_${v.i}: ${v.maxAxis.toFixed(2)}`));
console.log('accCtrl overAxis:', R.fea0.accCtrl.filter(a => a.overAxis).map(a => `A_${a.i}: ${a.maxAxis.toFixed(2)}`));

console.log('\n--- Step 4.2: lengthenTime(ratio) ---');
console.log('num1 =', R.lengthened.num1, 'num2 =', R.lengthened.num2, 'deltaT =', R.lengthened.deltaT.toFixed(3), 'tInc =', R.lengthened.tInc.toFixed(3));
console.log('knots0:', R.knots0.map(u => u.toFixed(2)).join(', '));
console.log('knotsL:', R.lengthened.knots.map(u => u.toFixed(2)).join(', '));

console.log('\n--- Step 4.3: reparamBspline ---');
console.log('duration1 =', R.duration1.toFixed(3), 'dt1 =', R.dt1.toFixed(3));
console.log('feaReparam:', {
  fea: R.feaReparam.fea,
  maxVel: Math.max(...R.feaReparam.velCtrl.map(v => v.maxAxis)).toFixed(2),
  maxAcc: Math.max(...R.feaReparam.accCtrl.map(a => a.maxAxis)).toFixed(2)
});

console.log('\n--- Step 4.4: BsplineOptimizeTrajRefine ---');
console.log('feaRef:', {
  fea: R.feaRef.fea,
  maxVel: Math.max(...R.feaRef.velCtrl.map(v => v.maxAxis)).toFixed(2),
  maxAcc: Math.max(...R.feaRef.accCtrl.map(a => a.maxAxis)).toFixed(2)
});
const maxV0 = Math.max(...R.prof0.pts.map(p => p.vmaxAxis));
const maxA0 = Math.max(...R.prof0.pts.map(p => p.amaxAxis));
const maxVL = Math.max(...R.profNonUni.pts.map(p => p.vmaxAxis));
const maxAL = Math.max(...R.profNonUni.pts.map(p => p.amaxAxis));
const maxVR = Math.max(...R.profReparam.pts.map(p => p.vmaxAxis));
const maxAR = Math.max(...R.profReparam.pts.map(p => p.amaxAxis));
const maxVF = Math.max(...R.profRef.pts.map(p => p.vmaxAxis));
const maxAF = Math.max(...R.profRef.pts.map(p => p.amaxAxis));
console.log('Continuous profile peaks max(|v_d|), max(|a_d|):');
console.log('  Rebound (ts0):   v_d =', maxV0.toFixed(2), 'a_d =', maxA0.toFixed(2));
console.log('  Lengthened (uL): v_d =', maxVL.toFixed(2), 'a_d =', maxAL.toFixed(2));
console.log('  Reparam (dt1):   v_d =', maxVR.toFixed(2), 'a_d =', maxAR.toFixed(2));
console.log('  Refined (dt1):   v_d =', maxVF.toFixed(2), 'a_d =', maxAF.toFixed(2));
const hits0 = R.prof0.pts.filter(p => R.occAt(p.pos[0], p.pos[1])).length;
const hitsR = R.profReparam.pts.filter(p => R.occAt(p.pos[0], p.pos[1])).length;
const hitsF = R.profRef.pts.filter(p => R.occAt(p.pos[0], p.pos[1])).length;
console.log('Collision hits (Rebound, Reparam, Refined):', hits0, hitsR, hitsF);

