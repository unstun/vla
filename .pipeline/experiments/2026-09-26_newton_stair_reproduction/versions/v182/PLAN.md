# v182: minimum operating-speed correction

Stage: experiment + analysis. Dr Sun corrects the active diagnosis: the minimum
walking-speed condition matters. The existing project contract specifies0.6m/s
planned horizontal cruise; v179tested0.2/0.35/0.5, all below that operating
requirement. Retain v179as low-speed controls, not nominal-range qualification.

The single experimental change from v179 is the walking-command amplitude:
0.6/0.8/1.0m/s, two cases each on flat and stairs. Keep first-walk durations,
10s stops,3s restart, starting geometry, current model, all gains, smooth startup
and hold detachment identical. Record measured cruise speed separately;0.6m/s
command is not proof of0.6m/s actual motion. Stop commands remain exactly zero.
Twelve serial new trials; no controller, model or training changes.

Matched flat pairs change only command amplitude on homogeneous ground. Stair
pairs naturally stop at different physical positions, so stair differences are
not a controlled single-cause estimate. Report that confound explicitly rather
than claiming minimum speed alone explains all drift. All failure evidence and
old videos remain. No overwrite or relabelling of v179as nominal-speed tests.

The archived training sampler has a dynamic per-axis lower bound. With9mtiles,
0.5mborders and25sepisodes, its initial ordinary branch is approximately0.200m/s
per horizontal axis (about0.283m/s vector norm when both axes are sampled).
The bound depends on remaining commanded distance and time and can change; later
special branches override components. This is distinct from the project's0.6m/s
planned-cruise operating rule. Neither is a universal minimum for a zero stop.

Local Mac execution uses the same bounded temporary root and resource guards
as v179. New IDs v182_flat01..06 and v182_stairs01..06. Durable raw target is
`gpu5070ti:/data/sun/vla_mppi_20261009/policy_stop_v182_mac/`. Expected compact
returns plus videos<150MiB; retain raw in the authorized2GiBtemporary budget.
No navigation, formal training or real-robot actuation. Compare above/below-bound
approach speed to test the user's hypothesis, without assuming it is proved.
