# Per-case physical execution of frozen v240

Execution parent v241; installed navigation v240; scanner v237; RL/stance v216.
Approved Building generalization task 10-18-v242-building-generalization.

Bind frozen v242 scenarios selected in the approved A/G/R preference order.
One attempt per selected case, at most three, no retry and no historical_full
rerun. Keep source/install, RL, 0.35 m hard guards, 0.1 s original rays and
absolute deadline, native arrival/stop/failure closure and terminal PD unchanged.

The adapter changes only case/run/version identities, scenario loading, and
the explicit cross-floor map-layer selection for the generalization profile.
The original v232 driver infers terminal yaw from the native route tangent.
No goal-yaw override, planner repair, motion-state restoration or warm caches.

Private per-case capture root:
/data/sun/vla_mppi_20261009/trials/v243_CASE_attempt01.
Serial CPU physics, native 6 CPU / 6 GiB, inherited resource/port preflight,
600 s simulation / 900 s supervision. Do not modify any peer job.

Each actual attempt, including a failed prefix, is preserved, analyzed and
rendered from its own original states. All complete recorded-route MP4s return
to the local dated audit's delivered/ directory, with decode/frame/hash/causal
proof and compact outcome metrics. Bulk raw data and build caches stay remote.

No repeated reliability, new-map generalization or baseline-promotion claim.
