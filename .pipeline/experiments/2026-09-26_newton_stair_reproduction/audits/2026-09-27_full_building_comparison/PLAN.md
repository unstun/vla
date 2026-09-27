# Full Building regression comparison

Stage: experiment + analysis. Requested by Dr Sun on 2026-09-27.

This is a diagnostic review, not a production repair. Preserve v7 and the
historical sibling checkout. Reuse the existing v6 native frontier probe and
captured-message preparation seam. Only this audit directory receives new
scripts, recorded-input derivatives and results. No physics, remote execution,
training or robot actuation is involved.

## Ranked predictions

1. The current occupancy/support contract restricts the local route to a short
   prefix. Replaying the actual stopping input must reproduce target-selection
   rejection and identify the occupied/unknown/support branch before retiming.
2. Native replan exhaustion is not propagated to the P2B owner. Raw admissions
   should contain no failure at the native stop, while the backend remains
   active. Inspect the actual finishProcess and admission call sites.
3. Sensor geometry, reference height and robot dynamics differ from the old
   success. Compare executed sources/configuration and measured inputs; do not
   infer an isolated causal effect merely from a parameter difference.
4. The minimum cruise contract itself prevents continuation. This predicts a
   minimum-cruise rejection at the stopping decision. Check the gate order and
   published curves, not just optimizer candidates.

## Checks

- Verify the historical selected source against its upstream manifest and the
  run's executed-source manifest; verify current source against frozen v7.
- Recompute old/current travel, route, curve and stop evidence from raw records.
- Reuse native subscriptions and frozen original input bytes to reproduce the
  v7 final moving-curve continuation twice, inspecting support at both cylinder
  centers and sampling the original reference.
- Limit the local Docker diagnostic to 240 seconds, two CPUs and 4 GiB RAM,
  no external network, read-only source mounts and an audit-only output mount.
- Preserve failure evidence. No changed safety threshold, no speculative fix,
  and no claim of a full Newton reproduction from a frozen replay.
