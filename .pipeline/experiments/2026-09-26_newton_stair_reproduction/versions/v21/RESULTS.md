# v21 physical result

`v21_building_route01` runs 72.371857 s of continuous recorded simulation.
Net displacement is [0.075420, -2.557766, 0.358702] m. It crosses the previous
v19 stop, but still fails to reach the 5 m short-stair goal. Terminal cause is
`native_replan_exhausted`. Command transport has one connection, no reconnect,
no protocol or I/O error. Measured stop and returned Linux evidence verify.

The new stopping state is under `audits/2026-09-27_v21_frontier`. Component
acceptance in COMPONENT_RESULTS.md remains valid; it did not prove the entire
stair route. No historical full-building reproduction is claimed. Known mapped
low-protrusion semantics remains distinct from the unchanged eight unmapped
obstacle checks.
