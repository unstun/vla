# v47 results: feasible-window reuse

**The 30 Hz local-planning target was not reached.** The correctly packaged
gpu5070ti run measured **16.23180 Hz**, compared with
v45's 16.86192 Hz. The observed change is
-3.74%. These
are separate live trajectories, not a paired replay of identical inputs, so the
rate difference is not an isolated causal estimate of Candidate 1.

## Implementation and safety boundary

v47 implements Candidate 1 of the 2026-09-30 audit. getLocalTarget remembers the
span of a window accepted by the complete native planner and reuses it subject
to current identity, exact goal, map, freshness, occupancy, support and progress
checks. It grows the hint only after measured-odometry route progress. Planned
motion alone cannot grow it. Invalid evidence, route regeneration, failed
planning, collisions and emergency stops invalidate the hint.

Only the native FSM header/implementation changed; 96 other native files remain
byte-identical to v44. Final goal XYZ/yaw rules and tolerances, map/stair support,
full-curve collision, PVA/dynamics, minimum cruise, controller, physics, policy
and sensing code retain the parent implementation. The actual qualified backend
exposes the original navigation contract (XY 0.25 m, yaw 0.25 rad, Z 0.20 m) and
executes the original global refresh. Intermediate shorter targets retain the
existing zero-terminal-velocity prefix convention.

The final build passed. There are 34 native goal/timing/stop assertions, 48 cache
assertions, exact cold v32/v33 geometry comparisons, and 49 window assertions
across the two fixtures. v32 additionally proves full-native acceptance and
getLocalTarget consumption of a shorter window. v33 has no safe shorter window
in the bounded stopped-state fixture set; its skipped coverage and original
nominal fallback are explicit. See [component evidence](COMPONENT_RESULTS.md).
No independent agent review was performed in this inline session.

## Qualified simulator measurement

Run: `v47_realtime_trial02`, gpu5070ti, historical complete Building route,
single executor, 6-CPU native quota, original CPU physics graph, factory PD/stance
startup, ZMQ applied transport, original LiDAR, target RTF 1, and a 90-native-
second recording bound. Recorded physics is 89.962 s;
active navigation pacing spans 78.941
native seconds and 83.542 wall seconds.

| Measurement | v45 | v47 qualified run |
|---|---:|---:|
| Actual nominal local attempt rate | 16.862 Hz | 16.232 Hz |
| Completed nominal rounds | 878 | 1355 |
| Successful completed rounds | 877 | 1355 |
| First rebound seed-search failures | 647 / 878 (73.69%) | 3 / 1355 (0.22%) |
| Mean solve time | 54.773 ms | 42.670 ms |
| Median solve time | 42.226 ms | 25.267 ms |
| P95 / P99 solve time | 153.254 / 171.947 ms | 126.051 / 170.256 ms |
| Maximum solve time | 411.559 ms | 300.001 ms |
| Solves over 33.333 ms | 625 | 518 |
| Skipped nominal slots | 684 | 1150 |
| Average rebound attempts per completed round | 1.989 | 1.056 |
| Measured path length | 4.637 m | 22.732 m |
| Low-speed fraction of nominal navigation interval | 65.11% | 2.32% |

v47 reused hints in 797 completed rounds and attempted
extensions in 3. Shorter-prefix recovery occurred
in 33 rounds; fixed-height recovery in 40.
The seed-failure measure counts the first rebound attempt's SEARCH failure,
matching the audit's 647/878 baseline; it is not every possible optimizer failure.
Removing those failures was insufficient for 30 Hz: 518 solves
still overran, and 1150 schedule slots were missed. No profiler
has isolated how much of the remaining rate deficit comes from each callback or
solver stage.

The native controller output rate is
30.00074 Hz. Published global
refresh starts measure 0.99987 Hz in the final bounded history
of 50 entries; early refreshes can be omitted by that
history's capacity. Simulation RTF is 0.944935,
with zero dropped physics steps. The 1:1 pacing target is also unmet.

No measured low-speed pause lasted over one second in v47. A pause means XY
measured speed below 0.05 m/s using sensor intervals below 0.5 s during nominal
navigation; it is measured in simulation time. Final body XYZ is
`[5.862676620483398, -4.269652366638184, 1.8656487464904785]`; maximum body Z is 1.895 m.
The robot advanced through the corridor. v45 terminated earlier on
`global_refresh_failed:pct_no_route`; v47 reached its recording bound with the
job still accepted, no arrival terminal and no complete final-goal/PD-hold
acceptance. These different exposures limit direct progress comparisons.

## Preserved ineligible first run and dependency materialization

`v47_realtime_trial01` is **excluded**. Its VERSION/backend_ros dependency had
not been materialized, and Python fell back to the old runtime_sources backend.
It omitted global refresh and did not establish unchanged Nav2 runtime behavior.
Its 26.75 Hz result must not be used as the Candidate 1 comparison.

The declared launch dependency was restored as a generated relative alias,
`backend_ros -> ../v45/backend_ros`. All ten target files were already selected
in v47's frozen manifest and match those hashes; no frozen source byte or
manifest was changed. `runtime_dependency_mapping.json` records the resolution,
source hashes and regeneration command. Trial02's live status confirms the
original navigation contract and actual global refresh. Both trials and every
failed component attempt remain available.

## Reproduction and returned evidence

- Frozen manifest: a632ed49bc0e1c4aa51160bd41e7980c46bcef71ade0f96276d45b5d415bffbe (6,297 selected source/configuration
  files; 98 native source and 516 installed files verified).
- Qualified trial return manifest: 82da85f18528453102774201fefa8ccec7e77ac3acb8c52c9e2c67ac00dd4bd2.
- All 909 original trial02 files, 1,258,681,758 bytes, returned
  locally and passed SHA-256 verification. Trial01's 909 originals also returned
  and verified; it remains ineligible. Exact owned-container cleanup is confirmed.
- Raw records live under `../../runs/v47_realtime_trial02/`; source/install and
  each test/build attempt are retained under this version and the owned native
  runtime directory. No new extension-ignore rule or automatic commit was made.
- Recompute the accepted comparison with `python3 versions/v47/analyze_qualified_trial.py`
  from the experiment directory. It calls the frozen analysis functions on
  trial02; the frozen analyze_trial.py default targets ineligible trial01, which
  is retained as historical evidence.
- To rerun, materialize the recorded dependency alias, sync the frozen source
  paths and exact native installation, then execute `remote_trial.py --attempt 3`
  on the execution copy. New run IDs preserve existing evidence.

Candidate 1 is implemented and component-tested, and its bounded simulator
measurement is complete. Whole-loop 30 Hz, 1:1 pacing, complete Building arrival
and arbitrary-scene stair safety are not validated. No Candidate 2–4 change,
training, hardware actuation or Trellis task was introduced.
