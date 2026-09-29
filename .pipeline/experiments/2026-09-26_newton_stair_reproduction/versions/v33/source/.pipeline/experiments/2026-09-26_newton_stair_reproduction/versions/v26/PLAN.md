# v26: preserve explicit automatic PCT layer selection

Stage: experiment + analysis. Parent: v25. One configuration-loading repair.

The v25 live configuration contained `map.pct_layer: null`, but the loader
discarded it and retained default layer1. The real request therefore produced
a145-point17.244m route ending at body z1.861m instead of the historical
complete-floor route. The v25 direct native preflight did not exercise this
loader; preserve that validation gap and the failed physical run.

Preserve explicit null only at the complete configuration path `map.pct_layer`.
Omission keeps the existing default. An integer keeps fixed-layer behavior.
The adapter schema must distinguish an absent pilot field from an explicit
null. Other null values retain their existing ignore semantics. LayeredPctClient
and per-request explicit layer precedence are unchanged.

Record old/new loader tests, then run the actual loader -> LayeredPctClient ->
TCP PctIpcClient -> PctWorkerServer -> NativePctPlanner chain. Use the captured
v25 measured start and historical goal. Archive resolved configuration,
forwarded request, runtime snapshot and complete worker route for both old and
new loaders, fixed layers, adapter schema, and explicit request overrides.

Keep native scan58, map, policy, speed, geometry and PD/safety thresholds exactly
as v25. Freeze before a new bounded historical full-route physics run. Route
selection repair is separate from the open odometry/clock freshness failure;
complete acceptance still requires actual arrival and final PD hold.
