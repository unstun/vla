# v47: reuse the last feasible local planning window

Stage: experiment + analysis. Authorized by Dr Sun on 2026-10-01, including
gpu5070ti testing. No new Trellis task. Version parent v46; navigation parent
v45; native source parent v44 (`scan69_shared_attempt_cache_v44`).

## Change boundary

Only intermediate reference-target selection changes. The FSM remembers the
route-time span of a window accepted by the complete native planner. On the
next cycle it advances that span from the current measured route projection,
capped by the ordinary nominal target and current frontier. After measured
progress of half that span, it tries one existing sampling increment of growth.
This is a hint, never a cached collision verdict or a reused trajectory.

The hint is invalidated by route regeneration, P2B identity/map changes, changed
goal, backward/large projection jumps, regressed/expired simulation time,
invalid current endpoint/start evidence, unsuccessful planning, and safety or
emergency stop. Current occupancy, bounds, support and freshness are queried
again. Hint-selected shorter targets use the existing prefix convention of zero
terminal velocity. The normal optimizer, PVA, full-curve collision, dynamics,
minimum-cruise, final XYZ/yaw, controller and stop contracts are unchanged.

Owned implementation paths: `runtime/scan70_feasible_window_v47/src/plan_manage/`
FSM source/header, plus version-specific launch wiring and tests here. No
optimizer warm start, shared deadline, cross-callback cache or global-route fix.

## Verification and execution

1. Compile on gpu5070ti from SHA-verified local source; compare native files to
   v44 and require all files outside the FSM pair to remain byte-identical.
2. Run the existing 34 native goal/timing/stop and 48 cache checks, recorded
   geometry replays, and new hint lifecycle/freshness/goal tests against the real
   compiled FSM. Preserve each attempt, including failures.
3. Select v45 log rounds for first success, shorter-prefix recovery, fixed-height
   recovery, slow-tail and invalid-curve cases. Keep recorded log coverage distinct
   from executable replay coverage if complete serialized inputs are unavailable.
4. Freeze source and installation hashes before the full-stack run. Run the same
   Building route, original physics/PD/policy/LiDAR and v45 CPU quota, bounded to
   90 native seconds and 360 wall seconds. Do not actuate hardware.
5. Return raw evidence and verify SHA-256 locally. Report measured local,
   controller/global rates, median/P95/P99/max solve time, overruns/skipped slots,
   retry/hint counts, route progress, pauses, terminal state and simulation RTF.

Local source of truth: `/Users/sun/tongbu/study/phdproject/vla`.
Execution copy: `/home/sun/vla_exec/vla` on gpu5070ti. Sync only task-owned paths;
all runtime source/install hashes must match before launch. Results and logs
return under this version and an immutable `runs/v47_realtime_trial01/`.

The 30 Hz requirement is assessed on the complete measured loop, not component
timing or the timer setting. Report the exact achieved rate and deadline misses;
a shortened window that increases pauses or loses progress is not accepted as
an optimization. Full Building arrival remains a separate gate. If interrupted,
retain partial artifacts and make no frequency or navigation acceptance claim.
