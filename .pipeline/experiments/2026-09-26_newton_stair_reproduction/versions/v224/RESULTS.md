# v224: shared environmental scoring candidate

Status: **component validation passed; Building route benefit and runtime acceptance did not pass**. The scorer participates in PCT search, both GPMP orders and native SCAN rebound/refinement. Its real-map A* improvement does not survive the inherited GPMP objective. Do not promote this candidate over the accepted v219 physical source/v220 display. No new physics, training or robot motion was run.

## Implementation and reuse

Parent: v223, retaining v221 attempt03 hard admission/repair. There are 31 owned overlay files in a composed 312-file source tree. Most inherited files change by a few lines; no recovery connector or new execution state machine exists. [REUSE.md](REUSE.md) records upstream pins and inherited libraries.

One immutable `reactive_stair::EnvironmentalField` supplies the same pose/yaw score to PCT and SCAN. It reuses native physical-floor drop evidence, ETH step scores, the existing native terrain-return classifier and PCL spatial queries. The original Building PCD is explicitly added as a **static soft planning prior**; it previously served the tracker. Simulator mesh and FCL results do not enter planning. Mixed or unassociated static points remain; below-floor material is omitted only for its associated support level in the soft view. Online occupancy and selected-surface rules are unchanged.

The retained envelope is radius 0.35 m, offset 0.18 m, up/down inflation 0.55/0.35 m. Target extra clearance is initially 0.15 m. With `p(m)=clamp((0.15-m)/0.15,0,1)`, cost is `p(edge)^2 + p(solid)^2 + 0.25*terrain^2`. It saturates and does not impose road-centering. This is not a feet/legs/contact model.

- PCT A*: adds the new term after legacy `<5` truncation, with graph weight 2.0 and transition quadrature at 0.025 m.
- PCT GPMP: WNOJ/WNOA endpoint and interpolated factors retain their legacy residual and add an independent `sqrt(2*shared_cost)` row. Thus the shared row remains active below the legacy `<=15` threshold. The inherited factor noise scales remain unchanged. Optional single-Jacobian calls are valid.
- SCAN: samples the actual cubic curve, obtains the native lookahead heading, and propagates position/heading derivatives to control points in both objectives. Candidate `lambda_environment=1.0`; default is zero. At zero squared hinge cost the gradient is exactly zero, avoiding eight redundant queries.
- Profiles: an optional SHA/FNV/terrain-bound `ENV224B` manifest enables both consumers together. Missing manifest preserves legacy mode. Native loading verifies envelope/clearance compatibility. The accepted runtime profile was not replaced.

## Component and independent validation

- Nine packages build; attempt09 has **164 colcon test records**, zero failures/errors/skips: 144 distinct cases and 20 wrapper records. The returned XML and execution receipt confirm the count.
- Actual PCT A* selects the opposite, lower-cost hard-grid corridor in a controlled fixture; its returned smoothed route retains that side preference.
- Both GPMP orders and interpolants produce nonzero shared residual/Jacobian with legacy map cost 10 and threshold 15, while the legacy residual remains zero.
- The actual SCAN objective and L-BFGS move free control points away from an edge: cost 0.300000 to 0.179309, centre y to 0.531398 m. Position and turning/heading gradients are checked numerically. This is an objective test, not a full live solver success.
- Heading, multiple floors, target saturation, below-floor material, truncated exports, exact consumer equality and profile tamper/wrong-terrain rejection are exercised. Existing hard admission, cache, freshness, tracking and terminal regressions pass.
- **30,060 PCT/native same-pose score pairs: zero difference.** An independent unpartitioned SciPy/numpy oracle checks 640 real-map samples across all four final route outputs. See [field_oracle_final.json](results/field_oracle_final.json).

An unchanged stock Wait fixture segfaulted once in attempt05. Its isolated retry passed in 1.42 s, and full attempts06–09 passed. The intermittent failure is retained and is not claimed fixed. A retry-created pytest cache was preserved outside src after the source inventory correctly rejected unexpected files.

## Real Building comparison

Final exact-source run: `probe_attempt08.log`, `field_probe_output06`. Both columns use the same PCT bundle, original archived reference XYZ endpoints and current implementation. “Off” means the new field is disabled; it is **not** a new v219 physics run. Metrics sample route segments at at most 0.025 m with segment yaw. These direct adapter outputs have not yet passed final reference admission.

| Stage and metric | Shared score off | Shared score on |
|---|---:|---:|
| A* route time | 0.01343 s | 7.85875 s |
| A* route integrated shared cost | 1.218110 | 0.017219 |
| A* minimum extra edge margin | 0.022721 m | 0.125601 m |
| A* minimum static solid margin | -0.020444 m | 0.127016 m |
| A* route length | 79.0027 m | 79.2443 m |
| A* native rejected samples / queried | 0 / 3,560 | 1 / 3,562 |
| Search + GPMP time | 0.03164 s | 8.02333 s |
| GPMP route integrated shared cost | 0.271146 | 0.725006 |
| GPMP minimum extra edge margin | 0.105109 m | 0.093517 m |
| GPMP minimum static solid margin | 0.075647 m | 0.036790 m |
| GPMP route length | 75.2701 m | 75.8785 m |
| GPMP native rejected samples / queried | 21 / 3,319 | 35 / 3,341 |

A* cost falls 98.6%, with substantially more edge/solid clearance. The smoothed result is worse on these metrics. A nonzero GPMP row alone does not establish effective final-route margin preservation. Initial weights are not accepted for runtime use, and the new score is much more expensive than the legacy search.

Real-map native SCAN environmental cost-plus-gradient timing, 14 control points, 0.2 s knot interval, three evaluations per window:

| Window | Cost | Gradient norm | Mean evaluation |
|---|---:|---:|---:|
| Reference quarter 1 | 0 | 0 | 3.00 ms |
| Reference quarter 2 | 0 | 0 | 3.42 ms |
| Reference quarter 3 | 0 | 0 | 2.73 ms |
| Around highest scored actual route pose | 0.899515 | 6.022527 | 35.24 ms |

These measure one environmental objective evaluation, not a full optimization or control cycle. Active-margin cost remains material. Report it separately from the cheap zero-cost case.

## Final reference admission and repair

`admission_attempt03.log` invokes the actual installed PCT plugin, its RoutePolicy, three-round repair loop and service client. The provider delegates each STATIC_ONLY pose to the native GridMap. It uses archived reference XYZ endpoints with **explicit zero start/goal yaw**, not recorded robot states, live timing or a replay of the original mission orientation. Native final sampling also includes translation/rotation and the connector, hence different denominators from the table above.

- Score off: rejected pose counts 23, 18, 1; truthful no-route after 0.235 s.
- Score on: rejected pose counts 35, 14, 1; truthful no-route after 24.294 s.
- Neither candidate is returned as an admitted route. Both retain one `WrongHeight` (10) witness in the final graph fallback. Off: `(4.404685211, 0.763188744, 4.88125)`, yaw -2.35619449. On: `(6.404685211, 5.363188744, 3.410546875)`, yaw -1.96349541.

These full-Building static benchmark queries are separate from the v217 42–62 s recorded window. They do not contradict v223's zero remaining WrongHeight count in that sampled window. No rejection was waived, no retry budget was increased, and no recovery exemption was introduced.

## Failed attempts and diagnosis

The original ENV224 attempt took 92.484 s and worsened route score/edge margin. The first ENV224B correction took 71.970 s. Witness inspection identified static PCD material below its physical floor as a saturation source. The final exporter uses physical volume depth, not step-height capability, for below-floor annotation. Keep all three exports and failed outputs.

Exact computational reductions then partitioned static points by associated support floor, used unsorted PCL radius queries, skipped provably non-improving A* neighbors, pruned distant point groups by their 3-D bounding boxes and skipped zero gradients. The final geometry oracle checks the partitioned/pruned scorer against an unpartitioned implementation. These changes reduced total scored planning to 8.023 s, still far above the legacy 0.032 s result.

The remaining work is GPMP score scaling/margin retention, scoring-query cost, and an admitted same-input route comparison. R8's consumer wiring/component checks are implemented; useful Building route behavior is **not validated**. Preserve this candidate and its failed evidence rather than treating the A* improvement as acceptance. v222 blocked-region feedback remains separate.

## Provenance and regeneration

Local source of truth: this version directory, inheriting the exact v223 inventory. [source_identity.json](source_identity.json), [baseline_sources.json](baseline_sources.json), [results/sync_gate.json](results/sync_gate.json), and [results/source_inventory.json](results/source_inventory.json) bind local production bytes to the composed/tested source. Heavy exports remain on gpu5070ti:

`/data/sun/vla_mppi_20261009/environment_score_v224/`

Final `fixtures/building/environment03.env`: SHA-256 `72142fda10deec9cfabab95f5d27d1159fa8ec3821f1a808f4a6a1f8186edaac`, FNV `4316416882194453309`. Declared PCD SHA-256: `8721efeb74415336d47c97d861d6e30ad213669b120d5b37c62461100c1f2eae`. [execution_receipt.json](results/execution_receipt.json) records retained remote locations, sizes and hashes; compact logs, XML and final scored CSVs are returned locally.

Regeneration uses `prepare_workspace.py`, `build.sh attemptNN`, `tools/export.sh`, `tools/prepare_probe.py`, the built `field_probe`/`admission_probe`, and `tools/verify_field.py`. The build/export/probe scripts target an isolated workspace mounted at `/work` and the version source mounted read-only at `/source`, with original inputs at `/task`. Preserve existing output names; use a fresh execution copy for a new reproduction. Set `REPLAY_INPUT`, `PCT_INPUT`, `BENCH_POSES`, `ROUTE_ENDPOINTS`, `ENVIRONMENT_INPUT`, `ENVIRONMENT_FNV`, `PROBE_OUTPUT` as shown in the retained candidate/probe scripts. The independent oracle runs in the pinned host analysis environment; it is not a planner dependency. No large export or original failed artifact was deleted.
