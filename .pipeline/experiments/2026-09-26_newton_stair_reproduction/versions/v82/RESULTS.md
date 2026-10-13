# v82 integrated mapping: acceptance failed

**Frozen failed candidate; do not promote.** Eight native packages and all
component/native/recorded safety checks pass. Ten backlog cases/20 assertions
match full processing; 188 real moving scans preserve exact maps and histories.
Only fixed-point spatial duplicates can be reduced; neither physical run drops
distinct observations, and actual reduction counts are zero.

Two independent Mac corner runs record 89.962 s each with healthy heartbeat and
open backend gates. Maximum complete solves are 491.143/312.939 ms, but useful
planning is only 11.114/10.959 Hz; longest pauses are 23.787/31.283 s, with
850 emergency transitions per run. The mapper lags beyond the unchanged 250 ms
scan-age limit, so original safety checks repeatedly reject the old snapshot.
Goal arrival, trajectory continuity and steady 30 Hz acceptance fail.

No v49 deadline, new stop reason, watchdog change, inflation shrink or goal/yaw/
PVA/dynamics/support bypass exists. v48 stays the runnable reference. Complete
evidence, plots, diagnosis and storage locators are in
`audits/2026-10-05_safe_mapping_repair/REPORT.md`. v83 renders the actual failed
recording without rerunning physics.
