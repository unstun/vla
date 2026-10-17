# Implementation plan

Do this only after Dr Sun approves the planning summary. No GPU run before
the local tests pass.

## Checklist

1. Add `isaac_runner/run_unmapped_box_avoid.py`.
   - Build the package the way `run_two_goal_pilot.py` does: patched runner,
     PCT runtime, backend, Foxy bridge, `scan_04` hash gate.
   - Runner argv adds `--unmapped-box lidar` and
     `--lidar-pattern-mode livox_mid360`, and stages the Livox assets.
   - Driver posts one `/goal` for `goal-b`, then the finish request when the
     dog arrives or the sim cap hits. No `/cancel`, no `goal-a`.
   - Leave `run_two_goal_pilot.py` and `pilot.json` unchanged.
2. Local tests, no Isaac:
   - argv contains the two flags above
   - driver source posts `goal-b` once and does not post `/cancel`
   - source `planner.yaml` SHA stays
     `42a265a35cefb69eae43896acdd13780d1a7bd36a874b2f3aae967376b6e435e`
   - a fixture route through the box footprint is classified as crossing;
     a torso sample inside the frozen AABB is classified as overlap
3. Idle-check gpu5070ti (no Isaac, GPU free, ethernet up).
4. Prepare the package, then one `--execute` with the existing lead
   authorization flag. Sim cap 45 s, wall cap 1200 s.
5. Write
   `.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/livox_mid360_stand_probe/RESULT_unmapped_box_avoid.md`
   with the run id, the three AC2 numbers, pass/fail/incomplete, and the
   `planner.yaml` source hash. Do not edit 09-20 AC1.

## Validation

```bash
python3 -m unittest isaac_runner/test_run_unmapped_box_avoid.py
```

Run from `.pipeline/experiments/2026-09-16_pi_cortex_harnessvln` if that is
how the sibling two-goal tests are invoked. Match the existing test style.

## Risky files

- New launcher and its test only.
- Generated run copy of `planner.yaml` (adds `p2b_mode` only).
- Do not write the pinned baseline, `pilot.json`, or `scan_04` source.

## Stop conditions

- SCAN hash gate fails: do not start Isaac.
- GPU or port busy: do not start.
- Dog torso intersects the box, SCAN emergency-stops, or 45 s ends away from
  `goal-b`: record fail or incomplete. Do not retune and rerun in the same
  session.
