# Pinned speed references and reuse

The two inspected Nav2 source files are Apache-2.0 according to their own file
headers, at commit `3c3db59d6969d8ecee8e68468693d006397f4a0c`:

- [MPPI velocity-deadband critic](https://github.com/ros-navigation/navigation2/blob/3c3db59d6969d8ecee8e68468693d006397f4a0c/nav2_mppi_controller/src/critics/velocity_deadband_critic.cpp):
  scores velocity below configured deadbands; it is a soft preference, not a
  guarantee of measured minimum robot speed.
- [Regulated Pure Pursuit](https://github.com/ros-navigation/navigation2/blob/3c3db59d6969d8ecee8e68468693d006397f4a0c/nav2_regulated_pure_pursuit_controller/src/regulated_pure_pursuit_controller.cpp):
  `applyConstraints` applies a minimum translational speed, then separately
  applies approach slowing and the desired-speed maximum (lines 636-673).

These are **surveyed references**. Their ROS controllers were not imported or
run. No Nav2 runtime/dependencies were added. The local adaptation uses the
travel/approach distinction on the timed SCAN curve, rather than replacing its
controller. Local changes are in `native_changes.patch`.

The executable reallocation is the existing pinned SCAN code:
`SCANPlannerManager::refineTrajAlgo` -> `reparamBspline` ->
`UniformBspline::lengthenTime`, followed by the existing boundary-PVA fit,
optimizer refinement and final feasibility/collision checks. SCAN's original
upstream reference remains commit `348e8a590a50a5a6bbab8d8c6dcfd171f009be26`,
Apache-2.0; v6 is the local integration parent.

`upstream_reference/source.json` records exact download URLs, hashes and sizes.
The first web raw fetch had a cache miss; a direct GitHub download succeeded.
One requested newer-layout RPP header did not exist at this pinned commit (404);
the actual implementation above was inspected instead. No missing file was
invented or substituted with an unpinned implementation.

Build and run instructions for this local adaptation are in `RESULTS.md` and
the retained per-attempt request/inside scripts. The original Nav2 controllers
require their normal ROS/Nav2 plugin infrastructure; no upstream reproduction
claim follows from reading these two files.
