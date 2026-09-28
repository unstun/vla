# v24 native component results

Final native scan58 builds in63.589s. All97 source files and515 installed files
match the frozen version and build manifest. The source review is closed.

The actual v23 30s failure becomes a1.484612571m accepted continuation, duration
3.465794882s. Two native processes produce identical accepted controls/knots;
independent reconstruction gives maximum endpoint PVA residual2.73e-15. The
whole published curve passes collision sampling. All nine continuations
(original66/67, v18, v19 twice, v21 twice, v23 twice) and their no-progress,
out-of-map and stale-input gates pass.

Fifteen targeted body-support conditions pass, including a direct old
WrongHeight -> transformed support_z=.44 -> final Free assertion, and continued
rejection of actual/unknown obstacles, stale data, wrong body height, closer
Unknown/Unsupported layers, ambiguity, exact/excessive step heights, other
building levels, missing support and mismatched source/elevation. Existing ROS
source withdrawal/layout/freshness contracts also pass.

All eight complete unmapped-fixture JSON outputs exactly match v23. This is a
fixture scope claim, not proof of every obstacle geometry.

Mapped fixture free/envelope-overlap-free counts:

| Fixture | v23 | v24 |
|---|---:|---:|
|13cm low box|387/114|423/150|
|Low box beside wall|195/54|211/70|
|High box|109/0|109/0|
|Short wall|75/0|75/0|
|Overhead|10/0|10/0|

The36/16 added low-protrusion free queries all overlap its navigation envelope.
This is the expected terrain-support acceptance change, not observed physical
contact or stable stepping. The mapped-low-protrusion policy remains pending;
no universal independent-box avoidance is claimed. Physical validation is a
separate gate; the current short Building run contains no added objects.

Evidence: runs/v24_native_regression01/{execution.json,review.json,body_support_contract.log},
original result/query/log files and frozen source/install manifests.
