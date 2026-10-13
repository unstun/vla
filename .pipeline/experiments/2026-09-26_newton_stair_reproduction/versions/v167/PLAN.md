# v167: explicit short backward recovery without an in-place turn

Stage: experiment and analysis. Native and Mac host parent: v164. In the recorded
v165 attempt01 stop, the current body heading is clear, but intermediate headings
needed for turning are blocked by the unchanged support-gap mask. A 5 cm backward
curve at the current heading passes the actual native manager, full fixed-heading
collision check, boundary PVA and dynamics (0.607 s, 306 samples).

Add an explicit reverse_motion field to the internal Bspline message and rebuild
all consumers. Only a short stopped steering prefix can set it. For the backward
proposal, check the current orientation instead of asking for a 180-degree turn.
Retain all normal planning checks and additionally check its entire curve at the
measured heading. Discard an unpublished candidate cleanly if that check fails.

The tracker uses tangent+pi only for flagged prefixes, retaining measured heading
when direction is degenerate. The symmetric two-cylinder footprint is unchanged
by pi; do not generalize this assumption to an asymmetric footprint. The controller
rejects flagged control polygons longer than10cm or non-stopped boundaries. Normal
paths, goal yaw, limits, source freshness, ownership and measured-stop gates stay
unchanged. This is internal direction intent, not a new robot command protocol.

Require actual old-controller turning versus new-controller backward-command
regression, normal replacement reset, invalid reverse rejection, three recorded
native map cases, complete package rebuild and graph checks. Freeze before local
original-start physics; only afterward run a new Linux repetition cohort. The
v166 Linux port-isolation change is separate and must be retained in that port.
