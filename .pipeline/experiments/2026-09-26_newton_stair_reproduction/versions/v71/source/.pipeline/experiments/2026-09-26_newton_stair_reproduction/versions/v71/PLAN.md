# Upstream SCAN runtime comparison

Stage: experiment + analysis. Dr Sun authorized: "test it and show me video".

Use the pinned executable ROS2 port, yagami-light7/PCT-SCAN-ROS2
1cf45a1c12ca785ce533293302be09d51daf0ccb. The author ROS1 source used for the
preceding source comparison is wuyi2121/SCAN-Planner
348e8a590a50a5a6bbab8d8c6dcfd171f009be26. This is a ROS2-port integration test,
not a claim that the author's original ROS1 procedure has been reproduced.

The smallest gap is missing measured upstream behavior in the actual Mac
Newton Building loop. v71 branches from v70's host package and replaces the
native planning/map/search/optimization sources with the pinned ROS2 base.
Retain the exact current controller, identity messages, backend, physics,
factory startup, policy, sensor input and historical route. Native additions
are limited to identity/admission/cancellation transport and timing observation.
The original upstream three initialization modes and optimizer restarts remain;
local warm-cache, fixed-height recovery, shorter-prefix recovery, whole-curve
PVA/support contracts and 30Hz scheduling are not added to this baseline.
Its own terrain/trajectory contracts therefore differ and must be reported.
No v49 timeout or modified stop protocol is permitted.

Owned paths: versions/v71 host/transport/test/freeze helpers and receipts;
runtime/scan83_upstream_probe_v71 source only; this audit; task execution state;
version index; a separately versioned recorded-state video helper if needed.
Frozen parents remain immutable and current.json stays v48.

Ranked predictions:
1. Local outer recovery amplification: upstream has no 11-complete-attempt
   round structure; max complete attempts per reference replan should be three.
2. Inherited expensive search/optimizer: even without local outer recovery,
   individual upstream rounds can exceed 33.3ms and hit the existing 200ms A* limit.
3. Different admissibility/progress: upstream may stall or stop before the
   later corner; an early termination cannot establish superior full-route tails.

Before physics: verify canonical source and generated transport-only diff;
build all selected packages in the same cached amd64 Humble image; run actual
native identity/cancel smoke and negative source/install gate tests. Freeze
source/configuration and installed hashes. Execute one bounded 90s actual Mac
Newton trial with the original clock/stop rules. Preserve incomplete output.
Compare complete-round timing, retries, successful publication rate and
physical progress with the frozen v70 observation; distinguish unmatched
trajectory/load and missing-corner evidence. Add a same-input native replay
comparison if an early upstream failure prevents the meaningful comparison.

Mac exception: build and raw recording under unique /private/tmp roots outside
repo. Durable bulk destination:
gpu5070ti:/home/sun/vla_artifacts/2026-10-04_upstream_runtime/.
Use storage-only transfer; no GPU/simulator job there. Local return allowlist:
source/config, compact report/metrics/hash receipts/plots and finished review MP4;
expected under 20MB of new result/media bytes. Archive and verify every unique
raw member before removing temporary expanded data. Render v51 streaming MP4,
verify full decode and original frame/state hashes, and inspect representative
frames. Mac latency is not gpu5070ti performance.
