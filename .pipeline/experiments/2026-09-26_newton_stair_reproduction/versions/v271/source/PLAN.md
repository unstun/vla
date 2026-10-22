# v271 native source-surface integration

Compose frozen native v261 with the independently qualified v270 source geometry.
Keep the legacy voxel loader and its full equality controls. Add a hash-bound
source descriptor at the existing StaticSolidField boundary so PCT and SCAN
share one hard obstacle model. Requested endpoints, support source, ENV225,
RL, 0.35 m cylinders and 0.1 s scans remain fixed.

Owned changes: private source geometry kernel, StaticSolidField dispatch,
separate source fixture descriptor/configuration, installed-API conformance
probe, and evidence tooling. No endpoint exception, runtime recovery protocol,
support waiver or legacy map rewrite. Source margin is a radial distance
conditioned on the finite vertical interval; do not inherit negative voxel-SDF
Lipschitz certificates. Outer-circle freedom and inner-core collision retain
strict geometric containment proofs.

Validate independent v270 first; then build all seven native consumers in an
isolated prefix. Check installed source values against the independent 512-query
ledger, 14 counterexamples, tiny-face interior distances, finite gradients and
actual witnesses, invalid identities, and rotational proof implications.
Retain 70,928 legacy full-value, 5,000 edge and native regression controls.
Run development A04/G05 and unchanged H00/measured-A02 before freezing.
Freeze source/install/fixtures/evaluators before original52 and fixed50+3.
Score actual native 0.8 s trajectory-yaw protocol, full chain, first GPMP and
CPU2 wall time. Preserve all prior scored results. Physical routes remain
conditional on the declared >=90% coverage/smoothing and recovered timing gate.

Development01: source installed API512values,14counterexamples and16384rotation implications passed; PCT74tests passed. A04firstGPMP passes but10.2917s global is too slow. Legacy70928/5000binary/edge/cache comparisons match, but12scalar/gradient values drift up to3.33e-16; keep this failed receipt. Isolate the source kernel into its own compilation unit and test exact old arithmetic again. Source memoization uses only identical real height and positive radial-distance displacement proofs, with ordinary exact fallback and per-request owner reset. No query coordinate rounding or cross-height proof. Add40000direct-versus-cached source comparisons plus owner changes before rerunning controls.

Development03passesallnative/equalitytests,including40000sourcecachechecks. A04/G05/D07firstpassin5.290/5.452/5.672s;timingstillfails. ActualA04callbackprofile:747959circlequeries,498000cachehits;poseedge3.272s,posevalidity0.545s,rotation0.272s,ENVcost0.187s,GPMP0.763s. The dominant work is exact edge collision, not ENV. Source cache identity now uses exact body-height bits (not a coarse height bucket) and retains newly computed anchors when four slots are full. Values and hard predicates are unchanged; no cross-height reuse is introduced. Preserveattempt03sourceandtimings.

Development05retainszerolegacy/source differences and lowersA04to3.6149s. The next candidate short-circuits Boolean source checks once one fully terrain-clipped face proves collision. Full assessments keep exact margin/gradient/witness. The privatecircleMargin returns exact positive clearance or a nonpositive collision witness; onlypositiveboundsare reused awayfromananchor. Compare40000early/cachequeriesagainstfullassessment,plus512independentvaluesandallothergates.

Development06allgatespass,A04/G05/D07=3.3687/3.4109/3.6952s. NextmemoimprovementreusesadjacentXYbucketanchorsatidenticalrealheight. Positiveclearanceusestriangleinequality;negativecollisionwitnessesremaininsideafterXYmovementsmallerthantheirradialintrusion. Thisnewproofdoesnotassume3DSDForcross-heightcontinuity. Unknownboundfallsbackexact. Add5000sweptsourceedgesandanalyticwalltangenciesalongside40000full-assessmentcomparisons.
