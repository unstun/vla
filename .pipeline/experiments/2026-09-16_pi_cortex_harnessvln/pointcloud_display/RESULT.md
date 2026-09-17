# Live Point-Cloud Display Result

Date: 2026-09-16. Stage: experiment + analysis. Target: gpu5070ti.

The bounded GPU display and recording test succeeded. RViz actually used
`NVIDIA GeForce RTX 5070 Ti/PCIe/SSE2`, with NVIDIA driver 580.126.09, and the
host recorder used `h264_nvenc`. One active encoder session was sampled during
physics. Both point-cloud status and the global RViz status were visibly OK.
The complete-navigation acceptance criterion did **not** pass: all three new
conditions failed after cancelling and resubmitting goal A. Preserve this
distinction; the earlier accepted actual4 run is one successful pilot, not
evidence of repeatable navigation across these new trials.

## Measured comparison

Each condition executed 45 simulation seconds, including the protected
stationary tail after the navigation failure. CPU/RAM/GPU samples below cover
the active physics interval, excluding initialization and cleanup. There was
one run per condition; these are descriptive observations, not statistical
estimates or isolated renderer costs.

| Measurement | Display off | CPU RViz + libx264 | NVIDIA RViz + NVENC |
| --- | ---: | ---: | ---: |
| Physics-loop wall time (s) | 56.839 | 58.512 | 58.422 |
| Control-loop p95 (ms) | 47.571 | 48.319 | 48.308 |
| Sampled total GPU memory peak (MiB) | 7082 | 7121 | 7445 |
| Sampled total GPU utilization median (%) | 38 | 39 | 39 |
| Sampled host CPU median (%) | 14.595 | 15.470 | 15.700 |
| Sampled host used RAM median (GiB) | 10.018 | 10.298 | 10.306 |
| Telemetry drops | 0 | 0 | 0 |
| Command watchdog events | 1 | 1 | 0 |
| Control intervals above 250 ms | 1 | 1 | 1 |
| Complete two-goal navigation | Failed | Failed | Failed |

Relative to display off, GPU display plus capture increased wall time per
simulation second by 2.786%, control-loop p95 by 1.549%, and the sampled total
GPU memory peak by 363 MiB. The GPU peak was about 7.27 GiB out of the reported
16303 MiB device memory. This small cloud did not stall or exhaust the host.
The short trial does not establish long-duration or dense-map performance.

The RViz PID's median CPU use was about 4% of one core with software rendering
and 3% with NVIDIA rendering; the capture PID changed from about 6% to 4%.
These are individual PID measurements and exclude child processes such as the
cloud audit subscriber. Whole-host CPU did not decrease in this single pair.
NVENC utilization rounded to 0% in the samples despite a recorded encoder
session and a successfully encoded video; do not claim high GPU saturation.

## Display and media evidence

- Latest-only `/quad_0/cloud_raw`, BEST_EFFORT depth 1, Decay Time 0, 10 Hz
  drawing limit, 1228 x 826 captured window. No cumulative map is displayed.
- GPU condition received 450 nonempty, monotonically stamped cloud messages
  spanning 44.900 simulation seconds; median 2843 points, maximum 2858.
- `gpu_comparison.json` verifies the actual renderer, NVENC, full video decode,
  matching frozen runner/SCAN/pilot identities, clean samplers and returned
  artifact hashes. Its overall `passed` remains false because navigation failed;
  `display_recording_and_provenance_checks_passed` is true.
- `pointcloud_gpu.mp4` is a 58-second, 8,946,235-byte preview in wall time. It was
  trimmed from the raw capture to remove the long driver-wait tail, without
  speed changes or re-encoding. `preview_provenance.json` records hashes and
  the exact extraction command. The raw video and preview fully decoded.
- Lead inspected the live GPU image and preview frames at 2 and 8 seconds:
  cyan live cloud, changing geometry/position and current pose arrow are visible;
  displayed frame rate is 9-10 FPS. This is actual RViz output, not a mock-up.

## Navigation failure retained

PCT returned a valid route quickly after resubmission. SCAN received that route
but repeatedly rejected its refined trajectory at the native acceleration
feasibility check. No second spline reached the controller. The backend then
reported `initial_heartbeat_missing` and completed a protected fault stop.
The display-off condition already exhibits the same chain, so this failure
cannot be attributed to point-cloud rendering from these results. Navigation
parameters, thresholds and physics inputs were not relaxed.

Inspect each run's `returned_artifacts/logs/scan_planner_node.log`,
`closed_loop_controller.log` and `pilot_journal.json`. The independent physics
review correctly rejects the missing A/B arrivals. Resolving this repeatability
problem remains open before expanding the navigation claim.

## Source, review and cleanup

- Run IDs: `pointcloud_20260916T171400Z_off`,
  `pointcloud_20260916T172100Z_rviz`,
  `pointcloud_20260916T173400Z_rviz_gpu`.
- Returned hashes match: 38/38, 46/46 and 47/47 respectively. Execution packages
  are immutable snapshots under `runs/`; using an existing run ID selects its
  prepared source, not subsequent edits to the shared observer directory.
- GPU providers are scoped read-only mounts with hashes in
  `nvidia_runtime.json`; no NVIDIA toolkit installation or full host-library
  directory mount was used. Actual Ogre verification rejects software fallback.
- The GPU pilot's captured window was independently correlated with the sole
  RViz process, container host PID and PID namespace in its
  `window_ownership.json`. Review then strengthened future selection to an exact,
  unique title derived from the run-specific configuration filename.
- The updated window selection passed an additional actual GPU startup check
  under `qualification/pointcloud_window_20260916T174100Z/`: NVIDIA renderer,
  exact run-specific window title and no capture before physics. All 10 returned
  artifact hashes match. It did not launch Isaac or navigation.
- `final_cleanup.json` confirms all owned registered PIDs exited, no containers
  remained, all four navigation ports were free, encoder sessions returned to
  zero and device memory returned to 204 MiB. No processes are left running.

GPU is the default display profile in `run_probe.py`. Use a fresh run ID for
new source changes. `--mode off` and `--mode rviz` retain the diagnostic baseline
profiles. The local VLA repository remains the source of truth; sibling source
repositories, physical robot control and the overall in-progress task are
unchanged by this display probe.
