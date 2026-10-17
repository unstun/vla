# v236: LiDAR deadline scheduling on gpu40901

User authorization2026-10-17: diagnose and fix the v235 scanner timeout,
explicitly examine two-CPU affinity/contention, preserve RL/endpoints/.35m
hard guards/.1s capture period, preflight and then exactly one new full route.

Scope: new v236 scanner deadline/timing helper, v198 recorder adapter, bounded
host binding/probes/tests and recorded-state analysis/video. Keep all frozen
parents immutable. Navigation native source/install remain v232/v234. Do not
modify peer process priority/affinity, shared environments or training jobs.

Hypotheses: CPU runnable wait; main/scanner GIL contention; native-clock catch-up
checks before a full100ms wall budget; slow specific ray windows. Use original
Building/rays and captured state with zero physics to separate these first.
Any replacement must retain original capture stamps and data; genuine100ms
job overruns remain failures. Record submit/start/end/scheduler wait and native
next-due arrival time. Test delayed/overdue/exception paths before the fix.

Heavy evidence stays under /home/ubuntu/sun/vla_v234_20261017; return compact
regression/profile/route gates and review MP4s, not raw captures/build caches.

## Confirmed fix and resource binding
Real ray replay reproduces early rejection after~25us even though the ray
completes in37ms. Longer two-core batches also show genuine runnable wait:
39.7ms CPU +223.1ms wait =264.8ms total. The fix waits only until submit+100ms
and rejects a genuinely late result, including completed-late/queued work.
The own host runtime now uses a Docker4-CPU/6GiB quota with flexible affinity,
nice19/shares128. Host libraries are mounted read-only at original paths;
Python/wheels, ray payloads and policy golden frames remain identical/qualified.
User cgroups lack CPU delegation; the unsuccessful systemd probe is preserved.
The native container also keeps its4-CPU/6GiB cap with flexible affinity.
