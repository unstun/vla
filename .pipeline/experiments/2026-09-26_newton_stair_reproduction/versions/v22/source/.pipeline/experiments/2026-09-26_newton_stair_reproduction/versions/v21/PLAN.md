# v21 candidate: separate additional floor evidence from selected-tread risers

Stage: experiment + analysis. Parent: v20. One terrain-input contract change.
This candidate is not navigation acceptance. The user has a pending choice
about known mapped low protrusions versus semantic independent-box avoidance.

The v19 189-scan stop reproduces at the actual odometry pose. Original selected
navigation costs omit measured tread cells and make their raw returns obstacles.
A simple broad raw map was rejected as an acceptance solution. Restricting the
existing riser inference to the original selected treads, while allowing extra
un-inflated-cost source elevations to match only the original 0.05 m floor band,
gives a complete native continuation, PVA and whole-curve collision pass.

Reuse the pinned original PCT CPU generator's un-inflated cost observation and
original float32 elevations. Keep selected support, global PCT, 3D clearance,
unknown/freshness gates, 0.6 m/s planned cruise and original riser inference.
Publish extra surface evidence on a separate required Building topic. It never
expands scored support and cannot invoke the riser extension. Flat profiles
retain the old input contract. Missing/invalid required evidence blocks queries
and prevents raw-cloud ingestion before classification inputs are ready.

Tests: production ROS subscriptions with original 66/67 and actual v18/v19
inputs; missing/malformed evidence; isolated map ownership; stale cloud and
unknown guards; eight original measured obstacle cases; five mapped examples
with full baseline and new free-envelope counts. Known mapped 0.13 m cases must
be reported separately pending user acceptance semantics. Then bounded short
Building physics with versioned video, before the historical complete route.
No robot actuation or training is part of this version.
