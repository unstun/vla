# v196 component and live graph qualification

Stage: experiment + analysis. Version parent **v195**, navigation source parent
**v194**, native version **v196**, Mac ARM64 binary underlay **v176**.

## Changes

1. Restored Foxy PipelineSequence / RateController at 1 Hz. Initial acquisition
   requires a valid connected PCT route; same-mission refreshes retain a deep
   copy on terminal approach or the three declared transient route failures.
   Invalid inputs, nonfinite output and owner/cancel changes still reject.
   Cache use records refresh_status and retained_count.
2. Identical active-route geometry updates the controller reference without
   another /pct_path publication. Changed geometry and waiting recovery publish
   immediately. Existing spline-wait and goal-braking behavior is retained.
3. Reference replanning makes one initializer call per round, uses measured
   odometry for absent/expired splines or three failures, wakes REPLAN_TRAJ on
   a newly admitted route, and permits later checked steering recovery on the
   same route. Steering is also reachable when ordinary target selection fails.
4. Freeze accounting rebases on trajectory installation/generation and caps
   its own increment at now. Truly future-stamped inputs still fail the complete
   trajectory validator.
5. v196 planner profiles explicitly permit cloud age <= 0.35 s; generic default
   remains 0.25 s. Source timestamps and geometric/support checks remain intact.
   Non-hover emergency replanning uses finite horizontal speed < 0.15 m/s;
   hover-stop recovery retains its original full 3D velocity criterion.

## Direct results

| Check | Observed result |
|---|---|
| Native ARM64/Foxy build | All 11 selected packages built; 14 packages available |
| Full rebuilt-package tests | 93 colcon entries, including wrappers; 81 actual cases; zero errors/failures/skips |
| Controller package | 27 controller/FSM cases, 1 tracking parity, 1 executor shutdown |
| Mission bridge | 27 pytest cases; real ROS/HTTP with deterministic PCT fixture |
| Planner/math/plugins | 6 path utilities, 6 publisher units, 3 live launch tests, 2 spline cases, 8 plugin cases |
| Generated profiles | 2 tests pass |
| Native probes | V176_TERMINAL_CAPTURE_PASS and V196_CORNER_LOOKAHEAD_PASS |
| Mac host suite | 24 tests; zero failures/errors/skips |
| Live graph | Four active lifecycle nodes; exact v196 controller/native libraries loaded |
| Runtime configuration | 1 Hz BT pipeline; live SCAN cloud-age parameter 0.35 s |
| Transport | Bidirectional shared mount verified |
| Execution source | All 272 files match the local inventory; 40 changes relative to v176 underlay |
| Preservation | All 14 protected trees / 12,427 entries unchanged, including modes, mtimes and symlinks |

The first build stopped on ownership-type errors in new C++ test fixtures;
its log/source are preserved. The next build passed 91 colcon entries, but review
found two inherited launch classes silently discovering zero tests. The classes
now inherit unittest.TestCase and require actual planner startup output. The
final suite executes both and passes 93 entries. Both earlier evidence sets are
retained under verification; the receipt also rejects empty test-result files.

The graph preflight uses static identity world-to-base TF, sends no navigation
goal and advances no physics. run_mac_full.py was not invoked. Component and
live-graph qualification does not establish full-route arrival, elimination of
all stalls, latency improvement, physical stopping, reliability or robot safety.
The cloud-age policy adds 0.10 s of tolerated observation age and needs subsequent
physical evaluation. v194's existing physical result remains unchanged.

See quality.json and verification for measured evidence, native_sources.json
for source identity, changes.patch for the v194 delta, and manifest.json for the
freeze. Post-freeze verification is also recorded in the task evidence directory
and codex_v196_build_and_qualify.md. The named audit input contained only a
completion message; source_audit.json records that limitation.
