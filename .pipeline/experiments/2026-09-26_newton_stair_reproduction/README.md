---
origin: ai_only
reviewed: false
date: 2026-09-26
---

# Local Newton reproduction of SCAN stair integration

Stage: experiment + analysis. Active work follows the existing task's
`NEWTON_REPRODUCTION_PLAN.md`. Dr Sun requested reproduction of the previous
work after the local Newton/Lite3 flat-ground qualification.

Latest follow-up: [version index](versions/README.md). Dr Sun designated the
accepted empty-floor system as v3 and requested one integer version per change.
[v4 Building test](versions/v4/RESULTS.md) passes original-site factory/PD
standing, but PCT's 5.07 m route produces no accepted SCAN moving spline.
Navigation fails before motion; its actual video and diagnostic evidence are
retained. v3 remains the last accepted empty-floor condition.

The preceding [PD and 12 m empty-route result](repairs/2026-09-27_pd_long_route/RESULTS.md)
records one accepted local trial: 12.0169 m actual movement, native arrival,
0.19697 m final error and 2.080 s final PD hold. It uses native CPU physics at
navigation pacing factor 0.5 and SCAN42 v9 with diagnostic logging. Startup
repeatability and obstacle/stair acceptance remain open. The verified regular
video is `output/2026-09-27_lite3_pd_long_route/lite3_pct_scan_12m_pd.mp4` in the
repository root. Earlier failed trials remain in the report.

The preceding follow-up `repairs/2026-09-26_generic_occupancy/RESULTS.md` records the
class-independent geometry repair, pinned upstream reuse, native curve tests
and the separate Newton contact-capacity correction. Full avoidance and the
original Isaac stair gate remain open. Historical evidence below retains its
original source/configuration conditions.

The 2026-09-27 follow-up `repairs/2026-09-27_pd_startup/RESULTS.md` adds an
explicit crouch/PD stand mode using the pinned official Lite3 SDK spline.
Startup physics and bridge checks pass; a real static-human goal was released
after standing and produced one short curve, but the episode was interrupted
by a recorded Docker OOM. This is not a completed navigation result.

Local source of truth: `/Users/sun/tongbu/study/phdproject/vla`.
The prior Isaac archive is immutable. This experiment owns only its new source
copy, platform adapter, configuration and evidence. Source acquisition/build,
native replay, sensor qualification and closed-loop outcomes are separate gates.
The local native graph is now integrated with actual Newton physics and
geometric sensing. Stair navigation is **not validated**: the latest bounded
run terminates with `command_timeout`, after limited forward progress.

## Current evidence

| Gate | Direct local evidence | Boundary |
| --- | --- | --- |
| Native SCAN33 source/build | `builds/scan33_humble_amd64_v1/build_result.json`: all 93 source files unchanged, seven packages built, 158.7 s | Local cached ROS Humble amd64 image under Docker, different from archived Foxy |
| Original recorded inputs | `replays/old_positive_v1/review.json`: one moving curve from one checked seed; `replays/fresh_live_v1/review.json`: one moving curve from three checked seeds | Recorded-input native optimizer execution, not a live Newton navigation run |
| PCT runtime | `setup/pct_probe_v2/route.json`: 37 optimized waypoints through the original map | Native compiled PCT in Linux amd64; no route modification |
| Original Building physics | `runs/original_scene_stance_v2/result.json`: 2.000037 s, 2,000 dynamics steps, final up-z 0.99824, 30 contacts | Zero commanded velocity; MuJoCo-Warp CPU with Newton triangle contacts |
| Official human skin | `runs/asset_probe_v1/`: 11,457 vertices, 21,097 triangles, nine original meshes; repeatable skinned deformation | Source USD/animation, no procedural proxy |
| Upstream-backed sensor exclusion | `runs/lidar_upstream_contract_v2/result.json`: all controls pass, 180 fixed-root skin-dependent ray changes; three actual scene sweeps contain 9,707 / 9,833 / 9,851 valid points | Explicit original-sensor-link exclusion; geometric rays, no RTX or physical MID360 equivalence |
| Existing flat controller regression | `runs/flat_contract_regression_v2/run.log`: six tests pass | Qualified observation/history/motor contract retained after adding the scene/URDF seam |
| Cross-OS clock mapping | `runs/clock_reference_v1/result.json`: 1,124 comparisons with extracted MAVROS C++, maximum difference 0.109375 ns; `clock_live_v1` exercises the real Mac/Linux channel | Original 250 ms command watchdog retained; local uncertainty checks can reject motion |
| ROS executor | Multi-threaded backend received 2 callbacks versus 150 independent observations; single-threaded comparison received 149/149 | Standard executor change at entrypoint; archived backend core unchanged |
| Applied-state transport | `native_bridge_zmq_probe_v2`: 150 valid acknowledgments and four independent negative controls | Standard PyZMQ JSON REQ/REP; old probe copyback receipts do not prove tmpfs byte identity |
| Actual local stair loop | `stair_native_walk_v2`: 28.056 s, 28,060 physics steps, 280 sensor frames, two moving curves, 797 nonzero command steps | Goal failed on unchanged 35 wall-second timeout; net forward displacement 0.375 m, final XY goal distance 4.639 m |
| State return and video | `validation/stair_native_walk_v2_review.json` and `stair_video_review.json`: 15 interface checks, byte-exact Linux copyback, 350 frames decoded | 28 s replay rendering of actual recorded states, not live rendering or accepted stair avoidance |

Failures are retained in their original run directories. In particular,
unfiltered rays mostly hit the sensor housing; the optical-only exclusion was
disproved. The earlier two-mesh diagnostic was requalified against upstream
behavior before selecting it. The generic sensor constructor defaults to no
exclusion; the qualified probe requests the selected mode explicitly.

## Upstream-first handling

Dr Sun required GitHub source inspection before problem-specific workarounds.
The source comparison, exact commits, license checks and rejected alternatives
are in `../../survey/2026-09-26_newton_lidar_bridge_upstream_survey.md`.

The selected sensor-owner convention comes from Robotec's RGLGazeboPlugin
and MuJoCo's native rangefinder. The adapter resolves both visual meshes of
`mid360_body_link` in the original URDF, then uses Newton's public flags/BVH
API on a separate sensor model view. Physics and rendered shapes are unchanged.
The analytic comparison with installed native MuJoCo yields matching ranges
at 1.9 m, 0.35 m and 0.06 m. The 0.06 m external blocker invalidates the return
but does not expose the background. Other robot near occluders remain present.
The human follows Warp's update-points, refit, query pattern.

The archived TCP command state and applied-evidence reader assume one monotonic
clock domain. The bounded adapter now ports the pinned MAVROS filter and maps
source timestamps conservatively into the receiver's clock domain. The original
sensor/body/command wire formats, limits and watchdog remain unchanged.
The inspected `newton_ros` candidate remains surveyed only. Do not guess a
constant offset, disable freshness checks, relax planner bounds or reconnect
the shut-down server.
`setup/clock_domain_probe_v1.json` directly confirms unequal macOS/Linux
monotonic origins; `clock_domain_process_probe_v1.json` checks two child
processes within the same Linux clock progression. These are read-only
diagnostics, not a reusable time offset or proof of clock synchronization.

Mac bind-mounted atomic JSON replacement was independently observed to yield
truncated reads. PyZMQ now transfers each complete snapshot into Linux tmpfs,
where the original reader validates the bytes. The launcher returns the mounted
contents with Docker's documented `exec tar` method and checks the final SHA-256
against the last acknowledged message before container cleanup.

In the latest run, all 1,398 positive snapshot acknowledgments match their
actual commands. There are no applied-reader errors after the first snapshot;
124 startup missing-file observations precede it. Clock RTT rejection still
causes 10 command reconnects and 22 zero-command policy steps. These are retained
as a limitation, not hidden by retries or relaxed checks.

The second native moving curve is retimed from a 1.6 s seed to 34.250 s
(`scan.log`, scale 21.4064). This is a concrete lead for the slow progress, not
proof that the locomotion policy would otherwise complete the stairs. Separate
trajectory timing, low-speed tracking and wall-time/physics-time budgets in the
next diagnosis. The original Isaac A4 and human collision/avoidance acceptance
remain open. See `RESULTS.md` for the outcome and next source inspections.

Delivered regular video file:
`/Users/sun/tongbu/study/phdproject/vla/output/2026-09-26_newton_macos/lite3_newton_stairs.mp4`.
It includes original Building, original official right-side animated human,
actual robot states, native curves and the failed navigation status.

Latest display-corrected video (robot, human and Building):
`/Users/sun/tongbu/study/phdproject/vla/output/2026-09-26_newton_macos/lite3_newton_stairs_robot_color_fixed.mp4`.

After Dr Sun identified strange colors, `COLOR_CORRECTION.md` records a
render-only correction for authored USD tint/visibility and Building color.
The same recorded motion is rerendered in `stair_material_video_v3`; the earlier
video is preserved. The visibility inspection also identifies a separate
limitation: the recorded ray scene included four authored-invisible human
accessories. Those sensor records are unchanged and require separate visibility
requalification before visible-USD/Isaac sensor parity can be claimed.

## Re-running the bounded integrated episode

Use a new run ID and the existing pinned environment/image:

```sh
python3 .pipeline/experiments/2026-09-26_newton_stair_reproduction/scripts/run_bounded.py \
  --run-id stair_native_walk_review --deadline 600 -- \
  /Users/sun/tongbu/study/phdproject/vla/.pipeline/experiments/2026-09-26_newton_macos_policy/runtime/.venv/bin/python \
  /Users/sun/tongbu/study/phdproject/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction/scripts/run_local_episode.py \
  --backend-executor single --applied-transport zmq
```

Then run `scripts/review_local_episode.py --run-id stair_native_walk_review`.
Render only after physics stops, using `scripts/render_episode.py --source-run
stair_native_walk_review` through the same bounded launcher with a new render
run ID. Navigation failure is recorded separately from interface checks and
the original driver's `execution_completed` flag.

## Re-running the qualified sensor gate

From the project root, use a new run ID (existing runs are immutable):

```sh
python3 .pipeline/experiments/2026-09-26_newton_stair_reproduction/scripts/run_bounded.py \
  --run-id lidar_upstream_contract_review --deadline 90 -- \
  /Users/sun/tongbu/study/phdproject/vla/.pipeline/experiments/2026-09-26_newton_macos_policy/runtime/.venv/bin/python \
  /Users/sun/tongbu/study/phdproject/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction/scripts/probe_lidar.py
```

`result.json` must contain `accepted=true`, unchanged physical/render flags,
the three native-MuJoCo occlusion controls, retained other-robot occlusion and
both animation controls. A zero process exit alone is insufficient.

## Local-only bytes and reconstruction

The generic-occupancy follow-up keeps every failed/successful candidate and
episode. `repairs/2026-09-26_generic_occupancy/RESULTS.md` is the current evidence
index; one human arrival does not establish stable navigation. The original
Isaac stair gate remains open.

Generated `runtime/scan34*` through `scan42*` candidates are covered by the
existing exact experiment runtime rule. Returned `build_evidence_*` folders
retain materializers, build requests/logs and source/install hashes. Recreate a
candidate from its own `executed_materialize.py`, identity record and pinned
SCAN33 baseline, then invoke its recorded build request in a new attempt. The
selected v9 probe source is also copied to
`repairs/2026-09-26_generic_occupancy/build_evidence_scan42_geometry_v9/qualified_probe_source/`
because later diagnostic-only changes must not alter the reconstructed build.

Exact flat-video `frames/` paths and the two recorded diagnostic `probe_build/`
paths are separately ignored and inventoried. Frame provenance is the adjacent
`frames.json` plus the immutable source run's `video_states.json`; replay the
saved `executed_render_episode.py` using the saved request under a new run ID.
No physics reset or re-execution is needed to regenerate a video. The adjacent
MP4s, delivered regular-file copies, failed attempts and logs remain available.
The diagnostic build can be regenerated from its adjacent `probe_source/`,
`probe_source_sha256.json`, `inside.sh`, `native_request.json` and the qualified
v9 libraries. Do not overwrite source runs or use a different native library.

All bytes remain inside this project. Path-specific ignore rules cover only
this experiment's copied inputs, runtime sources, build outputs/source copy
and regenerable kernel cache. `setup/LOCAL_ONLY_BYTES.json` records their paths,
sizes and SHA-256; scripts, source provenance, logs, results and source/install
hash manifests remain discoverable. No files were deleted.

- `setup/source_identity.json` maps each original input to the archived Isaac
  run, including the original official-asset provenance. Regenerate an absent
  copy from the listed local source and require its exact SHA-256.
- `setup/runtime_sources.json` maps every runtime-source/library/background
  copy to its archived source with exact SHA-256. Do not substitute newer
  binaries or copy a sibling working tree.
- The native source copy matches the original SCAN33 `source_sha256.json`.
  Build provenance, the cached image identity and the exact build command are
  in `setup/build_scan_local.py` and the build directory's request/result files.
  Rebuild only in a new attempt directory; preserve prior attempts.
- `runtime/` contains generated Newton/Warp caches and extracted SciPy 1.8.1
  CPython3.10 / PyZMQ26.4.0 wheels. `setup/foreground_dependency.json` and
  `zmq_dependency.json` record official wheel URLs, hashes and extracted member
  identities; preparation scripts show acquisition without global installation.
  Licenses remain in the extracted distributions. A bounded rerun regenerates
  kernel caches. The E1 environment is inventoried separately.
- `runtime/diagnosis_plot/` is a separate plotting environment, with exact
  package versions in `setup/diagnosis_plot_requirements.lock`, dependency
  provenance in `setup/diagnosis_plot_dependency.json` and file hashes in
  `setup/LOCAL_ONLY_BYTES.json`. It does not modify the Newton interpreter.
  Recreate it with the recorded Python version and `uv pip install --python
  runtime/diagnosis_plot/bin/python -r setup/diagnosis_plot_requirements.lock`;
  `runtime/uv-cache/` is a regenerable package cache. Use the recorded bounded
  command in `runs/trajectory_diagnosis_review_v3/request.json` to reproduce
  the diagnostic checks and point-cloud plot under a new run ID.
- The exact `runs/stair_native_walk_video_v2/frames/` directory is local-only;
  `frames.json` retains all 350 hashes and source times. Re-render the immutable
  physics states in a new output directory; do not rerun physics to recreate
  this evidence. The original MP4 and result manifests remain discoverable.

The preparation scripts intentionally refuse to overwrite completed identity
records or run directories. They document initial acquisition; recovery must
copy only missing files and verify the recorded hashes.
