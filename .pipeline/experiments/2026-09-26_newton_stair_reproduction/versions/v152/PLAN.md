# v152 recorded replacement-planning diagnosis

Stage: experiment + analysis. Read-only comparison of frozen native v147 and
v151 against the v150 original Linux attempt09 input prefix and curve2366.
Restore the original generation7 PCT reference and curve PVA, then exercise the
actual native manager/FSM cold replacement path. No runtime algorithm change.
This excludes the original warm hint, asynchronous map batching and executor
schedule; it is a bounded numerical/geometry diagnostic, not physical recovery.
Keep retry, collision, support, freshness, PVA, dynamics and stop limits unchanged.

Ranked hypotheses: (1) denser validation catches the bad curve but cannot find a
replacement; (2) reference window/seed state causes a poor local target; (3) seven
separated safety stops exhaust the finite mission policy after prior progress.
The existing mission retry count will not be reset or increased in this probe.
Also audit coupling: makeWarmStartSeed uses validation sample count to construct
its initializer, so v151 changes warm seed density as well as safety work.
