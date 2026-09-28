# v24 short-route physical arrival, final PD gate incomplete

`v24_building_route01` records89.962189s continuous physics and4.914198m net
forward travel (XYZ[.165734,-4.914198,.707923]). The native backend returns
`arrived_after_quiescence`; the first captured arrived state is at72.991516s.
The final goal XY error is.200166m, below the existing.25m limit. Minimum body-up
Z is.949523. Source, sensor pairs, applied commands, measured quiescence and
Linux copyback checks verify. The detailed receipt is in the run folder.

The complete acceptance condition fails: no final FIXED_STAND was reached.
All850 post-arrival control frames remain STAND_SETTLING and RL owns the joints.
All850 satisfy zero-command, measured-speed and measured-yaw stop conditions;
83 temporarily exceed the goal distance limit. The PD handoff reasons include
427 tilt,406 four-contact,9 angular-speed and8 linear-speed wait frames. Last
foot forces are[53.67,20.87,0.0,53.97]N. These distinguish physical stopping
from a completed handoff to PD.

The short goal lies within the flight of stairs. The existing hold module
requires tilt<=10deg and all four feet>=10N for a dwell before its torque-matched
transition. No hold threshold or joint-control behavior was relaxed here.
The driver artifact is absent because the physics bound ended before its full
condition; the original review exception is preserved and the diagnostic
missing-artifact review correctly fails it.

The original full-route endpoint is a separate profile. A169-point static mesh
check over a1.2m square around that endpoint finds a horizontal floor at exactly
4.533030510m; this supports testing the original route, not declaring its PD
or navigation outcome in advance. The short-route failure remains recorded.

The v24 video shows actual recorded startup, repeated replanning, motion and
native arrival, followed by ongoing STAND_SETTLING. It must not be presented as
historical full-building completion or final PD acceptance.
