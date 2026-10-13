# Original full-route repeats: interrupted access checkpoint

Stage: experiment + analysis. Frozen navigation/host: v147 on gpu5070ti.

The full-route repeatability gate has **not passed**. Three new terminal outcomes
were received: all three navigation attempts failed without a fall. The six-trial
batch is incomplete/unconfirmed from the local observer. The delivered successful
attempt01 is excluded from the new six-trial denominator.

| New repeat | Run suffix | Terminal | Measured path | Native end | Fall | Max planning round |
|---|---|---|---:|---:|---|---:|
| 1 | attempt02 | FAILED | 35.422m | 88.123s | No | 377.403ms |
| 2 | attempt03 | FAILED | 40.206m | 83.486s | No | 311.178ms |
| 3 | attempt04 | FAILED | 49.389m | 102.855s | No | 374.452ms |
| 4 | attempt05 | Unconfirmed after disconnect | — | — | — | — |
| 5 | attempt06 | Unconfirmed | — | — | — | — |
| 6 | attempt07 | Unconfirmed | — | — | — | — |

All three completed launches reported execution_exit0, verified state copyback
and completed retention. The original full-route checker failed because the
navigation terminal was FAILED. A frozen v147 runner exit1 here is the navigation
failure result, not itself a transport failure. The subsequent SSH connection
ended with exit255 while attempt05 was the last observed active run.

The first failed capture was read directly before disconnection: final body
`[7.401442,6.482958,3.360214]`, a26.685s low-speed interval, original native
`Failed to make progress`, rejected fixed-height recovery attempts and final
Nav2 abort. The second failed capture ended at
`[6.585422,2.250702,3.353430]` with a10.894s longest low-speed interval; it did
not contain that exact native progress-error string. Do not merge their causes
or attribute the failures to GPU load without a captured-input replay.
Their measured RTFs were0.999862 and0.999543.

## Evidence boundary

`OBSERVED_PROGRESS.json` preserves actual streamed terminal metrics and reported
outcome hashes. Compact result files were not downloaded before access failed;
independent final file/member/native-after-batch verification and local SHA-256
return remain pending. Do not label the batch complete, report0/6, infer the
unknown attempts stopped, or promote these observations into validated raw
integrity. Heavy data remains at the declared remote roots, but its current
state is inaccessible and cannot be reverified now.

Local v147 source/snapshot/runtime verification passed3357source pairs and
618runtime inputs before execution. The batch checked frozen/native identities
before its first launch and each frozen runner checked the source again before
its trial. No navigation code/configuration was edited during the batch.
Other GPU work was present; server load/free space/GPU use was recorded remotely.

## Connection inspection

Dr Sun confirmed no manual restart or network change. Current provider entry
`23.252.106.36:60023` repeatedly closes before SSH key exchange; the historical
provider entry also closes. The existing ubuntu-obgx relay is reachable, but its
old127.0.0.1:2222forward is absent. Reaching the current provider entry through
that relay reports connection refused. The existing host-status API has no
posted GPU-host state and therefore cannot prove the target is powered off or
that its jobs have stopped. No reboot, service restart or other workload change
was attempted.

## Required continuation after access returns

1. Read the original batch request PID/cmdline and progress; inspect attempt05
   process/retention/outcome and owned containers/ports. Do not launch a second
   batch while the original is alive.
2. Reconcile every existing capture and preserve any interrupted execution.
   Do not overwrite attempt directories or replace failures with successes.
3. Continue only genuinely unstarted declared attempts, retaining all observed
   outcomes and any infrastructure interruption in the report.
4. Run the local `summarize.py` execution copy against the six closed records,
   then return its explicit under5MiBallowlist and manifest, verify every returned
   byte locally, and update the final result. If the original batch was
   interrupted, reconcile its progress explicitly before aggregation; never
   fake a completed batch state.

The next engineering priority is failed recovery on the complete route; the
single successful pilot and earlier short-route6/6results do not establish
original full-route reliability. MPPI steps2–5, broader reference,30Hz and
Jetson gates remain unchanged. Main Trellis task remainsin_progress.

## User steering after the access loss

Dr Sun reports that excess concurrent tasks can exhaust memory and freeze the
server, and will reboot5070Ti. This is an environment-change lead, not yet a
verified kernel OOM record. Preserve the first three navigation failures; inspect
previous-boot evidence and reconcile the fourth attempt after access returns.
Record post-reboot observations separately and check memory/process load before
launching another sequential trial. Do not attribute every earlier navigation
failure to memory pressure without evidence.
