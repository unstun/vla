# Diagnose the v76 977 ms input-processing spike

Stage: experiment + analysis. Dr Sun asks for the root cause of the measured
976.721 ms inclusive input scope in the v76 1,307.535 ms round. No production
planner/safety/stop repair is part of this investigation.

Read the exact native v63 callbacks and the remote SHA-verified v76 raw capture.
First reconstruct original refresh sites, scan counts and timestamps; distinguish
one expensive update from accumulated work across the synchronous retry chain.
Use existing recorded-message/map replay helpers for isolated native profiling
if the original aggregate scopes cannot localize the hot functions. Preserve
frozen v74-v77 and the v48 reference. Diagnostic native instrumentation, if
required, gets its own source-bound integer version; never edit frozen code.

Ranked falsifiable predictions:
1. Queued scans accumulate during search/recovery: the round's input-refresh
   records contain multiple newly received scans across replan/rebound/final
   boundaries, and processing those scans dominates input CPU time.
2. Sensor-pose movement repeatedly shifts the large local map: recorded centers
   cross 5 cm cells; native sliding resets/inflation deletion dominate a separate
   measured scope, whereas repeated calls at the same center return immediately.
3. Per-cloud raycasting/terrain classification/inflation is intrinsically costly:
   isolated recorded scan replay reproduces high CPU cost in a specific stage
   without DDS, the optimizer, rendering or simulator physics.
4. Host scheduling dominates: wall time substantially exceeds same-thread CPU,
   and isolated native stage CPU falls well below the historical totals.

Own only this audit, any explicitly declared diagnostic version/probe, compact
results/report and task/spec/journal updates. Keep raw data on gpu5070ti. Remote
access is read-only storage/standard-library extraction; no GPU/simulator job.
Mac builds and selected replay inputs use unique owned private/tmp roots and
are cleaned only after result/raw identity and durable storage checks.
Report original measurements separately from instrumented replay and inference;
do not claim an exact historical DDS queue/map-state restoration without proof.
