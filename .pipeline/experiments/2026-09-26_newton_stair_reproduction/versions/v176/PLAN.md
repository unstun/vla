# v176: local spline terminal capture

Stage: experiment and analysis. Parent execution: Mac v174 / Linux v175.

The closed v175 attempt05 reached the last accepted curve361 endpoint with about
5 cm error. The 15 cm local finish deadband returned zeros for nearly nine
seconds before the owner failed. During this interval the body drifted in
position and heading; its final measured footprint lacks support at one end.
Attempts02/03 additionally drifted into the pinned negative support mask after
revocation. This change does not claim to solve those separate stop events.

Change only the generated SCAN `finish_dist` from its inherited 0.15 m to 0.02 m.
The 5 cm recovery prefix must not be considered reached merely because it is
shorter than the endpoint deadband. No speed, collision, freshness, stop-proof,
mission-goal tolerance, map, route, start, or locomotion policy changes.

Verify the actual native tracking core on the recorded curve and pose: old
configuration emits zeros; candidate commands reduce the measured endpoint
error; a pose within 1 cm still emits zeros. This is a command counterfactual,
not proof of physical recovery. Verify generated profile and actual loaded graph,
then one complete Mac route. Freeze source and bind all tests to this version.
Only after local qualification create a separate Linux execution version and run
five serial complete routes on gpu5070ti. Preserve failed runs and all parent
versions. Heavy raw artifacts stay on gpu5070ti with verified local provenance.
