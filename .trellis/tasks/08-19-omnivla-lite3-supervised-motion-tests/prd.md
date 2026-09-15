# PRD: Staged supervised Lite3 motion tests

## Goal

After all preceding gates pass, evaluate guarded VLA navigation on Lite3 in a
controlled environment while Dr Sun retains immediate handheld authority.

## Requirements

- Begin with stationary shadow mode, then suspended/support tests if applicable,
  then a bounded ground-motion test in a cleared area.
- Freeze exact speed, distance, duration, scene, command, timeout, stop, and
  rollback rules before each run.
- Assign one operator to the handheld and one observer to robot/obstacle
  clearance; keep the physical/native emergency mechanism available.
- Log camera, language, VLA trajectory, safety verdict, arbiter state, body
  command, robot state, intervention, and stop latency on one run timeline.
- Stop immediately on stale data, safety rejection, unexpected motion,
  communication loss, or human intervention.

## Acceptance criteria

- [ ] All prerequisite child tasks have explicit human pass decisions.
- [ ] Dr Sun gives a fresh explicit real-motion authorization after reviewing
      the run sheet.
- [ ] The first ground run stays within frozen bounds and demonstrates tested
      handheld takeover and stop.
- [ ] Failures and interventions are retained and reported; one successful run
      is not called general navigation validation.

## Out of scope

- Unattended operation, high speed, uncontrolled crowds, narrow hard obstacles,
  or forest deployment in the first motion stage.
