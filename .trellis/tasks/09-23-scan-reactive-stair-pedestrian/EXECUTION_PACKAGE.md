---
origin: lead+local
reviewed: true
date: 2026-09-23
status: dispatched
---

# Reactive stair and pedestrian SCAN candidate: execution package

## Goal and scope

- Goal: implement and locally test the new SCAN candidate's conservative
  terrain/person collision decision and a reproducible `scan_05` materializer.
- Lead / executor: GPT-6 Astra lead; GPT-6 Sol xhigh executor.
- Dispatch identity: `/root/scan_reactive_impl` (Codex subagent).
- Source of Truth: `/Users/sun/tongbu/study/phdproject/vla`.
- Authorization: Dr Sun said to try implementation and requested this model
  for coding. No physical actuation or formal training. Executor performs no
  remote run; lead owns later build and simulator gates.
- Owned paths: new files beneath
  `.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/p2b_execution/reactive_stair/`
  and, if needed, a newly materialized `p2b_execution/builds/scan_05/`.
- Frozen boundaries: `builds/scan_04/**`, `baseline_config/planner.yaml`,
  existing `step_traversability.*`, dirty `isaac_runner/**`, sibling repos,
  existing result verdicts and task docs.
- Sync Gate: local-only executor work. A later remote copy must be hash-gated
  against these local sources, and every returned result must land locally.

Read `AGENTS.md` and the task's `prd.md`, `design.md`, and `implement.md`.
You are not alone in the repository; preserve concurrent edits and do not
revert changes made by others.

## Verified context

- Accepted SCAN is `p2b_execution/builds/scan_04`; `grid_map.h` SHA-256
  `3a562e007f40dc78fd811b31f4326cf778cfb0e475a1d61fd0836eda3aaa28d4`.
- The earlier one-window helper is a local prototype only. It clears an
  inflated hit at `getInflateOccupancy` without obstacle provenance and does
  not clear wide tread interiors. Its tests are not integration evidence.
- A*, the spline optimizer, and the 50 ms safety callback call
  `GridMap::getInflateOccupancy`. Current ROS packages include
  `scan_planner_msgs`, `plan_env`, and `plan_manage`.
- ETH `StepFilter` is surveyed, not imported. Official source:
  `https://github.com/leggedrobotics/traversability_estimation/blob/master/traversability_estimation_filters/src/StepFilter.cpp`.
- Moving pedestrians provide current tracks. Do not extrapolate velocity or
  implement a predicted occupancy tube. An upstream sensor-based tracker is
  not yet pinned; an external current-track contract is acceptable for this
  coding slice if its source is explicit and untrusted/stale behavior is safe.

## Remaining work

1. Design a small collision-decision interface with separate terrain support,
   raw/nonterrain obstacle, and current-pedestrian inputs. Person occupancy
   wins; unknown/out-of-map stays blocked. Handle full tread interiors. Avoid
   per-query full vertical-column scans if possible.
2. Implement local pure logic and meaningful negative tests: supported stair,
   flat, tall box, thin wall, a person on a traversable tread, track freshness,
   unknown support, multiple current tracks, no trajectory prediction.
3. Implement a hash-gated candidate materializer based on `scan_04`. Add a
   typed current-track ROS input if it is feasible within the owned overlay;
   otherwise return the exact interface or build blocker, with no fake claim.
4. Run local tests and record exact commands and raw outcomes. Preserve source
   hashes. Do not run on gpu5070ti or change the experiment's acceptance bars.

Repair ordinary errors within these paths. Return any consequential design
change to the lead before widening scope.

## Return

Provide the owned diff, commands and outcomes, exact source paths, source
hashes, and remaining integration blockers. State commit status. The lead
will inspect the actual diff, verify negative tests, and build in Foxy before
accepting a compiled integration claim.
