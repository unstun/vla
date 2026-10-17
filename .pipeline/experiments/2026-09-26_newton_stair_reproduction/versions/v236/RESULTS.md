# v236 scanner scheduling repair and one physical attempt

The LiDAR regression is repaired and verified. The single new original-route
attempt is **failed**, ending at35.59206771850586s on the unchanged evidence
writer backlog bound. It does not replace the accepted v232/v233 baseline.
The frozen manifest describes preparation-time status; this result records the
subsequent execution without rewriting that manifest.

## Diagnosis and change

Two independent mechanisms were reproduced using the original Building raycaster:

- NativeClockPacer catch-up reaches the next native0.1s capture after only~25us
  wall time. The original pending-future check aborts even though that scan
  actually completes in~37ms, inside its original100ms budget.
- Fixed hot two-core affinity also causes real overruns: one scan uses39.7ms
  thread CPU and waits223.1ms runnable, totaling264.8ms. Four fixed cores alone
  still show one132.8ms overrun in150 samples.

`ScanDeadline` waits only until the absolute submission+100ms deadline, including
queue time. It rejects late results even if already completed and preserves
worker exceptions. The adapter changes four scheduling sites in the frozen
v198 recorder; the original ray function, captured pose/state, index and stamp
are unchanged. Capture remains every five20ms native updates (0.1s).

Own physics runs in an enforced Docker4-CPU/6GiB quota, nice19/shares128, with
flexible affinity instead of fixed hot cores. Native ROS retains a separate
4-CPU/6GiB quota with flexible affinity. Shared packages, GPU settings, peer
priority/affinity and IsaacLab jobs were not modified. Read-only host-library
mounts retain the original private interpreter/wheels. A rejected systemd
probe lacked delegated CPU control; the accepted binding verifies real
`cpu.max=400000 100000`, rather than trusting a configured property.

## Gates before physics

| Gate | Result |
|---|---|
| Old guard regression | Fails:2 assertion failures /3 errors, retained |
| Fixed regression suite |7 tests pass locally and remotely |
| Original-ray sustained probe04 |450 samples,0 deadline failures; max36.910238ms |
| Native-clock catch-up probe04 |100 samples,0 failures; max35.584794ms |
| Original ray payload bytes | Exact match to original host probe |
| Original1000-frame policy golden test | Pass, max absolute error0.005950928 below0.01 limit |
| Frozen source/native install/profile | Pass |
| Actual12s graph preflight02 | Pass, zero physics |

Preflight01 failed before physics because a Python shebang helper resolved the
image interpreter. Exporting the original private environment bin on PATH
fixes the execution environment; all failed preparation evidence is retained.
The [runbook](RUNBOOK.md) records the accepted invocation.

## Single physical result

Run: `v236_linux_full_attempt01`. Exactly one physical launch ledger exists.
RL SHA7030ba4704ab1761e777ba2e268bb6070a1b245b9891bb6dc3c255414996581b,
original start/goal, ENV225, v232 native install,0.35m collision/support guards
and0.1s sensor period remain bound to the original inputs.

- 245 completed scans; **0 LiDAR deadline failures**; mean30.204114ms,
  maximum46.718744ms, maximum runnable wait15.992870ms.
- Goal sent and actual locomotion recorded;1367 saved states, last35.592068s.
- Exit1: `Evidence writer backlog exceeds its declared bound` (>256 jobs).
- Original result.json is absent; the driver wrote a FAILED finish_request
  (Geometric sensing became unhealthy). The terminal gate fails.
- 45–55s staircase success/margin/pause, arrival and final PD remain untested.
- Diagnostic prefix only:619/629 successful planner rounds,20.1777 successful
  wall Hz, P95 solve68.605ms, maximum576.295ms. These do not establish complete
  route timing or reliability and are not directly comparable to full routes.

The existing recorder sends current execution-state updates, telemetry, clouds
and snapshots through one writer thread. That coupling is source-confirmed;
this run did not measure per-write disk/CPU latency, so the dominant backlog
cause remains unproven. The256 bound was not relaxed and no second trial ran.
Next work should measure and separate critical state publication from bulk
evidence persistence, then verify the queue/termination contracts independently.

## Evidence and delivery

[Full failed-attempt audit and videos](../../audits/2026-10-17_v236_gpu40901_physical/RESULTS.md).
Heavy raw data remain at gpu40901:
`/home/ubuntu/sun/vla_v234_20261017/trials/v236_linux_full_attempt01`.
Verified non-pruning capture snapshot:67,694,719bytes,
SHA350aa0ab0889744418ae40d9dafe3c459caafd876240edf1e9ff144efd6e5869.
All original files remain retained. Rendering uses saved states only, zero
physics; the four-panel comparison explicitly ends v236 after35.592s.
