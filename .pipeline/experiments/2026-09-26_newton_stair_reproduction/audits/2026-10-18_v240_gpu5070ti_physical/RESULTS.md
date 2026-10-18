# v240 / execution v241 — one full physical route passed

The sole authorized gpu5070ti attempt passes the original route, arrival and
measured-PD gates. The two demonstrated approach emergencies and measured
>=0.5s pauses are absent. No physical retry was performed. Native source is
frozen v240; v241 binds its actual install to the original v232 graph/driver,
v237 scanner repair and v216 locomotion. Selected baseline remains v232/v233.

## Original-route and window evidence

| Metric | v237 | v240 / run v241 |
|---|---:|---:|
| Terminal result | FINISHED | FINISHED |
| Recording closes, physics seconds |124.223358|121.424896|
| Measured final PD hold |4.377594s|4.357605s;219 samples|
| Final XY error |0.118992m|0.115871m|
| Final yaw error |0.120769rad|0.068466rad|
|109–115s completed successful rounds |121/125|168/169|
|109–115s emergency publications |2|0|
|109–115s measured pauses >=0.5s |2|0|
|109–115s maximum measured low interval |0.659637s|0.271423s|
| Route-relative approach cumulative low time |1.219330s|0s|
|45–55s completed successful rounds |296/296|273/274|
|45–55s emergencies / pauses >=0.5s |0 /0|0 /0|

The raw fixed109–115s window is retained. The new run begins normal near-goal
STAND_SETTLING at114.668610s, with0.271423s low speed overlapping the end of
that fixed window. This is the original goal closure, not the old two approach
interruptions at2.6–2.8m remaining. The independently reported route-relative
approach spans108.851807–114.668610s: zero low-speed interval, emergency or
expired-active-curve gap. Old approach begins109.091675s and enters normal
goal stance at117.307159s, after the two emergency interruptions. STAND_SETTLING
continues to use RL; the measured speed, not the stance label, defines pauses.

Both fixed windows have continuous active-curve coverage before normal goal
closure. Failed nominal replans remain in the bill and retain valid previous
curves. Different round counts reflect actual execution and scheduling, not a
paired identical-round benchmark or proof of sustained30Hz. Mean successful
planning is25.325Hz; original full_qualification=false is preserved.

The final height error is0.008771m. All1104 scans complete under the unchanged
100ms deadline; maximum30.465ms, zero deadline failures. Original RL SHA7030ba47…,
ENV225 SHA7ec06542…, start/goal,0.35m collision/support and0.1s captures are
verified unchanged. The v237 deadline repair is reused without modification.

## Stair edge-margin comparison

| Actual-body ENV225 metric,45–55s | v237 | v241 |
|---|---:|---:|
| Known-floor samples |100/100|100/100|
| Minimum extra edge margin |0.150m|0.129810m|
|5th percentile extra edge margin |0.150m|0.149882m|
| Samples at0.15m capped target |100%|95%|
| Known samples with negative margin |0%|0%|

The new route retains positive edge margin and zero measured stair pauses,
with a slightly smaller minimum margin. This is retained as a real difference;
one trial cannot identify its unique cause. The metric uses actual body yaw/
height against the same frozen field and0.35m envelope, capped at an extra
0.15m. It is body geometry evidence, not individual-foot contact evidence.

## Source, videos and claim boundary

Work commits: b709a7d6 (v238 attribution/repair), e5f640ba (v239 rejection and
v240 repair/gates),80d4f74a (frozen v241 execution binding). Preflight verifies
all14 package prefixes, the six rebuilt v240 packages and inherited v232
interfaces/bridge/PCT, actual linked v240 core/ABI, original policy, scanner,
generated profile and12-second graph. Post-run source/install parity passes.
The create-exclusive launch ledger authorizes and records one attempt.

The original raw archive stays remotely at
`/data/sun/vla_mppi_20261009/trials/v241_linux_full_attempt01/runs/v241_linux_full_attempt01/raw_capture.zip`.
Its1108 members are verified; local delivery contains compact receipts, logs,
summaries and videos, with no compiler cache or raw cloud. v237 source/video
bytes remain unchanged. Native and host parents are mounted read-only.

The individual video retains the complete first/last recorded state, all
pauses, causal curve events and measured terminal stance:3636 frames,30fps,
full decode verified. Two-column comparison uses common physical time and the
latest actual frame at or before each time; no interpolation. A finished
recording becomes a labelled black panel rather than a fabricated stand hold.
Full,45–55s and109–115s comparisons have separate frame-mapping/decode proofs.

- [Full recorded route](delivered/v241_full_attempt01.mp4)
- [Full v237 / v241 comparison](delivered/full_physics_comparison.mp4)
- [Stair comparison45–55s](delivered/stairs_physics_45_55.mp4)
- [Approach comparison109–115s](delivered/terminal_physics_109_115.mp4)

[Window audit](results/window_audit.json),
[original route gate](results/full_route_verification.json),
[measured PD](results/terminal_pd_hold.json),
[body edge margin](results/body_edge_margin_comparison.json),
[source parity](results/post_run_source_parity.json),
[delivery manifest](results/return_manifest.json).

This is one successful original-route physical validation with improved
approach continuity. It establishes neither repeated reliability nor other
maps/start points, sustained30Hz or a baseline-selection change.
