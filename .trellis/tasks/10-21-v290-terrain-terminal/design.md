# Design

Preserve an immutable v289 parent and create v290. Terrain availability selects the internal neighbor representation independently of exact endpoint admission. Exact start remains the requested measured XYZ; terminal success still requires an explicit collisionFreeSegment to the exact requested end. Neighbor cells use terrainSupportHeight, with one immutable exact elevation per reached voxel.

Endpoint adjustment uses one proposal rule: in terrain mode each XY step is reprojected to the associated support layer and checked at legal local headings; failure remains failure, never a hidden switch to a sloped plane. The no-terrain branch retains the legacy bounded chord adjustment. Do not modify raw obstacle decisions to compensate for bad search heights.

Terminal approach uses the existing kp_pos distance law as a speed ceiling before the unchanged capture band, with matching effective phase advancement and original slew. Same-floor/Z association prevents slowdown from an overlapping other floor. Original final-yaw centering/PD and goal tolerances remain intact. Verify captured motion and commands, not just final zero-command state.

Owned native files: path_searching dyn_a_star.cpp/header (mode and exact-start storage); scan_nav2_controller tracking_node.hpp (terminal velocity/phase); corresponding terrain/repair/tracker tests. Additional production changes require captured evidence and a stated scope update. Full clean dependent-package rebuild if public layouts change.

Rollback: discard v290 execution copy; frozen v289 stays byte-identical. No physical acceptance claim without a separately completed physical cohort.

## Captured-contributor finding and bounded repair
Captured prefixes show tread/riser and underside returns retained as nonterrain contributors, including cells later labelled terrain. Keep raw history and occupancy unchanged. The existing selectedGroundReturn now recognizes the same legal adjacent-tread interval from either side, using only selected terrain and the unchanged ETH radius/step bound. rawContributorOccupancy excludes only source voxels whose entire vertical extent is below the query-associated selected support floor; full footprint support/freshness still gates the result. Above-floor boxes, walls and overhangs retain refusal. No physical-floor-presence-as-classification cast, mesh call, new classification threshold, history erasure or extra field/cache is introduced. This is the original requested inflated-obstacle investigation, resolved at the contributor owner. Native header changes require rebuilding dependent packages before replay.
