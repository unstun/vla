# v273 fixed source-model benchmark

Use one frozen native v272 installation and evaluator for both preserved
cohorts: original v257 52 requests and fixed v262 50 positive + 3 illegal
requests. Reuse the byte-identical scenarios and zero-step sensor fixtures.
One scored native call per case; no replacement, endpoint movement or relabeling.
Keep original source, v261/v262 scores and every failed development attempt.

Verify source/install/evaluator/fixture/policy identities before freeze and
before scoring. Run native requests sequentially with the existing CPU2/6GiB
limit. Complete native timing collection before parallel independent raw-PCD
audits, so audit load cannot contaminate measured planning latency. Audit all
returned global and local samples using the actual native 0.8s heading rule.
Keep source radial, raw unvoxelized point, old voxel and ENV margins distinct.

Report global admission, first GPMP (both all-positive and admitted denominators),
full static/cold-SCAN chain, typed refusals and elapsed time per case. Preserve
initialization separately. The clean gate requires >=45/50 full positives,
>=90% first GPMP among admitted positives, all3illegal refusals, no admitted
negative independent raw point margin, and admitted global median<=1.5s.
Retain the predeclared ten-route selection coverage (A04/G05/CU06/D07/S04,
descent, intermediate start/goal, same-floor and boundary). Do not launch
physics if the coverage/smoothing/margin/timing/selection gate fails.

All raw data and build caches stay on gpu5070ti. Return compact reports,
per-case evidence, manifests and later actual full videos locally. No source
or model change during this scored cohort; analysis or later repairs receive
separate versions and preserve this ledger.
