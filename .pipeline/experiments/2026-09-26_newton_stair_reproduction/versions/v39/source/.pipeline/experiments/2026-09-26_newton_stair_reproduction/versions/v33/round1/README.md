# v33 round-1 candidate, as independent review round 1 saw it

Copies, with their modification times, of every top-level file in `versions/v33/` when review round 1 returned
(`../independent_review_round1.json`, failed). The round-1 runtime bytes are recorded by `changes.patch` and
`prepared.json` here. They were restored to their v32 preimages before `materialize.py` was run again for round 2.

- **Scripts and plans:** `materialize.py`, `check_change.py`, `gate_contract.py`, `replay_gate.py`,
  `ros_smoke.py`, `run_ros_smoke.sh`, `freeze.py`, `PLAN.md`, `PHYSICAL_RUN_PLAN.md`, `COMPONENT_RESULTS.md`.
- **Outputs:** `prepared.json`, `changes.patch`, `check_change.json`, `gate_contract_mac.json`,
  `gate_contract_container.json`, `replay_gate.json`, `ros_smoke.json` and `ros_smoke_stdout.log` (K5 attempt 3,
  which overwrote attempts 1 and 2).
- **Unchanged since round 1, not copied:** `building_planner.yaml`, `flat_planner.yaml`, `evidence/` and
  `parent_source/` (round 2 added `parent_source/setup/runtime_sources.json`).

Round 1's `COMPONENT_RESULTS.md` and `PLAN.md` contain statements that are wrong. They are kept as reviewed and
corrected in the round-2 files:
- the three runtime files "had not changed since their import", and "none had been in a version manifest before";
- `PLAN.md` K5 "was revised to match before the passing run".
