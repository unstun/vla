---
origin: ai_only
reviewed: false
status: surveyed
date: 2026-10-16
---

# CMU Go2 implementation versus Lite3 PCT–SCAN

**Recommendation: evaluate CMU as a lightweight navigation baseline, while
retaining the current stair-navigation baseline.** It supplies a connected
navigation implementation up to body velocity, but does not provide the Go2
locomotion controller or establish a transferable stair/multi-floor capability.

The [source audit](../../references/upstream/2026-10-16_cmu_go2_code_audit/comparison.md)
and [manifest](../../references/upstream/2026-10-16_cmu_go2_code_audit/repository_manifest.yaml)
pin `jizhang-cmu/autonomy_stack_go2` to
`43d5f54b389b251713f0097893c30fa76c870d54`, default branch `foxy-humble`.
The 2026-02-18 latest commit updates a download link, not evidence of a new
planning algorithm. A clean sparse reference contains 417 materialized files
and 23 ROS packages. No upstream build or runtime was executed.

## What is public

Point-LIO, terrain analysis, FAR global routing, local collision avoidance,
path tracking, ROS messages and the real Go2 Sport request path are present.
The real launch connects these components. `pathFollower.cpp:429` sends
`Move(vx, vy, vyaw)` or `StopMove`; the request library serializes commands.
Go2's joint control, balance and stepping are external vendor capabilities.

## Why stairs remain an integration problem

- The local path generator produces planar curves. This can steer a capable
  walker over steps, but supplies neither foot placement nor a Lite3-specific
  physical feasibility check.
- Default local obstacle filtering uses terrain-relative height above 0.3 m
  with soft cost disabled; FAR splits free/obstacle points at 0.15 m. The same
  0.18 m terrain value can be excluded locally and classified as an obstacle
  globally. This is a source-level illustration, not an 18 cm stair test or
  proof of route failure.
- Missing-ground protection exists even though `considerDrop=false`:
  `noDataObstacle=true` adds obstacles for sparse or sufficiently low ground
  in a forward window. It is not a demonstrated stair descent skill.
- FAR has 3D and multi-layer code, but Go2 defaults to `is_multi_layer=false`.
  Enabling the flag does not establish reliable stacked-floor navigation.
- The exposed Unity vehicle loop integrates commanded body motion. It does
  not validate leg contacts or the actual locomotion policy on stairs.
- The README explicitly links low-obstacle limitations to L1 lidar noise and
  expects obstacles taller than 0.3 m. Better Lite3 sensing may improve this,
  but requires changed calibration and measured validation.

## Cost and reliability judgment

ROS 2 Foxy/Humble and body x/y/yaw velocity make the execution interface more
direct for Lite3 than the public UAS aerial local modules. CMU's precomputed
path selection also avoids online trajectory-optimization complexity. Neither
fact demonstrates higher physical navigation reliability.

Lite3 still needs sensor/frame adaptation, body and collision-lookup geometry,
consistent terrain thresholds, controller capability matching, cancellation
and input freshness, and the existing physical standing completion criteria.
A waypoint-distance success or a `StopMove` request is not equivalent to the
current pose/yaw plus measured-stop plus confirmed-standing contract.

Use the same Lite3 controller, sensor stream and success criterion for a
bounded comparison: flat/narrow/low-obstacle navigation first; stair ascent,
descent, landing turns and multi-floor routing separately. The public code is
a useful candidate, not evidence that replacing PCT–SCAN solves those tasks.

The current v208 local record reports two initialized-state physical pairs
passing and zero new full routes. This review neither repeats an outdated
claim that no stop repair exists nor treats those pairs as route validation.

Primary code, exact paths, package licenses, source hashes and documented
launch commands are collected in the linked audit. Status remains **surveyed**;
there is no CMU integration, reproduction, runtime result or baseline change.
