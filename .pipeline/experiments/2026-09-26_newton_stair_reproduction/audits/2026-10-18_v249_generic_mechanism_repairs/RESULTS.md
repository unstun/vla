# Generic mechanism repairs — v249 / v250 / v251

Stage: experiment + analysis. User-authorized offline repair of GPMP, G07 and
A02. Local VLA source is authoritative; gpu 5070 ti is an execution copy.
No new physics, training, endpoint rewrite or commit occurred. Frozen parents
and unrelated worktree changes are preserved. Selected baseline is v232 / v233.

## Outcome

The unchanged Building 12 x 5 matrix is 55/60 again, now with **55 first-GPMP passes
instead of 0**. All 55 admitted calls use the smooth first attempt; none falls
back to A* graph output. B09 remains 0/5 `pct_no_route`. H00 passes first GPMP,
static review and cold local publication, with exact requested goal checked
to 4.16e-8 m max-coordinate error. A measured-start connection is reviewed;
an optimized first point is not asserted identical to the measured start.

The saved G07 local failure is reproduced with original query/body/cloud times,
then repaired. Original A02 mesh, physical-floor grid and PCD show its old
SupportGap was a mask false positive. Source floors, RL policy SHA,
0.35 m hard radius, 0.18 m offset, height bands, 0.1 s scan period/deadline and requested
poses are unchanged. No Building coordinates, route labels, snapping,
connectivity-component exceptions or new recovery state machine enter code.

## GPMP: where rejection occurred and what changed

Actual installed v247 C++ first-attempt observation:

| Result after actual optimization | Cases |
|---|---:|
| `pct_support_height_missing_surface` in projection |10 |
| `pct_support_height_invalid_layer` in projection (A03) |1 |
| `pct_no_route` before optimization (B09) |1 |

The optimizer completed the 11 routable attempts; `pct_optimizer_rejected` was
the outer catch label, not evidence of an internal solver failure. Two coupled
representation errors explain the height-stage failure:

1. GPMP's truncated cell lookup disagreed with canonical support projection.
  Some intermediate PCT slice aliases also had `planning_ground=-100` while the
  original native low floor existed at the same continuous XY. A03 and R12 / B08
  are explicit witnesses; an earlier missing-ground hypothesis was rejected.
2. Trial evaluation could mutate height hints toward another storey. The old
  height smoother could then spread that association into unsupported Z.

Frozen v249 makes the native raw/scored support snapshot authoritative, uses
deterministic immutable reference heights, associates actual XY within the
existing legal band and recomputes output height without the old unconstrained
smoother in physical mode. 11/11 height projections pass; final support remains
mandatory. This alone still leaves genuine or conservative gap-domain failures.

Frozen v250 corrects the duplicated target-cell inflation described below.
Frozen v251 then gives GPMP the **same oriented gap feasibility** as the final
check, with position/yaw/velocity-chain derivatives in WNOJ/WNOA node and
interpolated factors. Legal support has zero feasibility residual. The existing
ENV225 edge soft channel now sees the same gap sources in PCT search, GPMP and
SCAN; the existing 0.15 m target and weights are unchanged. That removes the
missing-evidence inconsistency without creating another soft channel or hard
clearance band. All 11 routable final smooth references now have 0 static refusals.

Development traces include intermediate failing repairs and are retained as
diagnosis, not separate acceptance runs. See
`results/gpmp/diagnosis01/*/result.txt` and
`results/gpmp/shared_gap01/*/result.txt`. Full dense query arrays remain remote,
with hashes in `results/return_receipt.json`; representative rows and raw GPMP
outputs are local.

The actual returned paths are compared at a common 0.10 m XY-arclength scale,
including the original requested-start connection. In the coordinate-free
height-transition neighborhood, maximum heading change drops from 40.07 to
5.29 degrees for G07 and from 42.79 to 4.32 degrees for R11. Their recorded
rep 01 global planning times drop from 1.513 to 0.895 s and from 1.755 to
0.953 s. The 3-D piecewise-linear lengths increase slightly; these geometric
results do not establish fewer physical stops. See the
[route comparison](research/route_comparison/README.md) and its inspected plot.

## G07 : first refused edge and original-time replay

The original physical observation used rounded location(7.69, 6.49, 3.36).
The selected exact recorded query is 102.110511780 s:

- Body:(7.710203647613525, 6.484551906585693, 3.355505943298340),
  body stamp 102.110511780 s; measured yaw 2.993131660689271 rad.
- Latest published cloud 101.975585938 s;910 actual published scans and 11920077
  points are reconstructed in order. Original NPZ identities are verified.
- Route generation 14 and original route/curve history are preserved. The
  expired-curve branch uses the measured start; reconstructed reference duration
  is 44.852313539863019 s. Baseline and repaired map digest are identical:
  `9ab177f8bb390a816810917626dd3e6e12e3cca97d9d7a8c8f663d914039c748`.

The first refused edge in the baseline reconstruction is:

| Field | Value |
|---|---|
| From |(7.7102036476, 6.4845519066, 3.3555059433) |
| To |(7.6602036476, 6.4345519066, 3.3555059433) |
| Planning yaw |-2.356194490192345 rad |
| First refused sample |0 of 3 intervals, exactly the start position |
| Typed verdict |`SupportGap(11)` |

The old four seed searches each expanded only the start: all 8 neighbor edges
and the terminal edge failed at sample 0. Actual measured yaw being supported
therefore did not imply that these different candidate headings were supported.
The baseline reconstruction failed at the seed in 2.30 ms, before optimization.

The old mask enlarged original uncertain source squares into target squares,
then rejected every continuous center inside those target squares. v250 keeps
the original sources but uses bins only for candidate selection and tests the
actual center-to-source-square distance against the same 0.35 m. It frees G07
headings 0 or pi, and the actual connector becomes possible. Perpendicular headings
remain refused: original mesh distance is 0.314982632 m, below 0.35 m. Partial-source
square conservatism remains; the repair does not free every direction.

| Same saved-input treatment | Planned | Final full curve | Component time |
|---|---:|---|---:|
| v247 baseline |No |Not generated |2.30 ms |
| isolated v250 gap repair |Yes |Existing planner admission |61.3 ms |
| composed frozen v251 |Yes |Clear(status 0) |548.8 ms |

The v251 near-goal replay is not the cold-start matrix timing; preserve the
longer 548.8 ms measurement. The stale negative remains blocked: inputs_ready=0,
verdict `StaleInput(4)`. Final gate is in
`results/g07/g07_final01/final_gate.json`. Its legacy field `first_collision_s`
is the checker traversal cursor even when status is Clear; it does not denote
a collision when status=0. `searches.csv` has a legacy variable-width trailing
typed-count map; parse its first 7 columns then join the remaining tokens.
The fixed-width `rejected_edges.csv` is the primary first-edge witness.

### Later global review: what is and is not recoverable

The two global refusals were logged later, near 105.57 s. The original global
service request and returned rejected coordinates were not captured. An exact
historical pair cannot be claimed from that count alone.

Using the original canonical goal/quaternion and 164 recorded bodies over
103.809577942–105.698539734 s(18 pre104 controls plus 146 late-window bodies), actual
old PCT graph+RoutePolicy+StaticSupport reconstruction returns exactly 2 SupportGap
poses for every candidate. A representative original-body candidate gives:

| Sample | XYZ | Planning yaw | Old → repaired verdict |
|---|---|---:|---|
|6 |(7.617563302176340, 6.500654642922538, 3.362534976686750) |3.057266686954164 |11→0 |
|7 |(7.596603938511440, 6.504832676478795, 3.364211947577340) |3.085375342499374 |11→0 |

The same 328 reconstructed rejected poses are then checked directly by installed
v251 native C++:328/328 Free. This demonstrates the same quantization mechanism
across the recorded window; it does not identify the unlogged original request.
Exact candidate identities and both old/new verdicts are retained under
`results/late_global/`. Ordered published-prefix mapping has revision 0 rather
than original asynchronous revision 1102;910 published scans differ from the
historical mapper count 904. The 6 published scans are retained rather than
deleted to force an artificial count match. No exact asynchronous-memory or
new physical execution claim is made.

## A02 : geometry establishes a false positive

Exact post-PD body:
(-6.1107869148254395, 6.87894868850708, 0.3989008665084839),
yaw-0.7858018918788338 rad. Independent transformed-original-USD triangles match
all 16448 cached triangles elementwise. Exact continuous mesh union, original
physical-floor records and the original PCD agree:

| Cylinder | Distance to uncovered original mesh | Spare above 0.35 m |
|---|---:|---:|
| Front |0.635748117 m |0.285748117 m |
| Rear |0.378376919 m |**0.028376919 m** |

Both actual discs are covered. The old rear target cell hit 6 uncertain source
squares; none intersects the actual disc. All 72 missing generator samples in
those sources lie outside it. The nearest entire source square is 0.357299955 m
away, still beyond 0.35 m. Original PCD has 213 front/221 rear horizontal-floor
points atz≈0.05803 m, consistent with the native floor grid.

Thus 9.3 cmPDdrift exposed **target-cell quantization overreach**, not a real
support hole at the measured pose. v250 removes only this extra quantization.
Native C++ v251 now returnsFree for both actual post-PD and goal-submission poses.
The original source-square uncertainty stays conservative. No start movement,
snapping or radius relaxation is involved. Full geometric method, witnesses,
raw-input hashes and plot are in[the A02 report](research/A02/REPORT.md).

## Qualification and retained limitations

- Frozen 12 x 5 calls:55 first-GPMP/global/static/cold-local passes; B09 fails 5.
  All successful groups are 5/5. See[per-case table](results/evaluation/matrix_table.csv).
- H00 first GPMP and cold local pass. Successful matrix global time 0.563–1.071 s,
  median 0.748 s; first local 9.30–34.24 ms, median 19.54 ms. Fixed ROS capture epoch,
  steady component timers and 2 CPUquota; no real-time or repeated reliability claim.
- Six PCT/physical-factor CTest targets:43 cases pass, including node/interpolant
  finite differences, H 1-only/H 2-only, zero speed, exact contact and nonfinite
  states. Twelve native targets:97 cases pass. Source/build receipts alone are
  not qualification;[the independent receipt](../../versions/v251/results/acceptance_receipt.json)
  binds the completed gates and actual input/evaluator inventories.
- 10855 support queries:0 typed mismatches, 0 exported-admission mismatches;
  supported 9910→9973 after duplicate quantization removal. 110484 snapshot surfaces,
  sameFNV 1404261889151999461.40000 actual-source hard-domain comparisons against
  v250 show 0 mismatches;1442401 synthetic geometry cases also pass.
- B08 still has negative independent raw-solid reference margin(-0.1903 m).
  G05 minimum extra edge margin is 0.0200 m. ENVmetrics cap at +0.15 m; unknown live
  coverage remains reported. The 55 component passes are not 55 full-body route
  clearance proofs, future footstep proofs or physical completions.
- No new videos are produced because no new physical trial was run. Existing
  v248 R11 physical evidence remains separate; task stays open for review and a
  later authorized physical qualification. No commit or baseline promotion.

## Provenance and regeneration

Execution root:`/data/sun/vla_mppi_20261009` on gpu 5070 ti. Compositions are
`generic_mechanisms_v249/native`→`generic_mechanisms_v250/native`→
`generic_mechanisms_v251/native`. Pinned container digest and full environment
prefixes are in each version's build/probe scripts. All 7 native consumers were
rebuilt; separate evaluator binaries were rebuilt and SHA-bound as well.
RLpolicy SHA remains 7030 ba 4704 ab 1761e777 ba 2e268 bb 6070 a 1 b 245 b 9891 bb 6 dc 3 c 255414996581 b.

Use the version prepare/build/test scripts only on a fresh owned execution copy;
never overwrite frozen sources. `v251/gap_contract.py`, `probe.py build`,
`regressions.py`, support probe and frozen H00 /matrix/acceptance scripts reproduce
the offline gates. Audit `g07_replay.py` preserves recorded query time;
`late_global.py` reconstructs candidates and `pose_recheck.py` rechecks identical
refused poses. `collect.py` returns compact evidence, retaining full dense arrays,
PCD/mesh/cloud recordings, installed libraries and CMake caches remotely.

`results/return_receipt.json` records 440 copied files/10448443 bytes and 96 remote
dense-query hashes; generated witness subsets and the receipt add a small amount.
No local CMakeFiles, objects, libraries, raw point clouds or new raw physics data.

Local return verification also passes: all 440 copied result hashes, both
research artifact inventories, three immutable source snapshots and parent
manifest links, Python AST/JSON parsing, and retention checks. See
[local quality receipt](results/local_quality.json). The independent final
read-only review found no material discrepancy; the baseline replay timing is
explicitly labelled as reconstructed rather than original physical latency.
