# Fresh six-trial group after server reboot

Dr Sun reported possible task/memory overload and rebooted gpu5070ti. The original
batch is interrupted: attempts02–04 have FAILED terminal outcomes, attempt05
has a partial capture with no final outcome, and attempts06–07 were not started.
Keep the original batch/request/progress and all its files unchanged. A new group
is required to distinguish repeatability in the rebooted idle environment from
the earlier concurrent workload. Do not discard or pool the earlier failures.

Use unchanged frozen v147 for six new original full-route attempts08–13, in that
declared order, independently initialized/sequentially executed. No navigation
or physics/configuration changes. Every terminal outcome is counted; no ordinary
navigation-failure early stop. Each existing trial remains bounded by the
original v147 launcher. Pilot01 and pre-reboot group02–07 are excluded from this
new group's denominator and reported separately.

Same local/remote source and route-input gates as PLAN.md. Preserve the original
runner; the new audit wrapper only binds a separate output/order/protocol/boot
identity and resource observation. Verify frozen sources and installed bytes
before/after. Before each new launch require at least20GiBMemAvailable and no
GPU compute tasks, and original free-port/container/storage checks. Do not stop
other workloads. Record available memory/swap/load once per second throughout
the batch; this observes the environment and never alters an active planner.
If admission conditions change, pause before the next launch and retain results.

Start the bounded runner with detached stdout/stderr redirected to its own log;
connection loss must not itself break its stdout pipe. Original managed-run
timeouts, process ownership, retention and exit propagation remain unchanged.
Record kernel previous-boot OOM/Xid availability; absence of a matching entry
does not disprove overload. Current post-reboot inspection found28.4GiBavailable,
no GPU compute task/container, and no matching previous-boot OOM/Xid entry.

New remote batch root:
`/data/sun/vla_mppi_20261009/results/full_route_repeats_post_reboot_20261012`.
Raw and per-run closed analysis roots retain the same v147 scheme with08–13tags.
Return only compact summaries/latency/manifests/stop-proof/resource evidence
through an explicit checked allowlist. New group expected under5MiB; original
three closed failures/partial locator expected under2MiB; combined budget8MiB.
All raw capture/archive/build bytes remain on gpu5070ti.

Acceptance is six new complete original-route arrivals, no falls, original
measured PD hold/copyback/retention/proof/continuous-state/integrity gates. This
supports only fixed-scene post-reboot repeatability. Report original3failures,
1interrupted attempt and2unstarted attempts separately even if the new group
passes. Do not infer that memory caused all earlier navigation failures, or
promote30Hz/Jetson/general reliability/MPPI/reference status.
