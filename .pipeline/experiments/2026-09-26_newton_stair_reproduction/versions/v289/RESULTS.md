# v289 evaluation closed; physical acceptance failed

The frozen v288 parent remains unchanged. The fourteen-package build,
functional tests and targeted probes pass; inherited Nav2 style/XML lint
failures are preserved separately. All fifty starts pass their uniform margin
checks. The full53 gate passes49/50 legal requests and rejects3/3 illegal
controls, with admitted global median1.430741857s under the user-authorized
shared CARLA/ROS load and original2CPU quota. No timing exception was used.

Each of the ten physical routes ran exactly once. Goal and measured terminal
PD pass6/10; sampled geometry and arrival pass5/10. A04,G05,CU06,CM02 still
fail. CD12 reaches but crosses the source-solid envelope by0.046221m.
All6130 scanner jobs meet100ms. Native signal crashes, native unresponsive
routes and regressed-body-stamp errors are zero. Every route retains one
global epoch and the original global geometry.

Remaining log counts include26 endpoint adjustment failures,58 A-star
optimization failures,48 inside-obstacle messages and410 actual solver
returns of-1008. The latter excludes six dashed replan counters. A lower rate
per completed planning round is not an independent solver failure probability.
The candidate is not promoted to the accepted navigation baseline.

Source manifest SHA-256:
`5406c3d4930c29d4bb4a456c43874963c236ab9de2ef7fc9ae2c27a60b5f1d06`.
No navigation source was changed after freezing or during analysis.

[Complete Chinese report](../../audits/2026-10-20_v289_ordered_input_terminal/ultra9/RESULTS_zh.md),
[ten ordinary local full videos](../../audits/2026-10-20_v289_ordered_input_terminal/ultra9/delivered/README.md).
All ten video hashes match; local full decoding and twenty-frame visual review
are complete. This new result artifact does not rewrite the frozen source
manifest or imply continuous-time or real-robot certification.
