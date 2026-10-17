# Lead review: `scan_07` ETH-style SCAN candidate

Date: 2026-09-23. Stage: experiment and analysis.

## Decision

`scan_07` is accepted as a **buildable source candidate**. It is not accepted as
a completed SCAN stair/pedestrian integration or a validated avoidance result.
The next runtime gate needs both a real `/pct_tomogram` producer in the P2B
launch and a provenance-labelled `/tracked_person_snapshot` producer. The
current pilot launches neither. The missing-input behavior is fail closed.

## Review evidence

- The exact ETH `StepFilter.cpp` at commit
  `14d24c059e1c43466aadf328280adf6394d78039` is preserved under
  `references/upstream/2026-09-23_eth_stepfilter_reference/`, with SHA-256
  `cdcf18ef0b6396770ea779fd03683b757ddd78640bc4817205377713186920f2`
  and its BSD-style license. The local C++ adapts the original two-pass
  max-minus-min and critical-cell score. Its sparse/multilevel handling and
  0.26 m V12 hard gate are local changes; numerical fixtures passed.
- `reactive_stair/test_materialize_scan_07.py -v`: three tests passed. The
  materializer verifies the built `scan_06` source identity, unchanged copied
  source files, changed-file hashes, and the ETH reference hash. The accepted
  `scan_04`, `scan_06`, and frozen `planner.yaml` were not edited.
- `test_eth_step_score_adaptation.cpp` compiled with `-Werror` and passed.
  The fixture covers flat tread interiors, 0.18 m edges, a 0.50 m box, a thin
  wall, missing cells, multiple elevation layers, and ETH formula values.
- `python3 build_scan.py scan_07` passed in the pinned Foxy image
  `e4aa715467b93f20a9d9cdbb6a1dbd0d3c8c1e033e7792f2d889cba03db227d8`:
  six packages finished in 52.5 s; before/after source identity matched.
  The full command, logs, and manifest are in `builds/scan_07/`.
- `python3 capture_install_identity.py scan_07` recorded 425 installed files;
  installed identity SHA-256
  `19a71f283e101844f2af8dd130c2bf2ff4f0a395f5d207e57991b6fbc912f358`.
  Existing compiler warnings are present; the build has no errors.
- A bounded, CPU-only Foxy process startup smoke ran `scan_planner_node` for
  10 seconds from that installed workspace. It initialized to `INIT` and
  waited for odometry/goal, then the timeout sent SIGINT; no initialization
  exception occurred. Logs and the exact command are in
  `.pipeline/experiments/2026-09-23_scan_reactive_stair/scan07_startup_probe/`.
  This did not exercise either new ROS callback.
- A separate CPU-only PCT ROS probe published 86,775 selectable cells from
  pinned `inputs/new_building.pickle`. Its logs are in
  `.pipeline/experiments/2026-09-23_scan_reactive_stair/pct_tomogram_probe/`.
  The integrated `isaac_runner/run_two_goal_pilot.py` starts the socket PCT
  worker, not this ROS publisher.
- An offline route probe of the pinned `reference_path.map.yaml` stairs
  sampled 100 points along x=-5.5 m. Ninety-eight had selected supported
  ground within 0.20 m and 0.12 m height tolerance. At y=0.3 m and -0.6 m,
  the selected ground was present but approximately 0.13 m above the
  interpolated reference-path height. This is a route-height compatibility
  check, not a SCAN route or locomotion test; the source and full output are
  in `.pipeline/experiments/2026-09-23_scan_reactive_stair/`.

## Open gates

1. Wire a labelled current-person source. `scan_07` provides only the typed
   consumer. A LiDAR clustering source must be reviewed as a candidate
   detector/tracker; simulator actor poses would be an oracle smoke only.
   The current collision contract uses XY person radius and discards the
   message's center z, so a person on an upper floor can conservatively block
   a lower-floor query at the same XY. Floor-aware avoidance needs a measured
   vertical extent and a separate test; the present implementation may yield
   on multilevel overlap.
2. Run PCT publication and the SCAN subscriber together in the same pilot,
   then measure callback time, 50 ms safety-loop timing, map-frame alignment,
   and freshness behavior. The standalone PCT probe does not establish this.
   The pilot's frozen planner configuration uses simulation time; the first
   standalone PCT probe used wall time. Its one-shot startup publication cannot
   be used unchanged as a valid pilot terrain timestamp. A zero-clock probe
   logged the PCT publication but its topic echo timed out, so the actual
   one-shot stamp remains unmeasured. The next publisher must explicitly wait
   for a nonzero simulation clock and verify the delivered stamp.
3. Check whether the intended stair run uses the example reference path; if
   so, resolve its two height mismatches. Then run a stair-route episode with
   a moving tracked person. Report contact, fall, route completion or safe
   yield, and sensor-to-correction timing. No such episode exists yet.

Claim labels: ETH **surveyed**; `scan_07` local adaptation **implemented and
built**; live behavior **not integrated**; pedestrian avoidance **not
validated**.
