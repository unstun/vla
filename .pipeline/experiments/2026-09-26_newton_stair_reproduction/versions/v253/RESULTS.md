# v253 — Continuous endpoint attachment (offline qualified)

Parent frozen v251. Physical-mode start/goal are transient real-coordinate
nodes connected only to the ordinary one-cell grid neighbourhood. Dense 0.35 m
swept support, legal floor transitions and ENV225 score the actual entry/exit
segments. Search output and both GPMP orders retain real endpoint anchors.
No endpoint motion, scene branch, threshold change or new recovery protocol.

- Recorded v252 A02 request: first GPMP + complete static review pass;
  requested/returned start and goal XYZ error are both exactly zero.
- Unchanged 12x5 matrix: 55/60 first GPMP/static/cold SCAN passes, no admitted
  graph fallback. B09 remains 0/5 and stays in the denominator.
- Historical H00: first GPMP/static/cold SCAN pass, zero endpoint goal error.
- 97 native tests, complete 47-case PCT rerun and 10,855 support parity checks
  pass; both native support mismatch counters are zero.

The initial frozen source/build receipt contains 46 cases because preserved
source mtimes retained a three-case test object while its source contained four.
Rebuilding that test from identical frozen bytes gives the complete 47-case
rerun in `results/qualified_pct_unit`; the initial receipt remains unchanged.
Installed planner files, source and evaluator hashes stay frozen.

Final review found the new legacy distance branch used integer norm. This does
not affect configured physical mode, but v254 restores the original floating
sqrt(2) cost and adds a behavioral regression before physical validation.
v253 is preserved offline evidence, not the physical execution treatment.
