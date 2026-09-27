# v4: connect the established PD/RL chain to the complete Building

Stage: experiment + analysis. Parent: v3. User authorization: try the previous
complete floor scene and start sequential versioning at v3.

One change: add an explicit `building_full` scene that combines the original
Building mesh/PCT map with the existing factory-to-PD-to-RL control chain.
Use the original archived spawn, heading and goal; start at the existing
0.14 m crouch clearance above the recorded ground. This first scene condition
contains fixed architectural geometry and no added pedestrian. Preserve the
original `building` moving-human profile and every v3 flat profile.

The behavior belongs at `StairRobot` construction and scene selection in
`run_local_episode.py`, `newton_episode.py`, `native_graph.py` and
`render_episode.py`. Reuse the long-route driver for measured PD readiness,
native arrival and final two-second PD hold. Reuse the existing captured-state
sensor path for this static geometry. Keep original factory, hold, policy,
native planner, map, controller and freshness thresholds. The Building requires
the existing triangle-contact Warp CPU path and its already available automatic
contact budget; native flat-plane physics would not reproduce this geometry.

First run a bounded actual factory/start/PD hold probe in Building. Require
measured support, upright standing, continuous time and unchanged Building
geometry. Then run the complete native PCT/SCAN loop for at most 90 physical
seconds, 600 goal wall seconds and 1700 worker wall seconds. Arrival requires
the original goal and tolerance, native `arrived`, no fall and final PD hold.
Retain failed or incomplete trials and render their actual recorded states.
No claim of wall-contact-free navigation follows without corresponding scoring.

Freeze v4 code/configuration before the first test. Any subsequent logical fix
gets v5 or later; do not edit the v3/v4 source snapshots. Display-only changes
also receive their own version if made after this version is frozen. Trial
results and version index status may be appended without changing source.
