# PD switching and one completed empty long route

Stage: experiment + analysis. Date: 2026-09-27. Local simulation only.

## Current result

`empty_long_root_live08` passes the prospective empty 12 m route checks:
native PCT/SCAN arrival, actual movement and final PD hold. The delivered regular
MP4 is `output/2026-09-27_lite3_pd_long_route/lite3_pct_scan_12m_pd.mp4`.
This validates one bounded trial under the instrumented native CPU condition
below. Repeatable startup, obstacle avoidance, the original Isaac A4 and physical
factory calibration remain unvalidated. Earlier failures are preserved.

| Measurement | Recorded result |
|---|---|
| PCT global route | 12.000 m |
| Actual accumulated navigation path | 12.0169 m |
| Net navigation displacement | 11.9003 m forward, 0.0246 m lateral |
| Final XY distance to the original goal | 0.19697 m, within the existing 0.25 m criterion |
| Native terminal | `arrived`, cause `arrived_after_quiescence` |
| Final PD hold | 2.080 s, Kp 60 / Kd 1, policy does not own joints |
| Native moving curves | 12, within 18 total spline messages including holds |
| Continuous physics | 41.760 s / 41,760 steps, including 11.040 s factory prefix |
| Minimum navigation body up-z | 0.99714; no fall |
| Applied snapshots / sensor frames | 1,531 acknowledged, zero mismatches / 307 paired unfiltered frames |
| Review / media | 15 common checks and 17 route checks pass; 522 frames, 1280 x 720, 12.5 fps |

Direct evidence: `../../validation/empty_long_root_live08_review.json`,
`../../validation/empty_long_root_live08_long_route.json`,
`../../runs/empty_long_root_live08/` and `video_delivery.json`.
The common review's historical `navigation_validated` boolean only admits
`flat_static`/`flat_box`; it remains false for this new profile. Its common checks
pass, and the dedicated long-route reviewer is the acceptance result.

Dr Sun resumed after freeing storage. The measured free space was 30 GiB at
resumption and 35 GiB after rendering. The previous 182 MiB and blocked launch
remain historical failures; no unique evidence was deleted or guard lowered.

## Implementation and reused sources

- Reuse the existing `isaac_runner/stance_hold.py` without editing it, SHA-256
  `9a97879a5d5ed2f7c9c3e327c1193b1c42cf079eaaf073a855afad53a7dbc306`.
  Preserve auto/xfade1s, Kp 60/Kd 1, support balance and quiet-state gates.
- Newton adapter: `2026-09-26_newton_macos_policy/scripts/newton_stance.py`.
  Policy-owned steps feed raw policy actions back; PD/blend-owned steps feed
  the action represented by the actual target, as the prior local code does.
- Newton v1.6.0 pinned `c2ca70bec5998062b0b2d35869865cbe3a49feee` provides
  SensorContact/update_contacts. Original source is retained in E1 `source/`.
  Upstream example: [contact sensor](https://github.com/newton-physics/newton/blob/c2ca70bec5998062b0b2d35869865cbe3a49feee/newton/examples/sensors/example_sensor_contact.py).
- Native CPU mode reuses E1's original `SolverMuJoCo(use_mujoco_cpu=True)`.
  Foot-force extraction follows the existing read-only `machine-dog` runner
  at commit `fd751b8b`, `_foot_contact_forces`; original source SHA is recorded
  in the unchanged hold module. Foot identity uses original 22 mm spheres.
- Factory startup reuses the audited local algorithm process and source library
  hash in `2026-09-27_lite3_factory_runtime_audit`. Original encoder/calibration
  limitations remain; factory zero flags are not physical calibration proof.
- Native PCT, the SCAN42 geometry v9 algorithm, selected planner YAML and
  controller retain their original logic and limits. The accepted trial uses
  `scan43_prefix_diagnostic_v2`, a separately identified copy with prefix and
  occupancy diagnostic logging. PCT computes the 12 m route from the synthetic flat
  support prior. Real geometric ray returns supply local obstacle evidence;
  the scene contains no human/box/wall. Localization is simulator body state.

## Preserved tests and attempts

| Run | Evidence | Result |
|---|---|---|
| Existing hold tests | 53 pure tests | Pass |
| E1 `pd_long_motor_contracts01` | Original 8 tests | Deadline regression caught; original 600 s E1 limit restored |
| E1 `pd_long_motor_contracts02` | Original 8 tests | Pass |
| E1 `pd_long_motor_contracts03` | 9 tests incl. read-only physical observer and identical dynamics | Pass |
| `pd_switch_control01` | Fixed scripted stop durations, no factory prefix | Failed PD stop/rejoin and upright checks |
| `pd_switch_factory02` | Factory prefix, same short stop windows | First stop remained settling; final transition began near the run end |
| `pd_switch_factory03` | Restart only after measured two-second PD dwell | Three holds, two rejoins pass; 43.927 s continuous physics |
| `captured_lidar01` | Background ray query of captured pose after physical state advances | Exact point/world parity and unchanged physical state pass |
| `pd_switch_native04` | Same switching qualification using native CPU solver | Three holds, two rejoins pass; 42 s physical / 24.077 s total wall |
| `empty_long_route01` | Native PCT/SCAN, Warp CPU | About 1.9 m movement, then `odom_stale`; no arrival |
| `empty_long_route02` | Fresh body pose every five physical substeps | About 0.83 m movement, then `odom_stale`; no arrival |
| `empty_long_route03` | Captured-state background sensing and ordered evidence writer | About 1.37 m movement, then `heartbeat_stale`; no arrival |
| `empty_long_route04` | Explicit native CPU full-route profile | Preflight refused below 10 GiB free; no physics executed |
| `empty_long_route05` | Native CPU after free space temporarily returned to 14 GiB | `initial_heartbeat_missing`; no completed route |
| `empty_long_route06` | Native CPU, navigation pacing factor 0.5 | `initial_heartbeat_missing`; no movement |
| `empty_long_prefix_live07` | First diagnostic prefix build, same pacing | Initial heartbeat failure; no arrival |
| `empty_long_root_live08` | Second diagnostic build, native CPU, pacing 0.5 | All 17 prospective route checks pass; native arrival and final PD hold |
| `empty_long_video08/09/10` | Same recorded states, successive camera/label adjustments | Final video10 fully decoded; earlier renders retained |

Do not merge these verdicts. A completed recording process is not a route
success. The first two long attempts exited zero but their actual driver/backend
results failed. The later long-profile worker also exits nonzero on failed or
missing finish conditions.

## Timing diagnosis and remaining work

The first long run had a 0.2957 s native body-observer gap versus the unchanged
0.25 s odometry watchdog. Publishing actual substep states and moving ray/I/O
work off the physical loop preserve true sample times but do not solve all
stalling: run03 has a 0.563 s control interval and a heartbeat timeout. Do not
claim the bridge optimizations alone fixed navigation.

The native flat CPU solver passed the factory/PD/RL component test and the one
accepted route. Navigation was explicitly paced at half physical real time;
the whole run took 83.699 s wall time including startup. The video replays
41.760 s of recorded physical time. It is not evidence of real-time execution.

The successful trial still records 15 rejected clock samples, four command
reconnects, five clock-unsynchronized and six disconnected control steps. These
steps commanded zero. Short stops are retained in the video. Original odometry,
heartbeat, sensor freshness, occupancy and support gates were not relaxed.

Fixed-input native probes found a 1 m seed that succeeds where an initial
1.925 m seed fails. Repeating the short search after a failed long search also
succeeds, so persistent AStar state alone does not explain the live failure.
Frozen-input native replay produces three moving curves. Very small changes
around the PCT height of 0.3 m change voxel queries; no height snapping or
tolerance change was applied. Actual body heading freshness is another timing
lead, not a proven cause. See the retained `empty_start_*`,
`empty_search_sequence01` and `replays/empty_prefix_diagnostic01` records.

Both diagnostic builds start from hash-verified SCAN42 v9 and change only
`scan_replan_fsm.cpp` logging/query calls. Source/build evidence is preserved
in `build_evidence_scan43_prefix_diagnostic*`. Extra diagnostics can change
wall-time scheduling. Run08 therefore does not prove that initialization was
fixed or that the default uninstrumented build is equally reliable. Its baseline
and default selection remain unchanged.

Next work, if requested, should first reproduce the default build under the
same registered empty scene and record first-seed occupancy plus pose/cloud age.
Resolve the discrepancy with the existing upstream implementation and frozen
input controls before changing behavior. Then qualify repeated startup and
arrival separately; do not promote this trial to obstacle or stair validation.

The exact physical command, environment, build identity and source copies are
in run08 `request.json`, `episode_request.json` and `execution_sources.json`.
Use new run IDs for reruns. Replay regeneration and byte verification are in
`video_delivery.json` and `verify_video_delivery.py`; no physics is advanced
by the renderer. Orange is the native PCT path and cyan the native local spline;
the grid and overview are display-only. The displayed `command vx` is the
applied velocity command, not a measured speed.

## Local-only regenerable bytes

`LOCAL_ONLY_BYTES.json` records every file's storage path, size and SHA-256 in
the two diagnostic runtime builds, three replay PNG directories and four native
probe build directories. The runtime is covered by the existing experiment
runtime ignore; PNG/probe directories use new exact path entries only.
Sources, physical records, sensor returns, native logs and MP4s remain visible.
Recreate diagnostics with the retained materializers and hash-verified SCAN42
baseline; build requests, source/install manifests and the exact changed C++
source are also copied into `build_evidence_*`. Recreate the probes using their
own run `request.json` and retained input/source copies, with a new output ID.
Recreate PNGs with each render's saved request/source and unchanged video states.
These are reconstruction instructions, not permission to delete the existing
bytes or unique evidence.

Pre-edit source snapshots and `changes.patch` are retained here. The original
Isaac moving-person stair A4 remains open. No remote server, hardware actuation,
training, staging or commit occurred.
