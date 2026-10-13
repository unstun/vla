# v79 compact polling results

Frozen component-qualified backend change. All 23 Python/HTTP/backend tests pass;
original control and stop handler ASTs remain identical. Same retained 1.517 MB
state becomes 35.8 KB; ROS encoder mean 42.428 → 0.307 ms, maximum 83.505 →
0.833 ms under the measured load. Actual ROS callback test passes 360 compact
polls at 30 Hz, maximum callback gap 38.875 ms. Original missing-heartbeat
fault and latching remain. Full records are retained once in JSONL.

Both integrated v82 runs preserve backend heartbeat but fail continuity because
mapping becomes stale. This is not full navigation or steady 30 Hz acceptance.
See `audits/2026-10-05_safe_mapping_repair/REPORT.md` and the version's test and
benchmark receipts. v48 stays the runnable reference.
