# PCT / SCAN traversability and blocked-region feedback

## Goal
Global references should be executable under SCAN's geometric rules, and a rejected local region must change subsequent global planning instead of repeatedly delivering the same unusable geometry.

## Authorization and scope
Dr Sun approved implementation in two stages, preserving the original version, then explicitly approved task creation and continuing on 2026-10-17. The immediately preceding reviewed summary names v221 (shared traversability), v222 (blocked feedback), and v219 as the preserved control. No additional product decision is required to implement that scope. Formal training, new full-route physics and real-robot actuation are separate authorization boundaries.

## Confirmed baseline
- Latest validated source: v219; v220 only renders the recorded v219 run. Parent source overlays and results are immutable.
- PCT loads a static PCTMAP01 bundle; SCAN owns live 3-D occupancy, body heading and scored support. Nav2's 1x1 costmap is only a lifecycle/TF shell.
- The v217 stair refresh was followed by eleven deliveries of identical pose geometry; the last five v219 deliveries also shared geometry.
- Existing native gap queries on archived route yaw did not reject the examined stair reference. This does not prove live 3-D feasibility or establish edge clearance as the primary cause.
- SCAN's immutable snapshot query and current geometry/support implementation are reusable; source freshness and actual command admission remain local responsibilities.

## Requirements
R1. Use the same body envelope and static terrain/support rules for PCT candidate admission and native SCAN queries.
R2. Check final smoothed references and their connectors, not only graph nodes. A rejected candidate must change the next search problem or return a truthful no-route result.
R3. Global references outside current sensor coverage retain static-map planning; unknown live space must remain distinguishable from confirmed geometric blockage.
R4. Feed spatially located, typed, timestamped local blockage into PCT, bound to the active mission/route and map source. Solver or timing failure alone must not become a hard obstacle.
R5. Apply new constraints to search, smoothing and final admission, including cached route returns. Preserve still-usable execution while replanning.
R6. Preserve v219 source/config/results and separate v221 from v222. Bind builds/replays to local source hashes and return compact remote evidence locally.
R7. Preserve original target pose, speed/motor settings, collision/support thresholds, sensor-age bounds, stop rules and retry budget.
R8. Share continuous environmental difficulty and clearance scoring between PCT search/smoothing and SCAN optimization, alongside the shared hard verdict. Preserve planner-specific length, dynamics and smoothness terms. A score emitted only for diagnostics does not satisfy this requirement.
R9. Boundary-following routes remain acceptable when the oriented body retains the target clearance. Measure the margin from the swept body envelope; saturate the clearance preference after the target is reached. Do not substitute road-centering or unbounded obstacle avoidance for this requirement.

## Acceptance
A1. Identical static input and pose/yaw yield identical shared-rule verdicts; retain original native accept/reject behavior during extraction.
A2. A blocked smoothed route/connector is never published; a fixed-input scene with a valid alternative returns a checked alternative.
A3. Same XY on different floors remains independent; direction-specific blockage does not automatically prohibit every heading.
A4. A confirmed local obstruction changes the next candidate, and clearance/new evidence permits reconsideration; stale or old-mission feedback cannot affect a new mission.
A5. Cache fallback cannot republish geometry rejected by the current constraints.
A6. Existing tracking, source freshness, cancellation, map immutability and terminal tests remain passing.
A7. Compare v219 / v221 / v222 on identical recorded inputs with route geometry, native verdicts, repeated rejected regions, solve latency and no-route outcomes. New physical-route acceptance is reported only after separately authorized runs.
A8. Same static evidence and pose/yaw produce identical environmental score components. In a fixed scene with two hard-feasible corridors, the lower-risk corridor is preferred by both consumers, and the scores demonstrably participate in search and trajectory optimization.

## Task map
- 10-17-pct-scan-shared-traversability: v221, R1-R3 and the shared admission/cache portion of R5.
- 10-17-pct-scan-blocked-feedback: v222, R4-R6; depends on tested v221.
- Parent: integration evidence and preservation review.
