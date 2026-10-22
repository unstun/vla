# Design

Parent: immutable v284. Owned changes: GPMP source cost wiring; SCAN environmental cost wiring; terrain-layer query in GridMap; local A-star source/header; tracker; reference-mode local replan seed; focused native regressions and version execution/report wrappers. Existing support/raw layer agreement, selection and gap checks remain authoritative.

Use nearest legal same-XY support layers within the existing stair height association bound, seeded by the current adjacent node rather than the start/end sloped plane. Keep exact layer heights in returned geometry instead of treating snapped Z as terrain. Endpoint adjustments are bounded XY proposals on support, tested with their connector tangent and existing full segment checks. No extra local publication veto. Preserve the legacy no-terrain fallback and exact endpoint contract.

Heading scaling remains positive during travel and scales both requested translation and execution phase. The FSM reuses a predicted seed only within 0.15 m and when existing occupancy permits it; otherwise it uses odometry and invalidates the inconsistent warm seed. Final yaw capture, emergency owners and hard validators retain their meanings.

Local repository is the source of truth. Sync only v285/task-owned artifacts to gpu5070ti, verify parent inventories, build in a private execution copy, and freeze identity before scored runs. CPU physics/policy and shared GPU rendering use the already authorized capacity policy. Return compact logs, hashes, reports and regular video files; keep raw recordings remote.

User-proposed timing and optimizer causality are hypotheses; report measurements without promising removal of independent failures.
