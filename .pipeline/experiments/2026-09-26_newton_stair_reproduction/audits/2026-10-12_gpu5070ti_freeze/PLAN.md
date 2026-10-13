# gpu5070ti loss-of-response investigation

Stage: experiment + analysis. Dr Sun requests investigation of SSH becoming
unresponsive and recovering only after his manual reboot. His latest correction
does not establish a directly observed local display freeze. The manual power
key events are recovery actions, not the initiating cause.

Read-only historical probes and bounded resource observation are authorized by
this diagnosis. Do not reproduce a host crash through stress, reboot, service
changes, or killing other workloads. No navigation source or frozen version edits.

The evidence gap is the absence of a precise first-failure timestamp and a
high-frequency host resource trace before the power key. Collect existing
incident-boot journal events, a sysstat snapshot, and the last simulation's
monotonic records. Compare network errors with an earlier healthy-access window.
Clock conversion must use journal realtime/monotonic pairs from that same boot.
Distinguish sampling gaps, actual computation, SSH acceptance, and completed
navigation qualification. A partial result without copyback stays unqualified.

Local source of truth is this directory. Copy only the collector to its matching
path in `/data/sun/vla_mppi_20261009/repo`, verify its SHA-256 before execution,
and retain raw logs under `/data/sun/vla_mppi_20261009/results/freeze_20261012`.
Return only a manifest-bound compact allowlist below 2 MiB. Archive no credentials,
complete service configurations, or private keys. Root-only FRP settings are not
readable with the current noninteractive account; do not bypass that boundary.

Historical traces support or weaken explanations; they do not reproduce the
reported outage. No root-cause or fixed claim without a matching failure and
direct evidence. Keep the original interrupted batch and resource-paused
post-reboot cohort separate, including all failures and unstarted attempts.
