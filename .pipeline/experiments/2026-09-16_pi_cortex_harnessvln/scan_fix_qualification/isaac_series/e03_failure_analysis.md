---
origin: ai_with_source_check
reviewed: false
date: 2026-09-17
run: two_goal_20260917T090126Z_scanfix_e03 (5070 Ti host, scan_04)
---

# Episode 3: goal-B stop dwell failed (40/41)

## Result

- Failed check: `two_goal_20260917T090126Z_scanfix_e03-goal-b:raw_physics_stop_dwell`. The other 40 checks passed.
- The integrity checks passed: returned hashes match, the SCAN hash gate passed before and after, and the walk
  review rendered.
- The part the fix is about worked: the cancel terminal was at x = -1.1127 and the still-confirmed pose, where the
  resubmitted plan started, at x = -1.1130. That is inside the original build's failure band [-1.19, -1.11] m, 3 mm
  from its edge; the native replay of the original build rejects this plan 3/3 (1.529 m/s^2). The resubmitted goal A
  was planned and reached (0.189 m), and goal B was reached (0.177 m).

## What the review measured

`review_two_goal.py` walks back from the goal-B terminal through every 0.02 s physics record in `metrics.jsonl` and
needs 1.0 s of consecutive "still" samples (command norm <= 0.01, speed <= 0.10 m/s, |yaw rate| <= 0.15 rad/s;
`inputs/pilot.json`).

- Command went to zero at sim 14.06 s; speed fell below 0.10 m/s at 14.18 s.
- At sim 14.30 s one sample had yaw rate -0.1595 rad/s (limit 0.15). All other samples from 14.18 s to the terminal
  are still.
- The terminal's last physics record is at sim 15.20 s, so the still window is 14.32-15.20 s = 0.88 s (45 samples).

## Why the backend still declared arrival

The backend's dwell check (`backend_adapter/backend_adapter/applied_evidence.py`, `StopEvidenceWindow.observe`)
uses the same three limits and a 1.0 s sim-time window. It reads the single, overwritten snapshot file
`external_episode/current_command.json` in a polling loop (`backend_ros/p2b_backend_ros/runtime.py` `_stop_worker`,
0.02 s sleep). Snapshots written between two polls are never seen.

The backend confirmed at a snapshot no later than sim 15.20 s. A 1.0 s window at that point needs its first still
sample at or before 14.20 s. If the backend had read the 14.30 s snapshot, the window would have restarted at 14.32 s
or later (`_reset_continuity`). So the backend did not read that snapshot: it declared arrival from sampled
evidence that missed the one out-of-limit sample. The review reads every record and is stricter by design
(its docstring: the HTTP ledger is "never sufficient proof by itself").

## Where the yaw spike comes from (Dr Sun, 2026-09-17)

Dr Sun: this is a problem in how the robot's deployment program runs the policy, which should be V12 model_149999.
An RL policy almost never stands perfectly still. Holding the stance needs a switch to a PD controller, and making
that switch smooth is very hard.

Checked against the run:
- The runner loaded `model_149999.pt` (path in `returned_artifacts/env_identity.json`), sha256 `a9d31dce…d5450`
  (`returned_artifacts/runner_output/runtime_identity.json`). This equals the frozen V12 checkpoint in
  `p2b_execution/input_manifest.json`.
- The runner keeps the V12 policy running on a zero velocity command after the stop. Each step writes the command
  into `base_velocity` and calls `wrapped.step` (`runner_output/executed_run_pct_scan_building.py`, control loop).
  No PD stance hold exists.
- So the 20 ms yaw-rate excursion is the RL policy's jitter while it stands on a zero command.

## Reading

- The failure is a locomotion-layer effect: an RL policy stands on a zero command with no PD hold. The backend's
  polling missed the excursion; the full-rate review caught it. It is downstream of SCAN and is not a planner
  rejection, collision, reset or contact.
- The same backend code ran in the Sep 16 `scan_03` runs, so this weakness predates the fix.
- Under PRD D11 this is a counted failure, not an infrastructure failure. The series continues; it stops early only
  if the next episode fails the same way.
- No threshold is changed (PRD D3). A backend change (for example reading a per-step sample log instead of the
  latest snapshot) would be a separate task for Dr Sun to open.
