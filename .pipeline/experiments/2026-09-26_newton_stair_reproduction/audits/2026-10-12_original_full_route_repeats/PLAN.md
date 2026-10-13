# Six fresh original full-route repeats

Stage: experiment + analysis. Authorized by Dr Sun on 2026-10-12.

Local source of truth: `/Users/sun/tongbu/study/phdproject/vla`.
Execution copy: `/data/sun/vla_mppi_20261009/repo` on gpu5070ti.
Frozen navigation/host package: v147; unchanged native candidate installation.
The previously delivered attempt01 is a pilot and is excluded from the new
six-trial denominator. No new navigation version is introduced for repeated
execution of identical code and configuration.

## Protocol declared before execution

Run candidate attempts02,03,04,05,06,07 sequentially. Each attempt starts a new
simulator, native process/container, policy/controller and map state. Use the
existing v147 launcher with `historical_full`, CPU Newton, factory PD/RL,
RTF1,600simulation-second capture limit and its existing bounded supervisor.
Do not adjust parameters, support/safety checks, route, startup or retry limits
between attempts. Ordinary navigation failure is counted and does not stop the
batch. Unclosed writers, missing outcome/copyback/retention or transport/execution
failure pauses execution for an evidence-preserving infrastructure inspection.
Do not replace a failed attempt with another successful attempt.

Original route input SHA-256:
`6afa0e573c268aca641f7d176f55bbf720b6521db8e5ce8153e2baece1b5b621`.
Ground start: `[-5.545314788818359,6.01318883895874,0.05804443359375]`.
Yaw: `-1.3258179441604312`rad.
Ground goal: `[1.954685200623011,-2.9868112220934897,4.5330305099487305]`.

## Sync and evidence gates

Verify all v147 source/snapshot pairs and runtime inputs before/after the batch
and before each run using the original frozen verifier. Verify the installed
candidate receipt and every receipt-listed byte before/after the batch. Hash
this audit plan and runner in the batch request before the first run. No frozen
source is edited. Record per-attempt server load/free space/GPU use; other GPU
work was present at preflight and is not stopped or altered.

For each attempt, require a closed retained capture; check the original full-route
validator, measured terminal arrival plus PD hold, no fall, verified copyback,
continuous time/position, exact original spawn and goal, and every recorded route
replacement's original measured-stop proof. Verify every archived member and
the complete remote artifact inventory. Count all six terminal outcomes.
Report route completion separately from planner latency, mapping time and
planning frequency. Do not infer sustained30Hz, Jetson compatibility, universal
reliability or independent random-seed coverage from these six same-scene runs.

## Storage and return boundary

Raw: `/data/sun/vla_mppi_20261009/trials/v147_full_candidate_attemptNN`.
Closed analysis: `/data/sun/vla_mppi_20261009/results/recording_v147/v147_full_candidate_attemptNN`.
Batch: `/data/sun/vla_mppi_20261009/results/full_route_repeats_20261012`.
Keep recordings, clouds, raw archives, verbose logs, environments and builds on
gpu5070ti. Return only an explicit allowlist: batch request/progress/identity and
resource checks; per-attempt metrics, latency CSV, outcome, full-route result,
remote artifact/member manifests and recovery-proof summaries; final aggregate
report, remote verification and SHA-256 return manifest. Expected local return
under5MiB; check aggregate size before transfer. No new videos are required by
this repeatability request; the full delivered v148 pilot video remains valid.

Acceptance: six new complete original-start to original-goal arrivals, no falls,
all original hold/copyback/retention/proof/integrity checks. A mixed batch is
reported as mixed and does not pass the repeatability gate.
