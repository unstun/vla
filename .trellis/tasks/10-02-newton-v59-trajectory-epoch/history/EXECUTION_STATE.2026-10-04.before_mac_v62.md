# Latest diagnosis — 2026-10-03

Dr Sun requested "find problem". The audit `audits/2026-10-03_v59_cold_recovery/REPORT.md` confirms: (1) remaining curve is clear but a new83-degree connector heading enters the original drop guard at its first sample; (2) a clear fitted seed becomes colliding and each optimizer attempt repeats three identical failed constraint searches; (3) v59 loses the sampled epoch across FSM retries after old-curve expiry, rebasing unchanged PVA by1.259308s. The third finding corrects the earlier report's "fresh restart" interpretation. Direct timing tests remain scoped evidence, not a complete timing repair.

Two native CPU replays and a static floor witness pass; frozen native sources remain unchanged. Preparation attempt01 failed on a one-ULP equality assertion and is preserved. No new navigation version, physics, stop change, or timeout was introduced. Compact evidence is local; raw streams/builds remain on gpu5070ti. The audit recommends explicit failure propagation, retaining sample/PVA identity across all retries, and a feasible heading-aware trajectory extension. Main task remains open.

---

# Current execution state — 2026-10-03 delivery

Stage: experiment + analysis. Dr Sun authorized repair of the v57 post-70-second anomaly, then instructed us to wait for the other gpu5070ti evaluation. The GPU became free; both authorized 90-second validations and final review rendering are now complete. Do not repeat completed run IDs.

## Delivered repairs and evidence

- Frozen v58, parent v57: current necessary endpoint evidence before final-goal search. Five native files; original manager/FSM/controller/configuration unchanged. Build02 and full contracts02 pass, including 3,000 footprint-pair cases and inherited native/cache/warm/goal/freshness/physical-floor/backend gates. Idle-host replay03: 20 states, 80 calls, exact outcomes/paths, max 44.614381 → 0.259025 ms (99.4194%). Replay02 and its host-load caveat remain preserved; do not replace its frozen summary.
- Frozen v59, parent v58: retain the checked sampled trajectory epoch through warm/native fallback and consume elapsed time once at controller receipt. Build01/contracts01 and supplemental clock negatives pass: 15 actual-controller checks and 10 epoch checks per native fixture. Original stop, goal/yaw, PVA/dynamics, occupancy and stair rules remain; no v49 timeout mechanics.
- `v58_realtime_trial02`: 27.53428 successful Hz; whole-window median 2.040671 ms, P95 12.827233 ms, max 659.526460 ms; measured path 55.188386 m. No measured >1 s hold after the shared initial 1.40 s wait.
- `v59_realtime_trial01`: 26.42581 successful Hz; median 1.947497 ms, P95 13.092583 ms, max 1236.709246 ms; path 55.041707 m. Additional 1.099396 s pause at 81.287–82.386 s.
- Both ran 90,000 physics steps, recorded 89.962189 native seconds and dropped zero steps. No logged emergency or invalid-current-spline event; neither reached the complete final goal.
- At 81.027 s, v59 rejects `target_connector`, then takes eight cold rebound attempts. The observed old trajectory 1934 nominally expires at 81.440673 s; recovery publishes at 82.286407 s with sampled=0. Observer expiry is not exact controller pause-clock reconstruction.
- Late 85–90 s matched v59 handovers have zero epoch rebasing and maximum common-publication-time position difference 0.168 mm. This is separate from physical no-pause acceptance and from exactly identical optimized geometry.

## Artifacts

All paths below are under `.pipeline/experiments/2026-09-26_newton_stair_reproduction`:

- `versions/v59/REPAIR_REPORT.md`: full comparison, remaining failure and scope limits.
- `versions/v59/analysis/v59_time_series.png` and PDF: actual recording-window frequency, latency and measured progress. The horizontal axis is simulation time; frequency uses a rolling wall second. Original all-log metrics are retained separately.
- `versions/v61/REVIEW_VIDEO.json`: final display-only replay of exact v59 states. Local ordinary file `output/2026-09-27_lite3_versions/v59_realtime_trial01_review_v61.mp4`, 10,488,224 bytes, SHA-256 `03ade05cdc1f51e9c75650cb686f85dcfed6d53e8271ab3a9e6832814f8acc1a`. Full decode, all 2,449 time/state selections, six visual samples and all-frame low-variation screening pass.
- v59's original occluded camera and v60's cropped view remain remote as failed display attempts. v61 changes only framing. Raw NPZ/JSONL, complete frame arrays and builds remain on gpu5070ti.

## Current acceptance and next boundary

The two diagnosed endpoint/timestamp mechanisms pass their scoped tests. Sustained 30 Hz, full tail elimination, v59 uninterrupted progress and full-route arrival do not pass. v48 remains the runnable reference. Keep v58/v59 frozen; no new navigation change was folded into this delivery. The remaining connector/cold-recovery chain is recorded for a separately versioned repair and review.

GPU-wait heartbeat `finish-vla-planner-validation-when-gpu-is-free` is now **PAUSED** after results and the actionable validation failure. No owned remote run remains active. Do not stop or alter unrelated workloads. Local repository is source of truth; remote execution root is `/home/sun/vla_exec/vla`.

No commit or broad staging was performed. Preserve unrelated dirty work and the existing index-lock history. The previous execution state is saved under `history/`; its waiting/running notes are historical, not current.
