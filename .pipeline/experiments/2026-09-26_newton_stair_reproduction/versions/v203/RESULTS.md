# v203 static terrain and startup cleanup

Step 4 is implemented. One static terrain package binds the native PCT map,
selected navigation ground, surface evidence, physical-floor presence and the
negative-only support mask. One runtime node loads the three cloud payloads once
and publishes their distinct, original roles. The default navigation launch owns
that node and derives PCT/SCAN paths and source identities from the same manifest.

LocalMotion's 2D projection timer/publisher has been deleted. TerrainLayer source
and export are removed from the new plugin library. Default Nav2 maps no longer
run terrain or inflation processing. They retain a one-cell, 1 Hz TF/lifecycle
shell with a disabled, input-free stock ObstacleLayer. The no-retry tree's unused
Wait recovery server is removed. The 1 Hz global-planning policy remains for step 5.

## Checks actually run

- Seven ROS packages built; affected controller/bridge rebuilt after the Foxy
  parameter compatibility correction.
- 97 unique ROS component cases passed with zero failures/skips, plus one host
  graph-composition test with fake children. Colcon counts 111 including 14
  enclosing test runners; this is not 111 independent test cases.
- 300 original Tracker command/phase samples still match exactly.
- All original payload bytes match: navigation 86,775 points; surface 126,659;
  physical floor 150,500. Source IDs, point fields, world frame, 3 cm publisher
  offset, physical origin and resolution remain unchanged.
- Real ROS publication passes the advancing-positive-clock gate, late subscriber
  delivery and reset/republication checks for all three topics.
- The actual native SCAN decoder recognizes all three original source IDs and
  point counts. Its original support-gap mask still blocks the sampled recorded
  gap and does not apply that gap to an unrelated height.
- Both real Foxy map shells configure, activate with static TF, return a pose,
  report current state and clean up with the disabled placeholder. Generated
  profiles retain all non-static SCAN parameters; LocalMotion has no terrain-slice
  publisher. The default launch has one static node and no recovery server.
- PCT plugin loading/planning, LocalMotion cancellation and exchange, terminal
  completion, command ownership and no-retry BT regressions pass.
- All 291 composed source files match their authoritative overlays;
  1011 protected v196-v202 files are unchanged. Native plan_env,
  plan_manage, path search and spline optimizer sources are inherited unchanged.

## First-pass findings retained

Foxy's YAML parser rejects an empty plugin array (`No parameter value set`).
Using its disabled stock ObstacleLayer with no observation sources resolves this
without patching Nav2 or implementing a new layer. A zero update rate would also
block Foxy's activation wait, so the one-cell shell retains 1 Hz updates.

Old mission tests were updated for the explicit `terrain_manifest` launch
contract. The initial new launch test used an API absent from Foxy and now checks
its Node construction arguments. A host graph fixture was corrected to compare
canonical macOS paths. The first failing logs/XML are retained separately; all
final checks pass. Existing upstream compiler warnings remain.

No navigation goal, physics step, whole-route experiment, training or robot
actuation was executed. Sensor/3D geometry/support logic is preserved, not newly
qualified by a physical trial. Previous physical/display pointers remain v196/v197.

See BUILD.md, PROVENANCE.md and verification/ for regeneration, hashes, logs,
XML, generated profiles and the source delta. The exported terrain bytes stay in
the disposable execution workspace, not duplicated in the repository.
