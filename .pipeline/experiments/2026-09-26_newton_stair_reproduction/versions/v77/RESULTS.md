# v77 upstream corner test and partial review video

Stage: experiment + analysis. Parent v76 selects the exact v71 upstream ROS2
probe in the identical physical corner fixture. Existing external transport,
controller/backend and stop rules remain; native planning contracts differ.
Post-run closeout archives and renders actual observations despite missing final
result evidence. No final result is synthesized or safety threshold changed.

The six-package build passes. Attempt01 fails the actual route-admission smoke
before physics; logs are preserved. Attempt02 reuses the unchanged verified build
and passes all six actual transport/cancel checks before freezing and running.

The physical recording fails on the original AppliedClient receive/ACK path,
then fails final state/last-ACK hash verification. Last video time is 37.751 s;
the original final result is absent. Observed path is 1.130 m, then stationary.
There are 10 successful / 1,226 completed chains, 0.323 successful wall Hz,
median 13.422 ms, P95 43.218 ms and maximum 311.138 ms. At most three complete
initialization attempts occur per chain, with 2,828 inner optimizer collision
restarts across the recording. This is an incomplete failure, not validated
navigation/stop behavior or a same-input speedup over v63. The last saved backend
gate is open; no heartbeat terminal is established from this capture.

The actual partial review MP4 contains 921 causal frames, 30.700 s, 1280×720 at
30 FPS. Full decode, original state/time/index verification and three-frame
visual review pass; the partial-capture label remains visible. [Video receipt](REVIEW_VIDEO.json)
separates display/storage success from physical failure. All raw/render files
are durably SHA/size-verified on gpu5070ti, storage only. See
[comparison/report](../../audits/2026-10-04_corner_start/REPORT.md).
Production v48 and frozen v49 remain unchanged; the main 30 Hz repair stays open.
