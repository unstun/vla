# v134: static subcell support-gap veto

Parent: frozen v133, native and host. Stage: experiment + analysis.
Dr Sun authorized continued diagnosis, repair and repeated gpu5070ti trials.

The v133 failed second pilot loses left-front foot support in a roughly 7 cm
Building floor seam. Recorded foot z falls from 4.548 to 4.264 m between
36.492 and 37.491 s, before the final safety stop. Original mesh intersections
and static samples expose that seam; the 10 cm PCT height cell falsely covers it.
Changing PD timing cannot supply the missing floor.

One behavior change: add a negative support veto derived offline from the same
pinned static Building mesh used to construct the existing simulation map.
Test each original physical-floor cell at 16 uniformly spaced subcell centers.
A ray needs a triangle within the existing 0.26 m step-height bound. A missing
sample marks partial coverage. Inflate partial cells by the existing 0.35 m
cylinder radius, conservatively accounting for cell extent. The native common
collision entry checks this immutable negative mask before its existing checks.
The mask can only reject; it cannot supply support or waive live occupancy,
body/map freshness, trajectory, ownership or measured-stop requirements.

Scope boundary: this is a simulator static-map correction. All static surfaces
and existing floor layers are processed, with no route-specific coordinates.
The live planner never reads the mesh, robot feet or future recorded states.
No claim is made that a robot without this map can detect an unseen floor gap.
The finite 25 mm sampling is not proof against arbitrarily small holes.

Owned changes: versioned plan_env gap-mask helper and loading/query seams,
offline generator, explicit pinned mask receipt, candidate planner parameters,
and host receipt/tests for this new input. Physics, policy, scene, source stamps,
PCT navigation and surface payloads, and original safety criteria are preserved.
Baseline is now immediate parent v133, not native v114. Both arms share v134
host and original scene; the baseline ignores the added candidate-only parameter.

Validation: actual old/new native map query from the captured unsafe pose,
synthetic gap/solid/stair and malformed-mask cases, component and graph checks.
Then three fixed candidate pilots. If all arrive without falling, six fresh
trials per arm in ABBA order, all retained. Any failed pilot halts promotion
and is diagnosed before further changes; no replacement of failures. No full
acceptance or baseline promotion merely from a version number or component test.

Heavy generation/builds/captures remain under /data/sun/vla_mppi_20261009.
Local source, compact reports, hashes and review imagery are authoritative.
