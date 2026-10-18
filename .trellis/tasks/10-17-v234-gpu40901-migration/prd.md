# v234 gpu40901 host migration

## Authorization and goal
Dr Sun explicitly approved task creation and implementation on2026-10-17.
Move the frozenv232/v233 runtime to gpu40901 and pass offline gates. Report
before separately arranging a full-route physical experiment.

## Requirements
- Local VLA repo is the only source of truth; remote workspace is an execution copy under /home/ubuntu/sun/vla_v234_20261017.
- Preserve frozenv232 navigation andv233 reference, exact RL, original historical_full endpoints,0.35m hard collision/support guards and all native control/terminal gates.
- Isolate current IsaacLab: no signals, priority/affinity changes, package changes or GPU exclusivity requests affecting existing jobs.
- Prepare both pinned native/Foxy and ARM factory images, Newton/Python dependencies, underlays, native install, source, fixtures, scene inputs and launch/driver chain.
- Addv234 host binding only; no navigation algorithm, RL, geometry, solver-weight or tolerance changes.
- Retain every failed preparation/test; no new physics, training or real-robot actuation is authorized.

## Acceptance
1. Verify frozenv232/v233 source manifests and317 native source hashes. Rebuild all14 packages, record new installed hashes, verify original607-path coverage, and resolve all native libraries/package prefixes. Original installed-byte identity is an optional historical audit.
2. Actually rerun the165 distinct/186 colcon-record offline regressions on40901, including delayed zero-tail/shared-cost and fault closure. Historical receipt alone does not satisfy this gate.
3. Run static environmental consumer parity and actual installed Building admission; unchanged hard decisions and endpoint/config identity must hold. The historical126324+3 dynamic replay remains a separate optional audit if its original inputs are unavailable.
4. Start the actual source-bound graph for12s without physics, verify normal shutdown and no false failure receipt.
5. Smoke the host Newton/ONNX/scene and factory protocol without physics steps; validate video/runtime dependencies separately from a real video.
6. Return compact source, receipts/logs, exact sync manifests and existing-job continuity evidence locally. No caches/heavy data returned. Stop and report at offline validation.

## Verified checkpoint
The source host is powered off (user confirmed). Exact source reconstruction
and a new all14-package install were executed instead of copying its old
binaries. All independent gates pass; original607-path coverage is verified,
but original install byte identity is not. Operational offline migration is
accepted. Original runtime comparison and126324+3 dynamic replay inputs are
optional supplementary audits, not dependencies for gpu40901 execution.
See versions/v234/READINESS.md for the current assessment; RESULTS.md and
results/offline_summary.json retain the earlier checkpoint interpretation.
Next: prepare/preflight a full-route host launcher, then arrange physical
verification. No new physics has run or been authorized by this reassessment.

## Authorized physical continuation (2026-10-17)
Dr Sun explicitly authorized a full gpu40901 launcher, offline preflight, then
exactly one complete closed-loop route and comparison video. Preserve RL,
original endpoints,0.35m guards and existing IsaacLab tasks. v235 owns this new
logical execution change; previous no-physics authorization limits apply only
to the earlier migration checkpoint. Runtime baseline remains v232/v233 until
a separately reviewed new result. No automatic physical rerun after failure.

## v236 scanner repair and one new route (authorized2026-10-17)
Dr Sun explicitly authorized diagnosis/fix of LiDAR timeout, with emphasis on
two-CPU affinity/contention, preserving RL, original endpoints,.35m thresholds
and.1s capture period. Pass regression/profile/actual graph preflight, then run
one new full-route physical trial and deliver results/comparison video.

## Return to gpu5070ti (authorized2026-10-17)
Dr Sun selected the original5070Ti for continuation after the one v236 failure.
Preflight and execute one original-route trial as v237, retaining v232 native
source/install and v236 scanner repair. Existing constants and peer-isolation
requirements remain unchanged; no further40901 physical work is planned.
