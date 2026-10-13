# v87: Nav2 observation-window scheduling in SCAN's 3D mapper

Date: 2026-10-08. Stage: implementation + component analysis.

Implemented sensor-side observation buffering and independently timed map updates,
using Foxy Nav2's observation-retention semantics. SCAN's native 3D fusion,
support and collision queries remain in place. Source stamps and exact cloud/pose
pairing are retained. Expired/latest/capacity drops are counted; source-order and
metadata-overflow failures close the mapper. Selected observations are fused
once, rather than repeatedly marking retained observations as a 2D costmap does.

The candidate profile is 5 Hz with 0.5 s persistence and a 64-cloud cap. The
zero-persistence/latest-only profile is a comparison arm. Configuration and
implementation are in `building_planner.yaml` and `plan_env/`.

## Checks

- **37 checks pass**, including a direct comparison with actual Foxy
  `ObservationBuffer`, both zero and positive retention, expiry boundaries,
  capacity accounting and invalid-input handling.
- Six synthetic native-map cases confirm that a 0.5 s window retains the
  short obstacle burst, while latest-only misses it. When the last observation
  arrives 650 ms later, the 0.5 s window also loses that unprocessed obstacle.
  Passing this negative test is not obstacle-avoidance acceptance.
- The combined plugin/mapper workspace builds on ARM64/Foxy and passes the
  plugin tests and actual packaged native-worker lifecycle check.
- Two independent three-arm recorded runs use the same original 188 paired
  observations, original support inputs and two controlled 650 ms publication
  stalls. Input restoration verifies the original archive SHA-256.

Second recorded attempt (`recorded_comparison02.json`):

| Admission | Fused / discarded | Originally occupied cells no longer occupied | Maximum observed map age |
| --- | --- | --- | --- |
| FIFO reference | 188 / 0 | 0 | 0.800 s |
| Nav2 window, 0.5 s | 186 / 2 | 23 | 0.900 s |
| Nav2 latest-only, 0 s | 93 / 95 | 5,224 | 0.900 s |

The first attempt also yields 186/2 and 23 lost occupied cells for the 0.5 s
window. Latest-only yields 91/97 and 5,287 lost cells; scheduling changes which
observations survive. Both FIFO final full-state digests equal the archived
reference `da01d77d0e45f6f6a0884df0493dbcac3fae97bd42d13b96fffc44f8ec4a64af`.
The 0.5 s final full-state digest is identical across both new attempts but
differs from FIFO.

The source-age observer retains its previous immutable snapshot when the
publication lock is unavailable. These are observer-held snapshot ages, not
claimed physical controller latency. On the second attempt its 250 ms limit is
exceeded in 17 FIFO, 87 window and 70 latest-only samples. Native ingress remains
short while the writer is stalled; that does not establish fresh maps or 30 Hz
successful planning. The injected stall is publication contention, not a
reproduction of the historical CPU stall.

## Verdict

**The Nav2-style organization is implemented and component-tested. It has not
solved the navigation acceptance problem.** It bounds buffered observation work,
but retained evidence changes and stale-map intervals remain. Keep the original
250 ms source-age rejection and the plugin's fresh native-safety requirement.
Neither latest-only nor this 5 Hz/0.5 s profile is promoted to validated walking.

There is no full Newton route, physical robot run or locomotion qualification
for v87. The candidate does not replace v48. Source, compact logs and manifests
remain local; raw map arrays and build/install products are retained remotely
under the combined report's verified storage receipt.
