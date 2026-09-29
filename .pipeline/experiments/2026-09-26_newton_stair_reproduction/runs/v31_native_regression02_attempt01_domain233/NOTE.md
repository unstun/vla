# Failed first start of runs/v31_native_regression02 (not a result)

This was the first start of `runs/v31_native_regression02`, the first
candidate's (scan63) native regression rerun alone on the Docker VM. It is
not the paired A* timing control, which is
`runs/v31_regression_timing_control01`.

- **What failed:** `request.json` here set `ROS_DOMAIN_ID=233`. Fast DDS
  rejects domain IDs above 232, so the first probe (`v26`) exited at start-up
  ("Calculated port number is too high"; `v26.log`).
- **Result:** `inside.sh` stopped under `set -e` (`execution.json`: exit 1,
  73 s including the probe build). No planner ran.
- **Rerun:** `runs/v31_native_regression02`, with `ROS_DOMAIN_ID=232`, the
  value `runs/v31_native_regression01` used.

`probe_build/` is this attempt's CMake tree (local only).

Corrected on 2026-09-28: the first version of this note called the run a
"timing control" (first independent review, N8).
