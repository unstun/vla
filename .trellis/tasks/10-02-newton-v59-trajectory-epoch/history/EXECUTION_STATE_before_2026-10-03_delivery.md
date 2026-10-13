# Current execution state

Stage: experiment + analysis. Dr Sun requested repair of the v57 post-70-second
anomaly and then explicitly said to wait for gpu5070ti's other evaluation.
Continue inline; no delegation. Preserve frozen versions and all v48 safety,
goal/yaw/dynamics/stop rules. No v49 solve budgets or cancellation mechanics.

## Completed v58 component repair

- Parent v57, native `scan79_goal_endpoint_evidence_v58`.
- Five native search/evidence files changed; manager/FSM/controller and all
  configuration are exact parent. Conservative, current endpoint evidence:
  a potentially observed reflected front/rear voxel pair retains search;
  remote all-unknown endpoints cannot pass the existing footprint query.
  Recompute every call; never cache an admission verdict.
- Build02 and full contracts02 pass: 35 native, 64 cache, both 47-check warm
  fixtures, endpoint evidence, goal, freshness, physical-floor and backend gates.
- Paired replay02: 20 states, 80 calls, exact return/path outcomes. All 12
  formerly expanding states pruned. Maximum goal search 45.128580 -> 0.272144 ms
  (99.39696%). These are component results, not live Hz.
- First optimistic implementation and tests/replay01 are retained. Its three
  remaining expensive states were eliminated before freeze by the reflected
  pair test and exact query Z. v58 is now frozen: 7,572 source entries, 47
  copied delta files. Actual launch source/install/qualification/asset gate passes.
- Live `v58_realtime_trial01` did NOT start physics: preflight found another
  Isaac evaluation, PID573497, using 15,488 MiB. Preserve its preflight record.
  Next v58 live attempt is **02**, using the existing frozen launcher.
- Concurrent Isaac job began after the initial idle check and overlapped at
  least some component work. Disclose the load caveat for timings; repeat the
  paired replay with unchanged source when the host is free if needed.

## v59 timing repair in progress

- Parent frozen v58; native `scan80_trajectory_epoch_v59`; FROZEN and component-qualified.
- Three native files: manager header/source and controller receipt callback.
  Manager checks the previous curve, sampled time and exact sampled PVA, then
  carries that epoch through warm/native/fixed-height attempts. Already elapsed
  output curves cannot be committed; no wall solve limit or new stop reason.
  Controller consumes elapsed time once on receipt; existing subsequent
  incremental timing, heading/final-yaw freeze, emergency and cancellation remain.
- Actual-parent controller regression passes as a RED reproduction at
  `versions/v59/tests/controller_red/` on gpu5070ti. 40/80/600 ms delayed curves
  reset to zero in the parent. `red_controller.py` records source hashes.
- v59 build01 PASSED in 33.38 s, source unchanged.
- Full v59 contracts01 PASSED (202.639 s, source unchanged).
  Includes 15 actual-controller checks, 10 epoch checks per native fixture, recorded-map delayed warm/cold replans, expiry rejection, and the full inherited suite. Supplemental timestamp checks also pass.
- Local `scope_verification.json` passes: 11 relevant stop/control/goal/dynamic/
  warm functions exact parent, all configuration exact, materialization exact.
- Local files are the source of truth. Remote root is `/home/sun/vla_exec/vla`.
  Worker Python `/home/sun/vla_exec/envs/newton_worker/bin/python`; prepend
  `/home/sun/vla_exec/bin` for Docker wrapper.

## Next work

1. Both versions are now frozen. Do not edit their selected source/metadata.
   v59: 7,734 source entries, 33 copied deltas, 14 compact component files
   (609,084 bytes) hash-verified; actual launch gate passes.
2. No physics started. v58 attempt01 has only a resource-preflight rejection;
   preserve it and run attempt02 when free. v59 next attempt is01.
3. Honor Dr Sun's **"just wait"** for GPU availability. Do not kill or alter the
   other evaluation. CPU qualification can continue meanwhile. Check GPU/ports/
   containers before physics; no transfers/rendering concurrent with physics.
4. Once free: v58 trial02, then v59 trial01, each 90 simulated seconds through
   its frozen `remote_trial.py` and `scripts/run_managed.py` (360 s supervisor).
   Record every attempt under its actual version and ID.
5. Analyze original remote data, compare 70-90 s goal-search cost, full-round
   tails, complete-window successful Hz, motion/pauses and tracking. v58 analysis
   scripts currently default to trial01 and must NOT be mistaken for trial02;
   those analysis helpers are not included by its freeze script, but keep an
   executed-source identity for any path-only update. Its frozen collector
   defaults to trial01, so use a new supplemental return helper for trial02.
6. Prepared common-time handover analysis: `versions/v59/analysis/handover.py`.
   Its baseline QA reproduces the original v57 trial02 85-90 s result exactly
   (73 matches, median 0.048679399 m, max 0.080892414 m). the old v57 phase script
   assumes the new curve origin equals publication time. Parse the new
   `V59_TRAJECTORY_EPOCH` marker for publication time; compare old/new PVA at the
   same instant and distinguish reoptimized geometry from timestamp backsteps.
   Recorder events also have `clock_ns`, but observer receipt is not the exact
   internal controller receipt time. Keep that evidence boundary explicit.
7. Update comparison plot and one review MP4, verify full decode and exact state
   provenance, return only compact evidence/plots/video. Raw logs/NPZ/builds stay
   on gpu5070ti. Preserve original goal/yaw/PVA/safety and stop semantics.
8. Update results/spec/task/journal. Main 30 Hz/full-route acceptance remains
   open; do not promote component passes or a new version into live acceptance.

No commits made. Worktree contains unrelated dirty files; no broad staging.
An existing `.git/index.lock` was recorded earlier; do not remove it blindly.

## Ready execution commands

Once gpu5070ti has no other compute process and no conflicting container/ports:

1. Worker Python `versions/v58/remote_trial.py --attempt 2`.
2. Worker Python `versions/v59/remote_trial.py --attempt 1`.
3. Worker Python `versions/v59/analysis/compare_versions.py --skip-plots`.
4. Worker Python `versions/v59/analysis/analyze.py`, then `motion.py`, then
   `handover.py`. These default to v58 trial02 and v59 trial01; raw rounds stay remote.
5. Return only an explicit <5 MiB compact allowlist with SHA verification, excluding
   `*_rounds.json` and bulk logs/state/build trees. Plot locally from compact tables
   with `compare_versions.py --plots-only` if remote matplotlib is absent.
6. Render v59 from original states after both physics runs: use its frozen
   `render_review.py --source-run v59_realtime_trial01` through `scripts/run_managed.py`,
   with a new review run ID, external deadline900 and `XDG_DATA_HOME` set to
   `/home/sun/vla_exec/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction/runtime/render_env`.
   Original font/dependencies are already present from the verified v57 render.
7. Verify source/install identities after physics, full video decode, version/state
   hashes and three preview frames; preserve failures. Update result/acceptance files
   separately from manifests. No automatic acceptance of 30 Hz/full arrival.

CPU builds/tests are finished; no owned remote process is running.
Latest confirmed other GPU process: PID573497, Isaac evaluation, 15,488 MiB.
Dr Sun's last instruction: **just wait**; do not interrupt that process.

## Live validation resumed after GPU release

GPU became free. v58 trial02 launched and reached its recording bound; its
remote_trial supervisor/retention is still running in exec session54179. Do not
start another simulation until it exits and containers/ports are clear. Next
v59 trial01. Heartbeat `finish-vla-planner-validation-when-gpu-is-free` is ACTIVE
every10 minutes as a fallback; pause it after delivering results or an actionable
validation failure. It must not duplicate any active/completed run. Six further
compact launch/clock/baseline-analysis files (12,724 bytes) hash-verified locally.

## Both physical recordings completed

v58 trial02 exited0 in194.094s; v59 trial01 exited0 in193.504s; both owned
containers cleaned up. Do not launch them again. Analysis `compare_versions.py
--skip-plots` completed and verifies both frozen source/install trees and raw
archives. Full navigation-window results: v58 success27.53428Hz, median2.053ms,
P9512.789ms, max659.526ms, path55.188m, no >1s pause; v59 success26.42581Hz,
median1.964ms, P9512.913ms, max1236.709ms, path55.042m, one1.0994s pause.
Neither meets30Hz. Do not declare overall repair acceptance.

Post70 stage analysis initially raised StopIteration because it assumed an
unpruned expensive goal search remained. The postprocessing script now handles
absence with None; old script preserved in analysis/history. Frozen runtime
unchanged. Sync in session39517; after it completes rerun analyze.py, motion.py,
handover.py and inspect remaining full-run tail locations/stages. Need return
compact actual physical results, update figures, render/verify video, update
results and acceptance, and pause the heartbeat before final delivery. The
analysis and source gate complete; physical run sessions54179 and92711 are closed.
