# v256 — Offline native solid-body repair qualified

Frozen from v254; B08 original unsafe pose is now StaticObstacle(7), independent margin −0.183233718 m. Shared 0.35 m non-ground body geometry is used in graph, GPMP and static admission; original support/RL/sensor thresholds are unchanged. 61 plugin tests and 97 native regressions pass (10 overlapping; 148 distinct), with zero mismatches over 10,928 independent solid poses. Original controls retain ten positive first-GPMP/SCAN passes, B08/B09 refusals, H00 and exact measured A02 checks.

This is a native repair qualification only. The subsequent frozen v257 expanded 52-case cohort fails its prospective physical gate (34/49 positive full-chain). No new physical acceptance claim. See [complete mechanism and expanded evidence](../../audits/2026-10-18_v256_static_solids_and_space_coverage/RESULTS.md), [native receipt](results/acceptance_receipt.json) and [manifest](manifest.json).
