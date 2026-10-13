# v52 component comparison; physical validation pending

Stage: experiment + analysis, 2026-10-02. Parent: frozen v50, directly descended
from v48. v49 remains a frozen failed attempt and is not an ancestor.

**The scoped lookup cache reduced the worst reproduced cold replay maximum
from 483.747 to 434.117 ms (10.26%), preserving identical outcomes and control
points/knots. It did not eliminate long recovery rounds or validate 30 Hz.**
The live Building trial stopped at resource preflight and executed zero physics.
An unrelated IsaacLab evaluation occupied about 15,750 MiB of gpu5070ti memory.

## Change and preserved contracts

Only two native files change: `grid_map.h` and
`scan_reactive_grid_methods.inc` in `runtime/scan74_terrain_lookup_v52`.
The other 98 native source files retain parent bytes. The new cache reuses exact
raw/scored terrain-cell lookups inside the existing cache scope, with a 4096-cell
limit and original mutation invalidation. Layer selection, occupancy/support,
freshness and full trajectory checks still execute. Final goal, yaw, PVA,
dynamics, trajectory ownership/continuity, recovery attempts and the stop
protocol retain the parent code. There is no new solver deadline or cancellation.
See [implementation](IMPLEMENTATION.md), [native patch](changes.patch),
[continuity identities](continuity_identity.json) and
[runtime identities](runtime_preparation.json).

## Paired replay on gpu5070ti

The same compiled native binary alternates the original lookup path and v52
lookup reuse three times per case. Both retain v50's goal-region precheck and
v48's warm-start logic. Each pair restores the same manager/FSM state, uses the
same observed inputs and fixed clock, and requires identical result and accepted
geometry. No robot physics runs in this comparison.

| Original simulation stamp | Original lookup max / median | v52 max / median | Maximum reduction | Outcome in both modes |
|---|---:|---:|---:|---|
| 33.453 s | 100.201 / 98.941 ms | 90.486 / 90.277 ms | 9.69% | Success |
| 44.952 s | 483.747 / 482.371 ms | 434.117 / 433.691 ms | 10.26% | Failure |
| 74.041 s | 234.296 / 233.573 ms | 221.197 / 214.984 ms | 5.59% | Failure |

All 18 rounds retain paired outcome and control-point/knot equality. The failure
cases retain the parent's rejection; faster failure is not a new valid plan.
See [original returned pairs](profiles/attempt01/tail_pairs.jsonl),
[summary](paired_summary.json), [PNG plot](analysis/paired_latency.png) and
[PDF plot](analysis/paired_latency.pdf).

**Load caveat:** the competing IsaacLab process began at
2026-10-02 08:29:22.460 UTC, before the paired profile at 08:32:21.844 UTC.
These are alternating comparisons under shared-host load. Thread-CPU stage
measurements and paired restoration improve diagnosis, but an uncontended rerun
is required before adopting the magnitude as a stable production speedup.
[Resource evidence](trials/attempt01/resource_block.json) records process start
and the profile timestamps. The earlier cold-tail audit remains the separate
unchanged-native diagnosis.

The original v50 live maximum was 1,829.626 ms. The fixed-input replay removes
live input arrival/DDS batching and unpublished state, reproducing only part of
that chain. **Do not report 1,829.626 to 434.117 ms as a measured improvement.**
Every optimized reproduced cold case still exceeds the 33.3 ms planning period.

## Builds and safety gates

- Both remote native builds passed. The final build preserves all 100 declared
  source hashes. The first unfrozen candidate is retained under
  `candidate_attempts/build01`; final native build wall time was 45.889 s.
- 35 native checks and 64 cache checks passed, including 16 new terrain lookup
  assertions for missing/signed cells, scope nesting, capacity, disabled parity,
  empty drains and actual terrain/surface/cloud mutation invalidation.
- Both recorded native continuations succeeded and match the frozen parent's
  geometry exactly. Both warm fixtures passed 47 checks, including fallback,
  PVA, dynamics, ownership, obstacle/support and expired-curve cases.
- Goal-region fixture/property checks and all 17 backend tests passed, retaining
  the original stop ownership, hold and measured-stillness protocol.
- Local current source and all 6,761 snapshot locations passed SHA-256 checks.
  The execution copy passed the original 6,761-file source gate and the
  518-file native installation gate. Its 150 v52 snapshot files were verified;
  inherited snapshot records remain in the canonical local parent tree.

Direct evidence: [component result](tests/attempt01/result.json),
[qualification](component_qualification.json),
[final build](build_evidence_retry02/build_result.json),
[return verification](component_return_verification.json),
[local freeze verification](final_source_verification.json), and
[remote execution gate](execution_copy_verification.json).
These establish component validation, not physical continuity or route acceptance.
The prepared analyzer also reproduces the original v50 trial's maximum, measured
path, full-window rates, source hashes, pauses and emergency-transition count
exactly: [six-check verification](analyzer_verification.json). This check uses
existing expanded v50 data and executes no new physics.

## Physical trial and storage boundary

Attempt 01 failed the existing idle-GPU preflight before creating a run or
starting the planner/physics. [Preflight](trials/attempt01/preflight.json) records
the active evaluation. There is no v52 physical trajectory, live maximum,
successful-planning frequency, time-series plot or review video to report.
Navigation reference remains v48. v52 is frozen and component-qualified, with
tail elimination, physical continuity and 30 Hz acceptance still open.

Builds, probe binaries and the 112.5 MB cold replay input remain under
`/home/sun/vla_exec/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction`
on gpu5070ti. Only explicit compact evidence allowlists returned locally.
The v52 snapshot references the pinned v50 snapshot for inherited bytes and
stores its own source/configuration delta; older source/build trees were not
duplicated locally. See [artifact locator](remote_artifacts.json).

## Resume from unchanged frozen source

First require an idle GPU, empty owned ports and no competing Docker container.
Do not stop another evaluation as part of this task. Preserve failed preflight
attempt 01. Re-run the paired timing profile with `--attempt 2` on the idle host,
then execute the already authorized bounded Building trial:

```sh
export PATH=/home/sun/vla_exec/bin:$PATH
python3 versions/v52/remote_profile.py --attempt 2
python3 versions/v52/remote_trial.py --attempt 2
/home/sun/vla_exec/envs/newton_worker/bin/python versions/v52/analyze_trial.py \
  --run v52_realtime_trial02
```

Commands run from the remote experiment root. Full raw data analysis and managed
lossless archive validation stay there; return only compact analysis, provenance,
plots and any needed review MP4. Report successful completions over the full
navigation wall window, measured path/pauses and the complete-round maximum.
Future native changes require v53; do not modify frozen v52 to repair cold search.
