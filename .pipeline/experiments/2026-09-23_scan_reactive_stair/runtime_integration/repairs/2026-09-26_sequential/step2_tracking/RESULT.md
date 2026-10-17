# Static foreground tracking repair

Status: **validated for the declared recorded-input tracking component test**.
This does not establish live stair navigation, human recognition, or avoidance.

The old selected-ground mask removed 99.88% of the returns in the right actor
region. Simply using full ground joined actor returns to the building, and a
3D-cluster probe fragmented both sequences. The selected repair uses the pinned
published Building PCD only to extract current LiDAR foreground, then applies
the existing XY shape and observed-motion association code. Navigation still
receives every raw LiDAR return. Unknown space is not cleared by the prior.

The separate `/tracker_ground` payload has 149,504 finite ground records and a
fixed frame, SHA-256, PointCloud2 layout, field offsets, types and counts.
Invalid support, stale inputs, missing foreground ground, poor background
alignment and unresolved/lost tracks fail closed. The original selected
`/pct_tomogram` payload remains byte-identical (86,775 records). A review found
and closed a same-bytes/wrong-z-offset hole before building scan_22.

The frozen Foxy runtime imported SciPy 1.8.1 with Python 3.8.10 and the unchanged
NumPy 1.17.4. The captured wheel and all extracted members were verified. No
system package or container image was changed. All 19 targeted unit tests passed.

| Recorded placement | Published frames | Matching local/Foxy/ROS frames | Complete actor frames | IDs | Max ROS receive latency |
|---|---:|---:|---:|---:|---:|
| Original | 280 | 280 | 189 | 1 | 20.60 ms |
| Right | 282 | 282 | 189 | 1 | 20.41 ms |

Both sequences have zero pre-motion tracks and zero tracks outside the actor
scoring radius. The first complete actor observation occurs at 10.22 s, about
0.1 s later than the original-position V2 tracker. Actor truth is read only by
the host scorer after inference; it is absent from the remote replay inputs.
An independent reviewer checked all actual ROS messages, not just the first
matching one, and found no conflicting complete observation.

Evidence: `RESULT.json`, `foxy_scan22_v1/review.json`, its immutable results,
package/input manifests and returned-file hashes. The full native build has
458 installed files; identity SHA-256 is
`62c0bd04ee68668f289a54a45016a607de6ae1be342f1c0bda5aeed981dfc845`.

Regeneration uses `replay_foreground.py prepare` into a fresh input directory,
`run_foxy_foreground.py --run-id NEW_ID`, then `score_foreground.py RUN_DIR`.
The original recorded files and imported PCD remain the authoritative bytes.

Live V3 packaging is opt-in through `--static-background-tracker`. It stages
the exact prior and dependency, supervises a separate physical-ground publisher,
and requires both the V3 source ID and physical-ground topic for readiness.
The reviewer caught and closed a missing Foxy `/qualification` mount; six
launcher tests pass.

## Live standing integration

`runs/stand_scan23_tracker_right_v1` subsequently completed a 20.08 s actual RTX
standing episode. All 49 returned artifacts match; all 201 sweeps are ready.
The actor starts moving at 10.02 s, and the first track arrives at 10.22 s;
99 nonempty snapshots retain `cluster-1`. Both ground payload hashes match the
contracts above, and every track source is V3. The verified wheel unpacked
1,285 matching files in the disposable container. No navigation goal was sent;
all admitted commands are zero, nonfoot force is zero, and no reset or pose
injection occurred. This closes live standing tracker wiring only.

`LIVE_RESULT.json` records the runtime boundary and media identity. The actual
20.08 s, 251-frame H.264 video was fully decoded, inspected at 12 and 18 s and
copied as a regular deliverable file to
`output/2026-09-26_stair_human/stair_tracker_right_fixed_stand.mp4`.
