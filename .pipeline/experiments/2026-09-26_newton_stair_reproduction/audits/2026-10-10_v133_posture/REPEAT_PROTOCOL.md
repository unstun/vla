# v135 fixed comparison

Only start after all three fixed v135 candidate pilots finish with native
arrival, measured final PD hold, no fall, verified copyback and retention.

Both arms share frozen v135 host, the original Building scene, original task,
policy, clock/sensor/stop conditions, pinned x86 Foxy image and gpu5070ti host.
Baseline is native v133 with the original PCT map and original map identity.
Candidate is exact native v134 with its static support veto, coupled to the
v135 PCT cost map and separate `stair_reactive_coverage_v135` identity.

Six fresh trials per arm, sequential, in ABBA blocks:
A1 B4 B5 A2 / B6 A3 A4 B7 / A5 B8 B9 A6.
Each trial keeps the existing 90 simulated-second and 540 wall-second bounds.
No replacement, selection of favorable seeds, threshold changes, or concurrent
heavy analysis/builds. Runs that fail navigation remain in the denominator.
Execution or evidence-retention failure stops the batch for inspection.

Acceptance for this bounded scenario: candidate 6/6 arrivals with measured PD
hold, zero falls, all replacement owners preceded by original measured-stop
proof, and all source/input/copyback/retention gates pass. Baseline counts are
reported as observed, without a population reliability or causality-over-all-
failure-modes claim. The first three pilots are separate, not part of the six.

Main 30 Hz, arbitrary environment, sensor-only unseen-gap detection, Jetson and
real-robot acceptance remain separate. No policy or collision mesh is changed.
