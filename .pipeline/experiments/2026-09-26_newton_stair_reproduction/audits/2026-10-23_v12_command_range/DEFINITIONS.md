# Phase A frozen definitions — 2026-10-23

These definitions are prospective for the new command-range extraction. Historical reports were read;
new terminal command-band/pure-yaw metrics have not been extracted. Freeze this document with source,
request and tests before running `extract01`.

## Cohort and identity

Exactly ten v290 attempt01 runs from the frozen v290 physical selection plus the 24 entries, in order,
in the paired campaign's request. Preflights are excluded. Every requested run gets a result, including
missing/malformed recordings; missing metrics are null, never zero. Compare every file read against
its historical capture/analysis hash and byte count. Any mismatch rejects that run's new analysis.
Retain its error receipt. Do not launch or rerun simulation. Originals are read-only.

## Clock, applied command and measured motion

Use `telemetry.jsonl`: actual `effective_command=[vx,vy,wz]`, `physics_time_s`,
`body_sensor.position`, `quaternion` (wxyz), `linear_world` and `angular_world`.
Commands are body-frame m/s and rad/s; measured XY speed is the norm of world XY linear velocity.
Rotate commanded XY by measured body yaw to obtain its world direction for signed velocity projection.
Also report absolute perpendicular speed: transverse drift is not commanded-axis tracking.
Measured world angular Z is a separate rate; integrated heading change uses wrapped quaternion-yaw
increments, not an assumption that world angular Z equals Euler yaw derivative on tilted ground.

Require strictly increasing finite timestamps and finite used fields. The sample at t[i] owns
[t[i],t[i+1]); clip to the terminal window. Means and shares use actual interval dt, not row counts.
No extrapolation after the last sample. Report maximum dt and gaps >0.04 s (twice nominal policy period);
such intervals retain their actual duration and are disclosed. This is recorded-telemetry coverage,
not a claim of uninterrupted 50 Hz sensing. Positions for drift are sampled, not continuous extrema.

## Terminal window

Navigation starts at the first driver's `goal_request.initial_snapshot.sim_time_s`.
If unavailable, use the first `video_states` sample with `goal_sent`; record that fallback.
Missing both makes the window unavailable. Ignore pre-goal factory/idle zero commands.

Start at the first telemetry sample at/after goal request with XY distance <=0.25 m from the requested
goal, regardless of Z/yaw. This is the PRD's XY circle, not the prior stop audit's XYZ acceptance.
If it never enters, start ten simulation seconds before the first effective all-zero command after
goal request, clipped to the first post-goal telemetry sample. All-zero uses the inherited criterion
max(abs(vx),abs(vy),abs(wz)) <1e-9. Report `fallback_before_first_zero` explicitly. If neither an entry
nor such a zero exists, the window is unavailable. End at the final telemetry timestamp. An entry
only at the final sample has zero observed duration and unavailable shares, not a passing zero.

## Translation bands

Let s=hypot(vx,vy), with no rounding or speed epsilon. Disjoint main bands:
`zero`: s==0; `below_0p2`: 0<s<0.2; `exact_0p2`: s==0.2; `above_0p2`: s>0.2.
The denominator is all terminal-window time, including stops and pure yaw. Also report nonzero-time
shares separately. The PRD's inclusive shares are (below+exact)/all and (exact+above)/all, so they
intentionally overlap at exactly 0.2. Keep exact-0.2 separately; do not silently change either bound.
Fine bands are zero, (0,.05], (.05,.10], (.10,.15], (.15,.20], (.20,.25], (.25,.30], (.30,.40], >.40 m/s.

For every occupied band, report duration, dt-weighted command speed, measured XY speed, signed
command-axis speed, perpendicular absolute speed, and ratio of integrals (axis distance / commanded
distance). The ratio is not a mean of per-row ratios. Zero-command bands have null directional ratio.
These terrain/transition mixtures cannot select the flat-ground B6 speed floor or establish steady
tracking. Cross-run aggregate ratios are also ratios of summed integrals, with counts disclosed.

## Pure yaw

Require exactly vx==vy==0 and abs(wz)>=1e-9. A residual translation, however small, is not a pure-yaw
command. Maximal contiguous qualifying samples form an interval; split a sign reversal, but not a
change in yaw magnitude with the same sign. Clip intervals to the terminal window. An interval that
started earlier is left-censored; one still active at recording end is right-censored. A final-row-only
command has zero observed duration and is retained. A zero-duration row does not contribute averages.

Report every interval's source-row boundaries, start/end/duration, signed mean/min/max applied yaw,
measured world-Z mean, signed integrated heading change, sampled maximum and net XY displacement
from its start, and stance modes. Include the sample at the command-change endpoint for displacement:
it is the end of the preceding held command. For a window boundary between rows, interpolate only
position/yaw for that boundary and disclose the interval clipping. This interpolation is not a new
sensor observation. Report total pure-yaw time, longest interval and largest displacement per run.
No interval means zero duration/count with no maximum-drift observation (null).

## Interpretation and preservation

Keep scanner-failed prefixes and later recovery stops; do not call geometry-clear prefixes complete
routes. This audit does not reclassify old success/failure. Annotate the previous outcome from frozen
reports separately. Every interval is visible; do not choose only a favorable stop/turn.
The 0.2 m/s training exclusion was corrected at Step 0: saved dynamic sampling bypasses that branch.
Phase A measures commands and observed body motion; Phase B must determine usable speed/yaw/stop numbers.
