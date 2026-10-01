# Source and adaptation boundary

- Repository: https://github.com/ompl/ompl
- Version1.7.0, commit eabb4d0f825666e4553a2ec0ecb9c7a5a33637dd.
- Source: `src/ompl/geometric/src/PathSimplifier.cpp`, lines141-150.
- License: BSD-3-Clause, source copyright2011 Rice University.
- Local pristine source, license, tag receipt and hashes:
  `references/upstream/2026-09-27_ompl_seed_shortcut/`.
- Original API: `PathSimplifier(space_information).reduceVertices(path)`;
  OMPL supplies state allocation, interpolation and checkMotion through
  SpaceInformation. The upstream repository README/build instructions remain
  authoritative for running the complete OMPL library.
- Local adaptation: only its deterministic whole-path endpoint branch is used
  with Eigen value-owned vertices and SCAN's existing complete segment predicate.
  No OMPL binary/dependency, randomized reduction, new planner or new collision
  model is introduced. Existing Eigen/C++17 and ROS2 build remain sufficient.
- Local execution: `versions/v27/materialize.py`, then the existing bounded
  `repairs/2026-09-26_generic_occupancy/build_candidate.py` with scan59 and the
  scan58 incremental cache. Original search and final checks stay mandatory.

This is a small inspected source adaptation, not a claim that the OMPL library
or its general motion-planning results have been reproduced in this project.
