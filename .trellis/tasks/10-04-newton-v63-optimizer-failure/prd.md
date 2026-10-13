# Propagate failed optimizer repair

Stage: experiment + analysis. Continue Dr Sun's authorized planner repair on the Mac while gpu5070ti is busy.

Remove the repeated failed obstacle-constraint initialization diagnosed in the v59 81-second spike. Keep final goal, yaw, PVA/dynamics, occupancy/support and stop behavior unchanged. Add no solve deadline or v49 mechanism. Keep frozen predecessors immutable and preserve failed attempts. Acceptance: complete native build; actual parent/candidate optimizer-flow regression showing three failed repair searches become one while clear initialization and successful repair remain valid; inherited Mac native/controller/cache/recorded warm/PVA/backend checks. Full corner and physics acceptance remains pending its original remote inputs.
