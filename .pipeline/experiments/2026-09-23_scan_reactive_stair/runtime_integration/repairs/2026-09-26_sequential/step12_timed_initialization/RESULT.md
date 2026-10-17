# Timing initialization result

scan_28 preserves supplied endpoint PVA with fixed first/last three controls,
fits internal position rows, and performs at most eight initial refits using
the unchanged native derivative bounds. It still uses the original rebound
optimizer. A final numerical PVA guard rejects later soft-refit drift. All
collision, Unknown, footprint heading and dynamic limits remain unchanged.

The old native fit fails three declared regression cases and passes the straight
positive. The new actual UniformBspline suite passes eight cases both locally
and in pinned Foxy. Independent review found no blocker; full build and the
462-file installed identity passed. The initialization uses the supplied start
acceleration (zero for this first plan), not a measured acceleration estimate.

The first replay published one moving spline but exposed a separate preexisting
replay twist-frame bug during independent endpoint verification. Its complete
evidence is retained as RUNTIME_RESULT_legacy_twist.json. It satisfies the velocity
actually supplied by that old replay, which differs from recorded world velocity
by 0.000462074 m/s. Do not describe that run as measured-world PVA continuity.

Step13 fixes the replay by adding directly recorded body-frame twists from the
same physics rows, while leaving clouds, poses, world twists, tracks, route and
planner parameters unchanged. On these paired corrected inputs, scan27 still
publishes no moving spline and scan28 publishes one. The received scan28 cubic
has 451 controls, duration 93.222983 s, and passes 9,324 collision samples, the
original optimizer, final PVA and dynamic gates. Independent endpoint arithmetic
finds start world-velocity error 5.04e-11 m/s, with zero position and requested
acceleration residual. Control-point norm bounds are 0.091142 m/s and
0.290045 m/s². RUNTIME_RESULT.json and accepted_spline.json name the corrected run.

The bounded live run walk_scan28_height030_right_v1 did not reproduce route
search success: 75 searches failed before seed validation, and no nonzero
navigation command was admitted. This is a separate live-input gap, not an
optimizer regression. It returned 29.08 simulation seconds, no nonfoot contact,
no reset/pose injection, all49 matching artifacts and a decoded29.12-second
video. The effective runner cap was35s and driver cancellation27s; the inherited
run_request45s field is not the executed limit. Step14 captures this fresh input
prefix to separate changed map coverage from realtime scheduling.
