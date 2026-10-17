# Design

## Boundary
The source of truth is the local VLA repository. Add version overlays under the existing Newton experiment, using v219 as the pinned execution parent. Do not change any frozen parent.

## Shared environmental scoring (Dr Sun's clarification, 2026-10-17)
Binary admission alone is insufficient. Both planners must prefer a supported route with more room over a marginal but technically admissible route. A single native assessment must return the hard verdict and separate continuous terrain-difficulty and body-clearance penalties for a pose, heading and height layer. Use the same definitions, units and normalization in both consumers. A high soft score cannot make a hard rejection pass.

Dr Sun clarified that following a boundary is acceptable provided the robot retains enough clearance. Do not impose road-centering or keep rewarding larger clearance indefinitely. Measure clearance from the complete oriented body envelope, including rotation between poses, rather than the reference centerline. Use an explicit target margin in metres and a clearance penalty that reaches zero once that margin is satisfied. Narrow feasible corridors must not be rejected merely because a wider route exists. The target value remains an engineering parameter to validate against the actual scene; no universal safe distance is claimed.

PCT must consume the environmental score during graph search and smoothing, before final admission. SCAN must consume it during local trajectory optimization. Do not merely add a score to a diagnostic message. Keep route length, local dynamics and smoothness as planner-specific terms; equal complete objective functions are neither required nor appropriate.

Distinguish static terrain/support-edge clearance, static solid-obstacle clearance and locally observed obstacle clearance in the data and evidence. The current native static query only establishes the first category; it must not be described as complete static 3-D collision parity. Unobserved live space is not a confirmed obstacle.

Acceptance must include a two-corridor case where both corridors pass hard checks but the safer corridor receives a lower shared environmental penalty and affects the actual returned plan. Verify both consumers and report latency. The inherited PCT search suppresses step penalties below 5 after multiplying by 0.2, and its smoother has a separate zero-penalty margin; both dead zones must be addressed for the new shared term without changing legacy mode.

## Historical regression boundary
Dr Sun also requires PCT itself to leave room and asks which change made it appear closer to boundaries. Before treating added soft costs as a regression fix, compare the actual historical route geometry and input identity. The archived v210, v212, v217 and v219 initial references are identical across all 649 poses, including orientation. The 122 PCT core/adapter/policy source entries compared from the executed v206/v212/v217/v219 inventories are identical. The v210/v217/v219 execution copies have identical PCT bundle and support-gap hashes. The small-cost dead zone also exists in the original imported A* implementation and is not newly introduced in v212.

The confirmed strategy change is v212's removal of the 1 Hz global planning child. In the recorded 45-55 s stair window, v210 delivers 8 references and v212 delivers none. This establishes a changed reference-refresh history, not a causal proof that a particular wall clearance caused SCAN failures. Keep the refresh regression and shared-scoring improvement separately attributable; do not silently change refresh frequency under a geometry-only version. The comparison script, raw observation hashes and compact results are in research/.

Dr Sun subsequently clarified that the earlier statement was a visual impression, not a claim that a particular old version was better. Historical investigation is now supporting evidence, not a prerequisite for a clearance preference. The returned native gap-mask probe rejects none of the sampled PCT references in the selected stair region even after adding 0.15 m to the two-cylinder radius. This rules out insufficient support-gap margin for those sampled references under that predicate; it does not establish solid-obstacle, wall or live 3-D clearance. Do not implement a gap-only score and call it a complete obstacle-clearance solution.

## Shared checking
Reuse SCAN's existing map and immutable query views rather than construct another live mapper or copy a 2-D costmap into PCT. Introduce an explicit batched traversability query contract in lite3_nav2_interfaces. Its provider belongs to the native SCAN worker and uses a private immutable query view. A dedicated PCT client node/executor avoids Foxy executor re-entry while createPlan runs.

Separate static support/body checks from live observation admission. Extract the existing support-only predicate without changing its native caller's temporal/occupancy checks. Static checks use the same scored terrain, gap mask, body reference height, two-cylinder offsets and heading as SCAN. A static-only check cannot authorize a robot command or manufacture live free-space evidence. The live mode distinguishes outside/unknown coverage from confirmed blockage.

## PCT consumer
PCT retains the pinned multilayer search and optimizer. Add bounded candidate repair using explicit rejection constraints. Those constraints must be honored by graph search and final smoothed output, with map/height association preserved. Constraint storage is separate from the immutable base bundle; update both search and optimizer input views when costs change. Do not rely on increasing an old cost threshold to enforce a hard rejection.

RoutePolicy validates every returned route, including terminal retention and error fallback, against the current constraint revision. New checked routes preserve the original requested/canonical terminal pose. Replanning must not cancel an independently usable SCAN trajectory.

## Local feedback (v222)
Report a typed geometric rejection witness (pose, heading, height layer, reason, observation/map identity and active route identity). A boolean failed solve, unknown observation or stale source is insufficient to assert an obstacle. Publish/consume bounded feedback; bind its admission to the active mission and observation source. Keep planner-attempt timing distinct from spatial constraint lifetime so a replacement Path does not erase a persistent obstruction.

A candidate checks the latest admitted spatial constraints and a coherent native query revision. Direction-specific pose failures remain directional; confirmed environmental occupancy may reject relevant poses across headings. Reconsider transient constraints on newer clear evidence or bounded expiry, without granting SCAN execution clearance.

## Compatibility and rollback
v221 excludes spatial failure memory; v222 adds it. Existing standalone/component fixtures explicitly select legacy or shared checking as appropriate, while generated candidate runtime profiles enable the new mode. v219 remains runnable with its exact inputs/install identity. No migration of old logs or rewriting old manifests.

## Risks and deferred items
A global reference is not a dynamic execution proof. Far static planning cannot prove future live clearance. Heading-aware graph expansion is added only where the pose constraints require it; do not silently replace quadruped motions with a car model. New physics and performance/route reliability claims remain separate gates.
