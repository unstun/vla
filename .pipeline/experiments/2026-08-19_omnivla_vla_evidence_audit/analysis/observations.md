# Observations and claim boundary

This document separates direct observations from interpretation. It does not
select a final VLA verdict.

## Directly observed execution facts

- The frozen receive-only matrix scheduled 24 attempts per candidate and
  retained 24 validated records per candidate (48 total, zero runtime
  failures).
- Every successful output passed the frozen finite `8 x 4` trajectory schema.
- All three-repeat condition groups had zero observed pairwise dispersion.
  This describes these runs only; it is not a general determinism claim.
- Every language and vision counterfactual had non-zero trajectory difference
  relative to its frozen base, exceeding the base condition's observed repeat
  maximum of zero. This demonstrates numerical sensitivity only.
- Actuation was disabled and no trajectory was sent to a controller.

## Language-panel observations

For OmniVLA-original, `move forward` ended at `(x=5.09375,
y=-0.8828125)` with path length `6.37358`, while `stop` ended at
`(x=5.5625, y=-0.37890625)` with path length `6.18071`. The `stop` output
therefore did not suppress the forward extent in this normalized output.
`turn left` ended at `y=-0.123535` and `turn right` at `y=-0.824219`:
they separated relative to one another, but both retained the same negative
lateral sign.

For OmniVLA-edge, `move forward` ended at `(x=9.84077, y=-0.424207)`
with path length `9.93355`, while `stop` ended at `(x=9.57366,
y=0.429130)` with path length `9.61970`. Again, `stop` did not suppress
the forward extent. `turn left` ended at `y=0.404155` and `turn right` at
`y=0.239735`: they separated relative to one another, but both retained the
same positive lateral sign.

Under the upstream plotting convention (`positive y = left`), neither
candidate showed a clean signed left-versus-right separation in this audit.
The relative endpoint ordering is an observation, not proof of semantic
instruction following.

## Vision-panel observations

The deterministic blur, mirror, and upstream-sample inputs all changed the
output beyond the zero observed repeat maximum. The mirror changed the final
lateral sign for both candidates: OmniVLA-original changed from `-0.8828125`
to `+0.78125`, and OmniVLA-edge from `-0.424207` to `+1.69810`.
This is evidence of input sensitivity, not evidence that the response is
geometrically correct, calibrated, or useful for Lite3 control.

## Runtime warnings and evidence correction

- OmniVLA-original completed with exit code zero while stderr retained
  TensorFlow duplicate-factory and TF-TRT warnings.
- OmniVLA-edge completed with exit code zero while stderr retained a PyTorch
  mask-conversion performance warning.
- Each wrapper's inline postflight process search matched its own shell and
  therefore reported `task_processes_absent=0`. That raw output is preserved.
  A later independent process check, after the wrappers had exited, recorded
  `task_model_or_wrapper_absent=1` on both hosts. The correction does not alter
  the model outputs.

## Jetson network correction after the frozen run

The frozen OmniVLA-edge matrix used files already present under the remote task
root and did not depend on a live Lite3 network path. Its preflight/postflight
therefore preserved the then-active Wi-Fi address `192.168.31.246`, which was
not the Lite3 Wi-Fi connection.

After Dr Sun connected the Jetson to the robot Wi-Fi, a separate read-only
snapshot at `2026-08-20T06:46:52Z` recorded SSID
`YSC-JYML-uc3yac-5G`, Jetson Wi-Fi address `192.168.2.70`, and a route to
`192.168.2.1` through the Wi-Fi interface. Three ICMP probes returned with
zero packet loss (`1.009/119.576/354.787 ms` min/mean/max), and TCP port 22
on `192.168.2.1` was open. The large three-sample jitter is an observation,
not a latency benchmark. The snapshot also reconfirmed that the audit model,
wrapper, and `tegrastats` monitor were absent. See
`raw/omnivla_edge/network_after_lite3_wifi.txt`.

No inference, camera request, controller request, or actuation was performed
during this network-only check. The corrected connectivity enables a separate
future Lite3-to-Jetson latency experiment; it does not strengthen the present
frozen-image semantic or VLA claims.

## Strongest justified labels

- `reproduced`: each pinned candidate executed the frozen 24-forward matrix on
  its declared host, with synchronized raw records and matching hashes.
- `integrated`: each candidate's receive-only callable output was captured by
  this experiment's immutable record and validation interface.
- `validated`: only the frozen audit contract, including identities, complete
  record retention, finite `8 x 4` outputs, hash-checked synchronization, and
  absence of actuation dependencies.

No stronger label is implied. In particular, VLA identity, semantic
correctness, navigation performance, physical units, robot-frame calibration,
closed-loop stability, safety, latency under load, long-run repeatability,
robustness beyond the four frozen images, and real-robot behavior remain
untested.
