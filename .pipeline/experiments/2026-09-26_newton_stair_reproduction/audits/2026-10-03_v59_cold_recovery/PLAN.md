# v59 cold-recovery diagnosis

Stage: experiment + analysis. Dr Sun requested "find problem" after the v58/v59 validation. This audit is diagnostic only; frozen versions, native libraries, goal/yaw/PVA/safety and stop contracts remain unchanged. No new physics, navigation version or production repair.

Reproduce the recorded 81.027 s round: warm `target_connector` rejection, eight replan attempts, six failed rebound A* calls, 1.236709246 s solve and the subsequent pause. Extract exact initializer points/PVA and observer input order from the existing remote archive. Reuse the earlier after70 serialization/native-map replay seam, bounded to a CPU-only offline container. Heavy event streams/builds remain remote; compact results and source identities return locally.

Ranked predictions, stated before probing:

1. The selected nearest-point straight connector is invalid while the remaining curve is valid. Native replay must locate its first blocked footprint sample; test other joins against the same unchanged map.
2. `initControlPoints()` failure returns paths without an explicit failure result, so the optimizer retries after its misleading "aborting" log. Trace exact call endpoints and cost across repeated iterations.
3. Fitting/optimization moves a valid graph seed into collision. Replay the exact seed through the original fitter and optimizer and compare initial/final geometry and failed search endpoints.
4. Repeated ordinary/fixed-height attempts and fresh cloud application multiply the cost. Attribute calls without summing overlapping scopes; do not confuse CPU work with host contention.

Additional source/trace finding to verify: later `reboundReplan()` calls may retain the original sampled start PVA while dropping its epoch after the old curve expires. Compare the original sample, all retry boundaries and final publication using captured curves. Observer ordering does not reconstruct exact live DDS batching or controller pause state.

Expected output: reproducible trace/native checks, ranked findings with source lines and measurement boundaries, and a concrete repair recommendation. Production changes require a separately frozen integer version.
