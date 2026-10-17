# Captured LiDAR deadlines and shared-host CPU scheduling

## 1. Scope / trigger

v236 repairs v235's scanner failure on gpu40901 without changing the original
v198 raycaster, solver, policy, capture cadence, native planner or hard guards.
A native-clock catch-up can reach the next0.1s capture before100ms wall time
passes. Fixed hot CPUs can independently cause genuine runnable delays.

## 2. Signatures

`ScanDeadline.submit(executor, scan, *args, **kwargs) -> Future` returns the real
worker future with `scan_timing` metadata. `result(future)` waits only until
`submitted_wall_s + PERIOD_S`, where `PERIOD_S == 0.1`, and returns the original
payload. `save(path)` records submit/start/end/queue/CPU/runnable-wait evidence.

Run `versions/v236/cpu_launch.py {probe,preflight,route} --attempt NN` from the
private Python environment. Export its bin directory on PATH before invoking
the wrapper: Python shebang helpers must use the same private interpreter.
The route launcher retains the create-exclusive one-attempt ledger.

## 3. Contracts

Keep capture scheduling at every five original20ms control updates. Preserve
the original captured state, scan index, timestamp and point data. Do not drop,
duplicate or restamp scans. Waiting for remaining wall budget advances no
physics. Queue time counts toward100ms. A result completed after100ms is
rejected even if already done when inspected; worker exceptions propagate.

The own host runtime has a4-CPU/6GiB Docker quota, shares128/nice19, flexible
affinity and read-only host CPU libraries at their original paths. Native ROS
keeps its own4-CPU/6GiB quota with flexible affinity. No peer binding/priority
changes, driver installs or GPU exclusivity. Verify real `cpu.max`, not merely
a systemd property: this host's user service delegates only memory/pids.

## 4. Validation / error matrix

| Condition | Required result |
|---|---|
| Native next-capture arrives early; worker completes inside100ms | Wait remaining budget, publish original payload/stamp once |
| Actual queue + worker latency exceeds100ms | Original deadline failure |
| Late future already completed | Reject; no stale success |
| Raycaster raises ValueError/TimeoutError | Propagate the worker error |
| Fixed CPU runnable wait exceeds budget | Fix only own scheduling; keep deadline |
| CPU quota not actually delegated/enforced | Reject that execution binding |

## 5. Good / base / bad cases

The original guard rejects an actual37ms ray job after~25us when the pacer
catches up. A separate hot-two-core replay records39.7ms CPU +223.1ms runnable
wait. Flexible affinity under an actual4-CPU quota passes450 ray replays and
100 catch-up cases, zero overruns, max36.91ms. Original ray bytes match and
the original1000-frame policy golden gate passes. These are offline facts;
route/terminal acceptance remains a separate physical test.

## 6. Tests and assertions

`test_scan_deadline.py` exercises real ThreadPoolExecutor jobs and the original
NativeClockPacer: early native arrival, genuine timeout, completed-late result,
queue delay, worker exceptions and exact capture/payload identity. The old
behavior fails and the repair passes. Run original Building rays under the
actual CPU wrapper, verify point-byte parity,100ms budget, policy golden frames,
source/install identity and generated graph/profile before the physical trial.

## 7. Wrong / correct

Wrong: equate native-time advancement with elapsed wall deadline, expand the
sensor period, or call `Future.result(timeout=.1)` at every later check and
silently restart the budget. Correct: one absolute deadline from submission;
instrument actual completion and preserve immutable capture identity.

## 8. Physical prefix and independent evidence failure

The one v236 route records245 completed scans with0 deadline failures,
maximum46.718744ms. Its original writer queue exceeds256 at35.592068s;
result remains absent; the original driver writes a FAILED finish request. A passing scanner gate does not imply route,
staircase or terminal acceptance. Preserve the failed recording and label
rendered prefixes explicitly. Do not relax the evidence bound to mask lag.
The current recorder shares one thread for current execution-state writes and
bulk cloud/telemetry/snapshot persistence; measure these separately before
choosing a follow-up fix. Per-write service times were not captured here.
