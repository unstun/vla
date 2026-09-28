# v12 results

Two original 66-scan native continuation replays agree: target admitted and a
short continuation passes full collision and boundary PVA checks. No-progress,
out-of-map and stale-input negatives pass. The environment/search source is
byte-identical to v10, whose eight measured obstacle cases pass, including the
low box.

Physical `v12_building_route01` progresses past the old stop but aborts around
18.7 simulation seconds. Docker emits an OOM event and SCAN exits killed;
subsequent ZMQ receive and final-state copyback fail. No arrival, final PD hold,
full navigation or successful-copyback claim is made. Original records remain.
See `audits/2026-09-27_v12_process_exit/` for the primary Docker events and
original-input investigation.
