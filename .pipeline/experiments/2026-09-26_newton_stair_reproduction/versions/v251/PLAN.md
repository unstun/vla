# v251 — GPMP uses the same oriented physical gap domain

Parent v250. The existing GPObstacle feasibility residual uses the exact
unchanged-radius source-square mask at both oriented cylinder centres. Only
violated hard support produces residual; legal poses have zero residual.
ENV225 remains the sole clearance/centering soft objective. No coordinates,
route names, endpoint motion, added clearance band or new recovery FSM.

Preserve final native full-trajectory and static service checking. Validate
position/yaw derivatives, replay G07 and run unchanged12x5 plus historical H00.

The unchanged ENV225 edge channel must see the same uncertain mesh-gap source
as the hard domain. It now takes the minimum of its original floor-edge margin
and the same oriented cylinder-to-source-square margin. Target .15 m, weights
and original atlas bytes remain unchanged; no soft margin becomes an admission
gate. Both PCT callbacks and SCAN GridMap wrappers pass their pinned gap mask.
This removes a missing-evidence inconsistency rather than adding another cost.
