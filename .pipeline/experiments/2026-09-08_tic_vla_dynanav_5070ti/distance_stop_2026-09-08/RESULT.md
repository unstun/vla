# Chinese three-meter stop test

The completed trial **did not follow** `向前直走 3 米，然后停下`. The robot
turned and drove opposite its initial forward direction. It never reached the
forward 3 m reference and did not produce a qualifying voluntary stop. Even
when cumulative traveled distance first crossed 3 m, measured speed was still
1.382 m/s and desired speed was 1.500 m/s.

This result concerns one Chinese command in the current TIC-VLA/Nova Carter
simulation and waypoint controller. It does not establish that every VLA, or
this checkpoint under every prompt, cannot follow metric instructions.

## Recorded outcome

Completed execution: `20260908T162313Z_3m_zh_retry`.

| Measurement | Observed value |
|---|---:|
| Finite model predictions | 301, each `(1,30,2)` |
| Largest forward displacement along the initial heading | 0.1061 m |
| Final forward displacement | -8.4395 m |
| Final cross-track displacement, positive left | +2.3047 m |
| Sampled cumulative path after command | 9.7710 m |
| Benchmark full-episode path | 9.7809 m |
| Final distance from the relative 3 m reference | 11.6694 m |
| Continuous qualifying stop windows of at least 2 s | 0 |
| Measured speed when cumulative path first crossed 3 m | 1.3822 m/s |
| Final desired linear / angular command | 0.1691 m/s / +1.2000 rad/s |
| Final measured planar speed / yaw rate | 0.0623 m/s / +0.2075 rad/s |
| Recorded simulator time after instruction | 15.0000 s |
| Frame-derived time after instruction | 30.0 s |
| Encoded video duration | 49.24 s |
| Sampled total GPU peak | 15219 MiB |

All 301 actual inference-audit instructions match the original Chinese text.
The episode ends at the declared timeout, not because the policy stopped or
because it reached the reference point. The benchmark's `success=false` is
expected when its goal-termination function is disabled; the independent
distance/speed measurements establish this trial's task failure.

In later samples the measured speed becomes nearly zero while desired motion
remains nonzero. This does not count as a commanded stop. The benchmark reports
no detected human or physical collision in the completed run; that detector
output is not proof of unobstructed motion or a cause of the slowdown.

The fixed overhead camera covers the start and intended forward route. The
robot leaves its left edge while traveling in the wrong direction. The original
footage retains that limitation; measurements and the complete trajectory plot
continue throughout. No camera motion or replacement footage hides the failure.

## Predeclared protocol

- Stage: experiment and analysis. User explicitly requested execution after
  discussing a direct metric-language test.
- Instruction: `向前直走 3 米，然后停下`, verbatim; direct text input, no ASR or
  translation. One completed trial plus one retained crashed attempt.
- Same hospital, start `[-3,-1.2,0.01]`, initial yaw 0, 20 people, scenario seed
  36 and inference seed 36 as the earlier demo. Actual measurement origin and
  initial heading are captured at the frame-120 instruction application.
- Distance means displacement projected onto the initial heading. Cross-track,
  net displacement and accumulated sampled path are separately recorded.
- The 3 m goal coordinate is used only for evaluation/display, not policy input.
  Goal-based termination and automatic stuck/back-up behavior are disabled in
  this isolated copy, so intentional stillness cannot trigger forced reversal.
- Policy source, weights and waypoint-to-velocity controller are unchanged;
  byte comparison of the policy modules and compiled controller slice passed.
  Slew limits and the camera-readiness gate remain active.
- A candidate stop requires forward `3 +/- 0.25 m`, cross-track within 0.25 m,
  measured planar speed and desired/applied linear commands below 0.05 m/s,
  measured yaw and desired/applied angular commands below 0.10 rad/s, for at
  least two continuous simulator-timeline seconds, without hold/recovery.
  Reaching the threshold never sends a stop command.
- Episode bound: 1020 benchmark frames, called 34 seconds by the upstream
  frame-count convention; outer process deadline 600 wall seconds. The measured
  timeline advances 0.05 s per three-frame telemetry sample in this environment.
  Consequently, the 900 frames after the command cover 15 actual timeline
  seconds, rather than 30. Analysis uses the observed timeline for stop duration.

## Runtime failure and controlled retry

First attempt `20260908T161736Z_3m_zh` ended with child code `-11` at frame 927.
Its last stderr coincides with the 90-second periodic `faulthandler` dump and
contains a partial thread trace. The parent nevertheless returned exit 0 and
substituted a `no_result_file` episode with zero duration/path/collision fields
and infinite navigation error. **Those fallback metrics are invalid evidence.**
The local analyzer labels the attempt incomplete and collision status unknown.
Its 270 predictions and 46-second partial video remain available.

The retry removed only periodic traceback dumping from runtime behavior;
instruction, seed, config, model, scene, goal handling and controller remained
the same. It completed all 1020 frames with a real episode result. This single
retry supports using the dump-free execution copy, but does not establish the
native crash's unique cause. The first executed source is preserved under
`attempts/20260908T161736Z_3m_zh_source/` with its original manifest.

## Source and validation

Local source of truth: this dated experiment directory. Remote execution copy:
`/home/sun/vla_exec/2026-09-08_tic_vla_dynanav_5070ti/distance_stop_2026-09-08`.

- Parent demo manifest: `4a940f97a40d7cb513efd044f7df707daf71a13073f303b7395a4f050832c8c0`.
  All 65 parent files remain unchanged.
- First probe manifest: `18f8c8641ff19998b7a32ae712b2de5f980a1fa106872452b05882dba9014779`.
- Completed probe manifest: `cd3d13f7b90114b9ad211f7a97a86a00ab5906c32c6acc575264f38087e8eda2`;
  71 source/config/patch checks passed before launch.
- Pinned upstream: `9fa6f8b66b9e121d5df5df071297bba8e5353ebb`.
  Base-model revision: `4415a3b810e636d11dfa86b0e9ba40bb00535aa8`.
  Checkpoint SHA-256: `376263f89fad0f42c267d85655019232edc91d36e214e23424804dd4cd42e036`.
  All 21 model assets passed the current remote hash check, followed by strict
  checkpoint loading during simulation.
- Eight tests passed: verbatim metric text, rotated-frame measurement, path vs
  displacement, false-stop rejection, continuous hold duration, and existing
  request/latch/camera contracts. Source syntax and controller parity passed.
- All 363 completed-run artifact checks and 333 first-attempt checks passed
  locally, including archived raw frames. The final front-camera image also
  matches its remote SHA-256. Both videos fully decode.
- Representative overhead frames and the distance/speed plot were inspected.
  Process group 81816 exited; GPU returned to 252 MiB and 0% utilization.
  No physical robot, training, persistent website or Git commit was involved.

## Artifacts and reproduction

- [Completed video](runs/20260908T162313Z_3m_zh_retry/navigation_with_trajectory.mp4)
- [Distance and speed plot](runs/20260908T162313Z_3m_zh_retry/distance_speed.png)
- [Measurement analysis](runs/20260908T162313Z_3m_zh_retry/distance_analysis.json)
- [Raw telemetry](runs/20260908T162313Z_3m_zh_retry/telemetry.jsonl)
- [Local integrity](runs/20260908T162313Z_3m_zh_retry/local_integrity.json)
- [Failed first attempt](runs/20260908T161736Z_3m_zh/distance_analysis.json)
- [Exact local modifications](manifests/distance_probe.patch)
- [Predeclared plan](plan.json)

`prepare_distance.py` reconstructs the isolated source from the verified parent
manifest. Place a new UTF-8 request under `requests/NEW_RUN_ID.json`, sync the
package and recheck source/model hashes before launching the existing bounded
`scripts/launch_batch.sh NEW_RUN_ID top_down` on the execution host. Retrieve
the whole run except expanded `frames/` (the verified archive contains them),
then run `python3 analyze_distance.py NEW_RUN_ID` locally. Do not reuse run IDs
or reinterpret packaging success as episode completion.
