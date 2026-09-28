# Archived at v27 on2026-09-28

Authoritative continuation: [archive handoff](2026-09-28_newton_v27_archive/README.md).
Execution stopped at user request. v27 physical trial crashed; v28 not created.
The earlier progress notes below are historical, not current acceptance.

---

# Continuation update: v26 repaired config; v27 native candidate

Stage: experiment + analysis. Current frozen source v26; complete-floor physical
acceptance remains false. Source of truth is this VLA repository. No real-robot
actuation or sibling edits are authorized by this continuation.

- v24 short stair reached native arrived_after_quiescence at~73s, XY error.200m.
  Final PD handoff incomplete at mid-stair goal. Actual89.92s video delivered:
  output/2026-09-27_lite3_versions/v24_stair_arrival.mp4.
- v25 restored historical complete-floor route profile but loader discarded
  explicit pct_layer null; live145point17.244m wrong-floor path; odom_stale.
- v26 fixes that nullable field only. Seven loader tests and six actual TCP/native
  controls pass. Live v26_historical_full02 confirms631point~73.41m correct-floor
  route.110.731simseconds, one movingcurve, then no progress; diagnostic abort
  through existing driver cancel/failure flow. Zero reconnect/protocol/IO errors,
  verified stop/copyback; final PD is at start, not successful arrival.
- v26 captured30.005s/189scan fresh-state native replay still fails optimizer
  despite start/target/direct segment clear. AStar seed has backwards detour.
  Evidence: audits/2026-09-27_v26_frontier/{baseline.json,baseline.log,inputs}.
- v27 candidate scan59_seed_shortcut_v27 preserves AStar/edge validation and
  adapts OMPL1.7.0 reduceVertices verified direct connector before original
  sampler and all final gates. Build passes, native regression underway in
  runs/v27_native_regression01. Not frozen/physically accepted yet.
- Hold and scheduling failures remain separately open. A constant emergency
  spline still produces position feedback commands in current controller;
  therefore do not skip its safety checks on the assumption it is zero control.
  Single-threaded planning can let measured-body age exceed100ms, making the
  legal hold's yaw fallback invalid. No threshold/hold/executor edits in v27.

---

# Active continuation update: v24 frozen (2026-09-28 UTC)

Stage remains experiment + analysis. User requested continued repair, one logical
change per integer version, careful historical full-building comparison, and
actual video. Work is local simulation only; no hardware actuation or training.
No complete Newton stair/full-building acceptance has been obtained.

- Historical Isaac native_full02 is a genuine 74.06m XY physical completion of
  the same Building, with a 73.2373m/631-point PCT route. See the full_building
  comparison audit. Current `building_full` still means full geometry with a
  short 5m stair goal, not the historical route.
- v18 fixes isolated rejected clock samples; v19 restores original float32 map
  elevations; v20 repairs the Building replay camera. Delivered ordinary v19
  failure video: output/2026-09-27_lite3_versions/v19_building_v20_camera.mp4.
- v21 adds a separately validated floor-evidence source; actual physics reaches
  2.558m then native exhaustion. v22 densifies only that offline static evidence,
  using pinned Trimesh and the unchanged PCT generator; density alone fails.
- v23 selects the explicit qualified source for the complete existing floor and
  paired-tread riser rule. Seven stopped-state continuations and all eight
  unmapped fixtures pass. Physical v23_building_route01 instead stops after
  1.208m, reaches89.962s bound, has no terminal/driver result. Measured stillness
  and copyback verify; no transport errors. The review's missing-driver crash is
  retained; a diagnostic copy marks the missing artifact as failed.
- Actual v23 30s fixture has189 original paired scans. All front/rear occupied
  contributors are terrain-only, but the forward terrain height gate rejects
  the straddled posture: body z.482619, center floor.194552 (clearance.288067),
  forward floor.330916 (apparent clearance.151703<.18). This is a local
  per-cylinder height-gate wiring issue, not the original SCAN occupancy rule.
- v24 is prepared under versions/v24 and runtime/scan58_body_support_v24. It
  preserves raw query XYZ/bounds and all thresholds, validates the body center
  against the original height gate, associates each footprint sample through
  unscored original layers, then requires its same-index scored layer. Closer
  Unknown/Unsupported, equal-distance ambiguity and delta>=.26 stay blocked.
  Only terrain Query.z changes. Review found no remaining source blocker after
  strengthening red/green tests and diagnostic wiring. Final scan58 build passed and v24 is frozen;
  runs/v24_native_regression01 is running, followed by physical validation.
- Separately, the v23 safety callback repeatedly considers an expired emergency
  hold while in GEN_NEW_TRAJ. It can cycle states and plan from an old hold;
  this did not explain the initial moving-curve stops and remains a separate
  potential repair. Do not disable safety as a shortcut.
- Known mapped13cm low-protrusion policy remains an unanswered user question.
  Existing baseline already treated it as terrain; eight unmapped fixtures do
  not establish universal box avoidance. Current physical trial has no added
  objects and can proceed under prior authorization.

Do not overwrite frozen versions or prior runs. v19-v23 snapshots and current
v23 source were rehashed successfully. Native build attempts are immutable;
scan57 was a pre-review build, scan58 contains final v24 source. No commit was
made. Preserve unrelated dirty worktree changes. Only live production changes
require the next version; diagnostic fixtures are separate audited evidence.

---

# Historical v15 repair notes (superseded by the active update above)

User request: repair the regression against the historical stair/full-building
success. Continue locally; no physical robot, remote actuation or training.
Chinese interaction starts with `Dr Sun,`. Each logical production change gets
an integer version; preserve every frozen source snapshot. Do not call this
repair complete until the physical route and final PD stop are demonstrated.

## Source and versions

E2 is `.pipeline/experiments/2026-09-26_newton_stair_reproduction`.
Version index/current metadata live under `E2/versions`. Latest frozen version
is v15; next integer is v16, not yet assigned. Main session owns edits.

- v8: ETH missing-neighbor handling; absent central support still blocks.
- v9: historical .10 m positive Z inflation; rejected because it misses low box.
- v10 branches from v8: separate raw ground elevations from scored support.
- v11: matching FSM exhaustion closes gate; actual runtime receiver is
  runtime_sources/backend_ros/p2b_backend_ros/node.py.
- v12: target collision heading uses planned start, consistent with search.
- v13: remove discarded legacy seed initializer; repeated expired-curve calls
  pass the same bound that aborts v12. Physical OOM no longer reproduced.
- v14: admission waits require the requested consumer even for rejection.
  The actual v13 fault/hold message order reproduces red-to-green behavior.
- v15: raw risers bounded by associated mapped treads; no collision dimension,
  obstacle-history, unknown or freshness relaxation. Native build scan52_riser_ground_v15.

All v15 original 66/67-scan continuations pass PVA/full-curve checks (2–3 m
targets), and all eight measured generic obstacle cases preserve v10 outcomes.
Seven stop-flow tests, four receiver tests and four consumer-order tests pass.
Each version has PLAN, frozen manifest/source, patch and result evidence.
The shared receiver and setup/runtime_sources.json receipt are the only existing
production source paths modified through v15; native sources use separate copies.

## Actual failure still being repaired

`runs/v15_building_route01` ran 89.962 s, net forward 1.058 m, rise .079 m, then
held at approximately [-5.21,5.05,.477]. Gate remained open, no arrival/terminal.
Applied-state copyback verified; 45 rejected-clock-observation reconnects remain
recorded. Diagnostic video is an ordinary file at
`output/2026-09-27_lite3_versions/v15_building_test.mp4`, full decode passed,
24 s / 300 frames; source/version hashes are in versions/v15/video_receipt.json.

`audits/2026-09-27_v15_moving_frontier/inputs` freezes the exact 189 scans, paired
poses, route and last stop spline at clock 30000141144 ns.
Start=[-5.218457,5.054320,.480949], target=[-5.365330,1.698279,1.062114].
Native exact replay: start and target free, target selection true, continuation
false. Last committed planning end is 2.485040669994; actual projection is 1.05.

Three local prefix candidates 2.7118358/1.8809179/1.4654589 are all occupied
under start-to-candidate heading, and exhaust their shared 3-proposal budget
before any shorter candidate reaches manager. The remaining two initialization
flag retries repeat the same work; flags no longer affect mandatory graph seed.
Do not claim this redundancy is the new root cause; old seed was overwritten too.

Raw hits show a ground cell .417236 with four neighbors .467285; true tread
.467279 exceeds the 5 cm band by only 43 micrometers. Other edge cells have
missing low-floor support. Preserve these as evidence; do not waive unknown.

Diagnostic ablations (not promoted): native 3D search, .051 m raw band, and
historical .25 m horizontal radius individually fail. 3D + band gives a fully
checked 70-node seed but optimization fails; non-exact optimizer AStar moves
endpoints out of pool. Radius-only admits one short target, but full curve
collision rejects it. See moving_ablation and radius_ablation audit directories.

## Current next diagnostic

Existing authorized read-only reviewer stair_planner_cause_review confirmed the
short-prefix prefilter behavior. Recommended reusing the already implemented
findGoalNeighborhoodPath, which admits only reached nodes with selection and
stopped-endpoint heading checks. It is currently used only near the global goal.

`audits/2026-09-27_v15_local_neighborhood02` calls it on each exact blocked prefix
with tolerance min(existing 1 m, half candidate XY distance), checks actual
forward translation/projection, then runs the unchanged full manager plus PVA
and full-curve checks. Production v15 remains unchanged. First diagnostic
compile failed only because the native evaluator needs a mutable spline copy;
that attempt is preserved in the directory without the 02 suffix.

## Later full route

Historical Isaac native_full02 succeeded: 74.06 m actual travel, 98.08 s,
3.77 cm goal error, same Building/map. The original video and source comparison
are indexed in audits/2026-09-27_full_building_comparison/REPORT.md.
`--scene building_full` currently selects full geometry but a 5 m stair goal.
A separately versioned historical route profile is still needed after short
stairs pass. Original spawn [-5.5453147888,6.013188839,.0580444336], yaw
-1.3258179441604312; goal ground [1.9546852006,-2.9868112221,4.5330305099].
Existing PCT automatic layer mode None produces 631 points / 73.237319626 m
and correct endpoint height. Fixed layer1 puts the goal almost3 m too low.
See audits/2026-09-27_full_route_preflight/attempt02. Do not invent a layer selector.

No repair-turn commits have been made yet. Preserve unrelated dirty work and
review only owned staged paths. All original A4 moving-person Isaac criteria
remain open. Do not update global Codex memories without explicit user request.
