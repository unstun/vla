# v26 component validation

Seven host loader tests pass. The same tests against the unchanged v25 loader
have five failing assertions, including the actual v25 live configuration.

The real loader -> LayeredPctClient -> TCP PctIpcClient -> PctWorkerServer ->
NativePctPlanner regression passed all six cases in the pinned image. Old loader:
145 points,17.243903521675m, body endpoint z1.860560392834m. New loader:
631 points,73.410036509044m, body endpoint z4.831253391916m. This uses the actual
v25 measured start, so its length differs from the nominal-spawn73.2373m preflight.
Adapter explicit null matches the new route exactly. Fixed layer1 and both
explicit-request-layer controls match the old route exactly. Worker-received
wire requests and returned routes match the client snapshot and route bytes.

No native, policy, sensing, collision, PD or freshness threshold changes.
The clock/odometry scheduling gaps in v25 remain a separate open failure.
This establishes configuration and planning-chain repair, not physical route
completion. The source snapshot will be frozen before physical execution.
