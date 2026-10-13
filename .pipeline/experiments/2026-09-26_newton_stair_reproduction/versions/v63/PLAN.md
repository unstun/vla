# Propagate failed optimizer repair

Stage: experiment + analysis. Continue Dr Sun's authorized planner repair on the Mac while gpu5070ti is busy.

Remove the repeated failed obstacle-constraint initialization diagnosed in the v59 81-second spike. Keep final goal, yaw, PVA/dynamics, occupancy/support and stop behavior unchanged. Add no solve deadline or v49 mechanism. Keep frozen predecessors immutable and preserve failed attempts. Acceptance: complete native build; actual parent/candidate optimizer-flow regression showing three failed repair searches become one while clear initialization and successful repair remain valid; inherited Mac native/controller/cache/recorded warm/PVA/backend checks. Full corner and physics acceptance remains pending its original remote inputs.

# Design

Native parent is frozen v62, whose Mac subset passes but full qualification remains pending. Add an optional initialization-status output to the existing path-vector API; no-collision empty paths remain success. Mark the two existing error returns as SearchFailure or InvalidSearchPath. In rebound_optimize's existing collision-repair branch, return its original unsuccessful result immediately if initialization failed; do not repeat optimization with unusable constraints. Useful initialization retains the existing restart/weight schedule. Initial manager calls and every outer warm/native/fixed-height/prefix fallback remain unchanged. Only bspline_optimizer.h/cpp are owned production files. No success bypass or cache reuse across maps is added. Tests compile actual parent/candidate optimizer/LBFGS code with scripted occupancy/search outcomes; this establishes error propagation, not real map or tail-latency acceptance. Recorded Mac safety fixtures still use the full unchanged native map/search.

# Execution

1. Preserve v62 source identity and create v63 source-only copy.
2. Add status propagation at the existing initialization-error and rebound-repair branches.
3. Compile/run parent and candidate flow regressions; compare failed-search count and result, and cover empty clear paths, short search paths and useful repair.
4. Build all packages in cached Mac Docker image; rerun inherited Mac/recorded contracts. Keep build products ephemeral and return compact provenance.
5. Record partial qualification honestly; full corner/physics/30 Hz remain pending. No commit, broad staging or remote execution.

Applicable specs: backend quality-guidelines, newton-versioning, newton-stair-repair-contracts, code-reuse-thinking-guide. Existing fix authorization and Mac continuation cover this local error-propagation correction; no new goal/stop/safety decision is introduced.
