# Actual RTX stair and official-human integration

Stage: experiment and analysis. Dr Sun authorized the continuation and requested
a playable video. Local VLA sources and returned evidence are authoritative.
gpu5070ti is an execution copy. These are bounded simulator observations, not
formal training, real-robot actuation, or a validated VLA system.

Current sequential repair evidence is under
`repairs/2026-09-26_sequential/`. scan_20 fixes native search bookkeeping;
scan_21 shares the original segment gate between search and seed validation.
scan_22 repairs right-side moving-cluster extraction and ground coverage;
all 562 captured frames match the installed Foxy ROS tracker, with one stable
actor track after measured motion in both placements. See
`step2_tracking/RESULT.md` for inputs, tradeoffs and acceptance limits. None of
these results closes live moving-person stair acceptance: the fixed planner
still rejects the full recorded target. `--static-background-tracker` opts in
to the verified V3 prior, dependency and independent physical-ground topic;
old prepared runs and their videos remain unchanged.

`runs/stand_scan23_tracker_right_v1` verifies that V3 wiring in an actual 20.08 s
standing scene: 201 ready RTX sweeps, a first right-actor track 0.20 s after
measured motion, 99 nonempty observations with one ID, 49 matching returned
artifacts, zero admitted navigation commands and no nonfoot contact/reset.
This is a tracking integration result; no navigation goal was sent. Its actual
video is delivered at `output/2026-09-26_stair_human/stair_tracker_right_fixed_stand.mp4`.

`run_stair_video.py` packages the preserved Building/V12 runner, an opt-in actual
RTX geometric LiDAR adapter, the native PCT route worker and ground publisher,
native SCAN, the current-observation cluster tracker, controller, backend and a
read-only ROS recorder. The official NVIDIA walking skin is the rendered sensor
target. Its transform log is consumed only by offline outcome scoring. No human
capsule or simulator actor position is supplied to navigation or tracking.

The sensor gate is `../rtx_sensing/runs/mid360_v5_release_order/`. It verifies
actual RTX directions against the pinned Livox CSV and isolated animated-human
tracking. It does not establish a calibrated manufacturer RTX profile. Each
sweep uses a single measured sensor pose; intra-sweep motion distortion is not
modeled. The original Warp sensor is retained solely for static Building
preflight and the mounted pose, and supplies no published navigation returns.

## Execution and evidence

Prepare a fresh run with `--mode stand` or `--mode walk`, a unique `--run-id`,
and `--lead-authorized-execute`. Add `--execute` only after its local package is
reviewable. Existing prepared runs are immutable. The launcher requires a
successful native build and an installed-file identity, verifies staged source
hashes, supervises required processes, collects raw artifacts, and compares
remote/local hashes. A returned `passed` execution record means the observation
completed; it does not certify navigation or avoidance.

Use `review_stair_video.py RUN_DIR` to inspect full-rate commands, measured
progress, contact forces, resets, tracks, stop windows, terminal outcomes and
video identity. Deadline cancellation is excluded from reactive yielding.
Human geometry has no physical collision proxy: the reported robot/person XY
envelope gap is a conservative offline proxy, not a physical contact sensor.
Native nonfoot contact forces and fall/reset state are recorded separately.

## Preserved diagnoses

- `runs/stand_v2`: actual Building clouds and animated-human tracks reached ROS;
  commands stayed zero and the standing robot remained stable. Video and 47
  returned artifacts matched their remote hashes.
- `runs/walk_v1`: zero navigation motion. The physical body clearance incorrectly
  reused `grid_map.body_height=0`, whose frozen meaning is a route-coordinate
  offset. `scan_11` separates `grid_map.reactive_body_clearance=0.35` without
  modifying the frozen planner file or collision thresholds.
- `runs/walk_v2_clearance`: failed before walking because generated YAML was
  indented incorrectly. The generator and a YAML-parser regression test were
  corrected before preparing another run.
- `runs/walk_v3_yaml`: the goal reached native planning, but near-body reference
  voxels were unobserved. Actual returns contain no nearby self echoes at the
  failed start; zero motion is not successful avoidance.
- `replay/scan12_v2`: actual recorded inputs reproduce unknown near-body
  queries (`verdict=6`, no inflated obstacle, initial unknown log odds). Replay
  is deliberately slower than its recorded simulation clock and cannot prove
  live timing. `scan12_v1` retains an earlier replay scheduling race in which
  the goal arrived before its new cloud had been fused.
- `scan_13` adds atomic fusion within the single-threaded cloud callback and an
  explicitly enabled classification for only the current measured TORSO
  interior. The two boxes exactly match the pinned URDF. A stale/invalid body
  pose, any inflated hit, external unknown space, and current tracked people
  remain blocked. No map cells are cleared. `replay/scan13_v1` shows this alone
  is insufficient at the old start, including unsupported rear terrain.
- `support_audit/` applies the actual native terrain header to the delivered
  PCT payload. `prepared/stair_video_scenario_v2/` moves the start 0.12 m left
  and 0.0132 m along world +Y, passes the unchanged mesh/placement screen and checks
  supported terrain at all three initial collision-reference positions.

`--scenario-dir` selects an independently screened scene. `--known-lite3-trunk`
is opt-in and requires URDF SHA-256
`803d552703bcc4f72ce15f38b95bc3f62e3e4ada0b42bf3ecf71b32b6590bb9d`.
The candidate is not a general robot-body inference rule. The frozen accepted
`scan_04`, prior execution inputs, and sibling repositories remain unchanged.

The wider observer camera is read back from the USD session layer before the
episode. It is independent of sensing/control. Delivered clips must decode
cleanly and be visually inspected; static standing or an end-of-observation
stop alone cannot close the moving-person stair acceptance criterion.

## Subsequent native replay candidates

`scan_14` restores 26-neighbor search; `scan_15` restores the computed Z
gradients in both optimizers. Both build but still fail the recorded episode.
`scan_16` records the first rejected spline pose and establishes a measured
versus inferred heading discrepancy (-1.525 versus -0.583 rad) at essentially
the same body position. `scan_17` shares the controller's unresolved-direction
threshold, and `scan_18` additionally uses its complete 0.8 s lookahead, velocity,
and current-body fallback for trajectory checks. Their completed replays still
have no moving spline. The 0.05 m extra-objective-margin ablation also failed;
this ablation is retained only in `replay/inputs_v5_objective_margin/`, and is
not adopted for live execution. Hard collision parameters stayed unchanged.

`scan_19` tests a checked full native path as the spline seed, with correct
signed rounding and a search lattice containing the exact measured start.
Its source candidate preserves the original 0.2 m optimizer preference.
No-path, shifted-start and blocked-edge results fail closed. The native replay completed but exhausted its available search without an accepted path: 329 seed-search failures, no time-cap warning, no moving spline. This does not prove that every possible configuration is infeasible.

Actual media copies are under `output/2026-09-26_stair_human/`. Both files
decode fully and have inspected representative frames. The stair clip is
explicitly named `stair_scene_scan13_no_navigation.mp4`; it is not an avoidance
demonstration. The isolated sensing clip was linked to Dr Sun while integration
work continued.

## Actor placement comparison requested after video review

Dr Sun requested moving the actor to the image right to test whether its
central position was blocking the stair. `prepare_actor_right.py` preserves
the reference y/z route, 10 s activation, speed, robot start and goal. The
right vector at the initial -pi/2 heading is world -X: every actor waypoint
changes from x=-5.30 to x=-5.95 m. The independently saved scenario is
`prepared/stair_actor_right065/`.

Placement uses the actual pinned Building mesh. The selected PCT robot-ground
mask was too restrictive for lateral human placement; its rejected initial
screen remains in `placement_ablation/right_platform_screen.json`. The mesh
screen compares five foot-support samples against the original route and
checks torso-level side clearance, including vertical wall projections.
Its continuous clearance lower bound is 0.3540 m against a nominal 0.30 m
actor radius plus 0.05 m margin. Three geometry unit checks pass. This is a
static placement screen, not animated contact proof, and supplies no new
Building truth to the planner.

`run_stair_video.py --reference-run runs/walk_v4_ego` verifies byte-identical
planner/controller/pilot/worker inputs, identical bridge behavior except the
actor-route hash, and identical Isaac arguments after only run path/identity
replacement. It deliberately copies the original driver, retaining the old
goal dispatch behavior instead of introducing the later settled-start gate.
The reference remains `scan_13`. The first local preparation
`walk_v5_actor_right` failed because the comparator had not normalized
`--external-run-id`; it was never remotely executed and is marked as an
incomplete package. The corrected comparison is `walk_v5_actor_right_v2`.

The comparison completed 29.08 simulated seconds with all 47 returned artifact
hashes matching. All 291 RTX sweeps were ready. The measured actor x coordinate
was -5.95 m throughout; motion began at 10.02 s. All 1,454 admitted commands
remained exactly zero, matching the reference. Maximum incidental XY drift was
0.02257 m, with zero nonfoot force and no reset or pose injection. Navigation
again terminated as `initial_heartbeat_missing`. The first collision record
was the same UnknownObstacle query at (-5.347, 1.078, 1.198); the bounded
near-sensor diagnostics also retained 30 UnknownObstacle samples.

The right-side trial produced **zero nonempty actor tracks**, versus 190 in
the reference trial. This placement did not restore navigation and cannot
establish avoidance or tracking at the new actor location. The cause of the
missing side-position track has not been established by this comparison.

`runs/walk_v5_actor_right_v2/placement_result.json` records the paired evidence.
The delivered real copy is `output/2026-09-26_stair_human/stair_actor_right_comparison.mp4`,
SHA-256 `02afa116da4b3d7162c9dc8388a96afd116385c696a42ce03b049deb49348ee8`.
Its 364 frames decode cleanly (29.12 s, 1920x1080, 12.5 fps). Reviewed 10.8 s
and 12 s frames show the complete actor beside the image-right windows, with
the robot below the stair. The post-run read-only check found no GPU compute
process, running container, or process associated with this run.

## Cause review after the right-side comparison

Dr Sun requested a careful review with one subagent. The independent planner
review and the primary agent's captured-input audit are consolidated in
`diagnostics/2026-09-26_root_cause/REVIEW.md`. This supersedes any interpretation
that the first Unknown warning or the failed scan19 search proves physical
infeasibility.

The first warning checks the distant goal; the FSM subsequently retreats its
target. The native A* marks rejected nodes as already explored before deciding
whether to enqueue them, and initializes its nominal infinite cost with
`1 >> 20` (zero). A separate logging-only scan19 CPU replay of the captured
walk_v4 inputs confirmed 982 encounters with a later-free candidate that never
entered the search queue. The first search exhausted its queue in 5.36 ms,
well below its 200 ms cap. The shared defect exists in scan13, but this audit
does not establish that repairing it alone produces a complete live route.

The same-source tracker replay exactly matches positive-track timestamps:
190 frames at the original position and zero on the right. Of 21,954 returns
in the right-side actor spatial region, 21,927 lack the selected PCT ground
cell and are discarded. This is a ground-coverage/robot-traversability mask
coupling, not absence of raw range returns. Actor truth only defines the
posthoc diagnostic region; it never enters tracking. Complete-empty live
messages do not prove coverage of the entire person-detection region.

The right-side goal is cancelled at 2.16 s after no matching-generation
controller heartbeat; the two splines are constant-position stop output.
Actor motion begins at 10.02 s, so the recording never reaches active dynamic
avoidance. Stair Z constraints, multilevel support association and early
stand-transition goal dispatch remain separate issues documented in the
review. Original builds, live inputs and recordings remain preserved. A4
remains open; no repair candidate was promoted.

## Sequential repair evidence, 2026-09-26

The subsequent repairs are tracked in
`repairs/2026-09-26_sequential/` and the task's `REPAIR_PLAN_20260926.md`.
Earlier comparison videos and verdicts above remain historical observations.

- scan_20 fixes AStar discovery and queue bookkeeping; scan_21 makes search
  and seed use the same complete segment predicate. Native regression and
  full Foxy builds passed; these changes alone did not produce a moving spline.
- scan_22 adds tracker-only subtraction against the pinned static Building
  PCD and separate full physical ground. Raw SCAN clouds are unchanged.
  All 562 frames across the two recorded placements match the installed ROS
  tracker output.
- scan_23 bounds same-level support association using the existing step limit.
  No formerly blocked/Unknown ground record becomes traversable.
- `stand_scan23_tracker_right_v1` is an actual 20.08-second standing simulator
  run with 201 ready RTX sweeps and 99 nonempty, single-ID track snapshots.
  The first track follows motion by 0.20 seconds. No navigation command is
  admitted, no nonfoot contact is observed, and there is no reset or pose
  injection. The real video is
  `output/2026-09-26_stair_human/stair_tracker_right_fixed_stand.mp4`, SHA-256
  `1eb458c52da8461946ee604f3921bc2af2c73410dfc40d5bd49bbdce6953eead`.
  It establishes standing tracking, not successful navigation.
- scan_24 adds complete final/remaining sampled spline coverage. Native tests
  and its Foxy build pass, but no accepted moving curve has yet exercised the
  full gate in the actual scene.
- Source-verified V12 height semantics separate spawn 0.35 m from locomotion
  reference 0.30 m. Paired native-PCT/SCAN replays remove search failures with
  the corrected reference but still reject seed edges; neither publishes a
  moving spline. See `step6_body_reference/PAIRED_RESULT.json`.
- scan_25 fixes the exact endpoint contract. Native tests, full Foxy build and
  replay pass their gates; the trace confirms a9.10-degree heading change from
  the old endpoint overwrite. All162 recorded seed checks then pass.
- scan_26 preserves seed corners during resampling. Actual-map chains pass,
  while the original curve initialization/optimization remains infeasible.
- scan_27 fixes current-point rebound constraint validity and terminates empty
  rebound repair. Ten native Foxy cases and complete CPU failure-path evidence
  pass; this alone does not produce a usable curve.
- scan_28 initializes hard endpoint PVA and native-limit-derived timing before
  original optimization. Eight native cases, independent review, complete build
  and462-file install identity pass. Corrected-frame CPU replay receives one
  moving cubic, with93.223s duration, all9,324 collision samples clear, original
  optimization success, and start world-velocity residual5.04e-11m/s. See
  `step12_timed_initialization/RUNTIME_RESULT.json`.
- Independent received-spline validation exposed a historical replay transport
  bug: world twist was mislabeled as body twist. Step13 adds directly recorded
  body twists from the same physics rows without changing other data. Corrected
  paired replays retain scan27 failure and scan28 success. Old artifacts remain
  preserved and must not be called exact measured-world PVA continuity.
- `walk_scan28_height030_right_v1` is the latest live trial:29.08s simulation,
  75 search failures before seed validation, zero motion commands, no nonfoot
  contact and no reset/pose injection. All49 returned artifact hashes match.
  The effective cap is35s with driver cancellation at27s; the inherited
  request metadata45s is not the actual limit. Its decoded29.12s video is
  `output/2026-09-26_stair_human/stair_scan28_right_live_no_navigation.mp4`,
  SHA-256 `84f66b834e63dde4bd1921b8cdce5014e5501b01808d8006d9274962f8a86f02`.
  This remains a failed navigation trial. Fresh-input CPU replay also fails
  search, so step14 investigates observation coverage before further changes.

- Step14 isolates a terminal-connection restriction on the fresh input: a
  0.154980m segment from a reached node passes the original collision predicate,
  while both candidates inside the old0.10m radius fail. Same-time diagnostic
  evidence is recorded; the original diagnostic search still returns failure.
- scan_29 adds cost-ordered longer terminal checks only after strict search
  exhaustion, using the original complete predicate and total0.2s budget.
  Twelve native cases, full build and462-file identity pass. Old accepted-input
  replay still produces identical control points and knots. Fresh-input replay
  now passes63 seed chains but the final full-curve gate rejects all63, with
  zero moving publication. This is graph-repair evidence, not live acceptance.
  Step16 examines the first rejected curve and exact footprint. The latest real
  video remains the failed scan28 live trial above.

- Step16 same-time diagnostics identify footprint-heading/support conflicts in
  both timed initial and final curves. scan_30 unifies optimizer and manager
  full-curve checks; seven native two-stage fixture groups, full build, review
  and paired CPU runs pass their declared gates. Fresh input remains blocked:
  168 repair attempts add zero valid paired direction constraints. Old accepted
  controls/knots remain unchanged. Step18 diagnoses failed guidance endpoints;
  no new live candidate has been admitted.

An earlier remote diagnostic build was rejected before execution by automatic
approval review because explicit source-transfer authorization to gpu5070ti was
not recognized. Dr Sun subsequently replied “授权”, explicitly approving the
destination and bounded execution. The original denial is preserved in
`step7_exact_endpoint/REMOTE_APPROVAL_BLOCK.json`. The existing
scan24 height-corrected package remains unexecuted; the later scan28 trial above
was executed under that authorization. A4 is still open.
# 2026-09-26 archive continuation notice

The latest real video remains `walk_scan28_height030_right_v1`: standing,
zero moving curves and zero motion commands. Subsequent scan29–32 changes have
paired CPU replay evidence only. scan33 passes native tests, review and full
build, but installation identity, real optimizer replay and live video have
not run. Dr Sun reported server shutdown and requested archival; retries stopped.
See [current handoff](../../../handoffs/2026-09-26_scan_stair_handoff.md).
