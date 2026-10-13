# v186: retain small recovery movement; stop only stalled terminal correction

Stage: experiment and analysis. Linux parent: v185; v177 remains the prior
full-route baseline. v185 finished only3/5 routes and fails its prospective
endpoint-tail criterion in attempt02 (2.219s). Do not adopt v185. Its two
navigation failures followed zero-command intervals and six missing-trajectory
retries; their exclusive cause is not established by a paired physical replay.

One behavior refinement: restore the original2cm local capture distance. Keep
the per-curve completion latch. While an expired curve remains inside3cm, let
ordinary correction continue if the measured body advances more than5mm. If it
cannot move5mm for1s, latch zero for that curve. A new accepted curve resets
this state. Log each actual capture with owner, curve, reason and endpoint error.
This adapts Nav2 SimpleProgressChecker's movement-radius/time pattern to a
local terminal region; its numeric thresholds are this experiment's values,
not claimed upstream defaults or RL training limits.

RL model, observation scaling/history, stance hold, physics, gains, map, start,
mission tolerances, PVA/collision/freshness gates and retry budget stay unchanged.
A local completion latch never claims the robot is physically stopped. Keep
measured stop proof before replacement owners. Do not increase every tiny
command to0.6m/s or modify the policy.

Native checks: the recorded4.9246cm recovery still commands inward motion;
2.8cm does not stop immediately; a measured6mm advance renews the1s window;
0.5s of no progress does not stop;1.1s of no progress at2.19cm does stop.
Retain new-curve resume, default-off behavior, cancellation, stale-generation,
emergency and mission-yaw regressions. Verify loaded controller/profile and
package counts before freezing. Record source difference and run IDs.

Then run five serial complete original Building/historical_full routes on
admitted gpu5070ti. Reuse v185's prospective endpoint criterion (continuous
expired-curve correction inside5cm, actual nonzero RL horizontal command below
0.1m/s, over2s fails) and original full-route verification. Preserve all failed
runs. Inspect zero-command drift independently; arrivals alone do not qualify.
If the criterion is found insufficient, record that finding rather than changing
its definition retrospectively. Never pool the historical and new cohorts.

Local VLA source is authoritative. Verify frozen source and input hashes on the
remote execution copy. Raw captures remain on gpu5070ti; return compact metrics,
actual command evidence and hash provenance locally before reporting results.
