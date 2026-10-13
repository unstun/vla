# Recorded native check result

The unchanged nativev147library reproduces the recorded decision change on
curve2366: full interval clear, remaining interval beginning24.986267mslater
blocked. Holding the earlier body pose still rejects. Rechecking the full
interval at the later clock/body returns clear. The first blocked position is
[8.6042116106,4.4788738110,4.6500788655] at curve time1.601651779s.

This isolates a narrow unknown-obstacle voxel rejection missed by the first sample
grid and found after the grid changes with begin_s. It does not establish every
full-route failure's cause or a recovery fix.935published scans are reconstructed;
the live mapper counted931. That startup discrepancy and synchronous replay
boundary remain disclosed; the actual clear/blocked pattern was reproduced.
Both selected body sample timestamps match their recorded safety timestamps.

Candidatev151adds nested samples without removing any original sample. Its
header probe rejects this curve before motion and retains the later rejection.
Actual planner/full-route validation is separate and still required.

2026-10-12 terminology correction: native `Verdict::UnknownObstacle` is enum6;
`voxel=0` means unknown occupancy. The logged `support_z` is the adjusted terrain
query height, not a support failure code. The earlier support-clearance label
was incorrect. Sampling counterfactuals and recorded decision results are unchanged.
