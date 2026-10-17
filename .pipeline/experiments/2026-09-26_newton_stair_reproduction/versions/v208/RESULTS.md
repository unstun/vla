# v208 result: stillness-based return passes two short physical comparisons

Stage: experiment + analysis. Candidate parent: v206. Frozen manifest:
`7472c07817bcfaf2b128ecc39e188ebc31416d2232c67d97c68689be971fad09`.

## What changed

Only the versioned locomotion return changed. Zero-command entry now requires
body and joint stillness for 0.25 s, followed by a two-second PD crossfade with
a 0.2 rad per-joint stand-target offset cap. The target is captured from the
current V12 state by the existing torque-matching rule; no V21k nominal pose
or equal-leg posture was imported. Initial factory holding, disturbance exit,
REJOIN, policy/history and motor limits retain the parent behavior.

The unchanged navigation implementation remains v206: PCT/SCAN geometry,
Tracker, 1 Hz global refresh, final position/yaw gates, the ten-second terminal
budget, two-second measured PD confirmation and retry policies are untouched.
`activate.install()` explicitly selects this candidate before robot construction;
the full-navigation default was not silently replaced.

## Checks on gpu5070ti

- Candidate behavioral unit tests: **10 passed**.
- Original preserved hold suite: **53 passed**. The initial invocation failed
  because its test file was missing from the remote execution copy; copying the
  unchanged local test file resolved the setup error. Both logs are retained.
- Recorded v206 input: the old source exactly reproduces all **543** terminal
  mode/reason/progress samples with no transfer. The candidate first allows
  transfer at **115.867950 s**, about **0.320 s** after the final zero input.
  The candidate replay stops at that first ownership change; later behavior
  requires physics, not continued replay of the old trajectory.
- Both captured-state restoration preflights passed: q/qd, native body pose,
  full ten-frame policy history, source identity and adapter selection checked.
- No C++ packages changed or were rebuilt. Newton's first-use kernels compiled
  on gpu5070ti; no local compilation was used.

## Paired physical results

Original Building triangle mesh, original Warp CPU contact path and V12 ONNX
policy. Every arm receives zero command from the same captured initial bytes.
The snapshots are test fixtures, not coordinates embedded in the controller.
Each arm ran about ten physical seconds; total actual integrations: **40,040**.

| Initial state | Original hold | v208 candidate |
|---|---|---|
| Final-zero boundary, original time 115.548126 s | No transfer within 10.01 s; remains STAND_SETTLING/support_balance | Transfer observed at 0.340 s; FIXED_STAND at **2.359 s**; **7.656 s** continuous measured PD hold |
| Quiet but balance-blocked state, original time 120.285522 s | Transfer only at 9.831 s; no FIXED_STAND before the 10.01 s bound | Transfer observed at 0.280 s; FIXED_STAND at **2.299 s**; **7.713 s** continuous measured PD hold |

Times in this table are post-control-interval telemetry observations; the hold
decision occurs one 20 ms control interval earlier. Passing requires physical
speed <=0.03 m/s, angular speed <=0.05 rad/s, all four feet >1 N, PD ownership
at gains 60/1 continuously for at least two seconds, no fall, and the existing
action-history/motor mapping tolerances. Neither original arm met this gate
within its bound; both candidate arms did.

| Candidate measurement | Zero-boundary fixture | Quiet-blocked fixture |
|---|---:|---:|
| Maximum body tilt | 5.826 degrees | 4.255 degrees |
| Maximum XY drift from initialized state | 3.189 cm | 0.678 cm |
| Final XY drift | 3.114 cm | 0.408 cm |
| Minimum individual foot force while FIXED_STAND | 2.613 N | 11.350 N |
| Frames at >=95% static torque limit | 0 | 0 |
| Applied-action history error | 0 | 0 |
| Maximum requested/applied motor torque mismatch | <4.77e-7 Nm | <2.39e-7 Nm |

All four arms remained upright with no torque-limit sample. The first candidate
holds an asymmetric stance with a lightly loaded hind-right foot (about 2.6 N).
This is a measured hold under the declared existing >1 N criterion, not proof
of equal loading, disturbance robustness, or a preferred nominal posture.

## Interpretation and limits

The matched old zero-boundary arm reproduces the support-balance blockage in
actual physics. Replacing the entry rule and transfer behavior lets the robot
complete a measured PD hold from that state. This is stronger evidence than an
enum-only unit test or forcing the balance predicate to pass on old telemetry.

The probes restore recorded robot state, applied targets/gains, last action and
all ten policy-history frames. Solver contact/warm-start buffers were not
recorded and are rebuilt equally in both arms. They are controlled initialized-
state comparisons, not byte-exact continuations of the original episode.

No new whole-route navigation was run. The last accepted complete-route trial
remains v204 on Mac; v206's Linux route remains a recorded failure. These two
fixtures do not establish arbitrary slopes, steps or disturbed-support coverage.
The quiet-body tilt limit comes from the inspected upstream mechanism, not
this Building coordinate. No threshold was tuned after these outcomes.

## Evidence and reproducibility

- Frozen code and protocol: `manifest.json`, `PLAN.md`, `changes.patch`.
- Tests and fixed-input result: `results/components/`.
- Compact physical results and time series: `results/physical/`.
- Source/raw-file hashes and all four outcomes: `results/physical_summary.json`.
- Heavy raw recordings: `gpu5070ti:/data/sun/vla_mppi_20261009/stance_v208/`.
- Candidate command: `probe_stop.py --variant candidate --seed zero_boundary
  --output <new-owned-directory>` with the existing Newton worker Python and
  `WARP_CACHE_PATH` set. `old` selects the pinned original hold; `quiet_blocked`
  selects the second recorded fixture. Existing output directories are refused.

Run labels and outcomes remain separate. A successful probe script exit does
not mean its physical `result.json.passed` is true; the baseline failures are
deliberately retained as the controls.
