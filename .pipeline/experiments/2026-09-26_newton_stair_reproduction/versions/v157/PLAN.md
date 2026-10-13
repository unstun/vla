# v157 body-aligned lattice retry for an isolated start

Stage: experiment + analysis. Native parent v151; host parent v154.
v156 reproduces stationary failure on776original published scans: all eight
original grid edges reject. Finer directional probes find legal5–20cm paths
while ground-gap constraints still forbid the nominal outgoing direction.
The gap mask, not a terrain-inflation waiver, causes the rejected headings.

One proposed change: after exact planar AStar exhausts with only its start
expanded, retry the lattice aligned to the fresh measured body heading. Keep
the same total200ms deadline, pool size, resolution, exact endpoints and every
native edge/support/collision check. Successful ordinary searches are unchanged.
World-axis bounding certificates apply only in the original frame; rotated
search still checks each world-space edge. No rotation/sideways execution mode
or ground-gap relaxation is introduced. All ordinary spline PVA/dynamic/final
checks remain mandatory. Native and captured-replay regression must pass before
freeze and full original-route physics. v155warm-seed draft remains unbuilt.
