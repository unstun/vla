# Frozen native frontier diagnosis

Stage: experiment + analysis. No v6 production source change yet.

Exercise the actual SCAN FSM and manager using the original v5 Building PCT
route, recorded body/LiDAR sequence, static support and last moving spline.
Compile unchanged native manager/FSM sources into the diagnostic executable;
use compiler access-check suppression only for calling their private methods.
Cancel the two autonomous FSM timers so they cannot replace the captured state;
map callbacks remain active. Preserve all native collision/terrain parameters.
Freeze the original simulation clock at the recorded continuation failure.

First reproduce getLocalTarget/reboundReplan rejection twice with the same
inputs. Only then test ranked causes. Do not modify frozen v5 source, numerical
limits, sensor points, route goal, control or watchdogs. A behavior repair must
be frozen under a new v6 source identity before execution.
