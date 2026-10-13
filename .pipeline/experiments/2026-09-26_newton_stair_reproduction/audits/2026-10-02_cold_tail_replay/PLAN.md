# Cold-tail diagnosis after v50

Stage: experiment + analysis. Continue the authorized tail-latency task.
No planner behavior, goal/yaw, PVA, safety, stop or timeout change.
Frozen v48/v49/v50/v51 remain intact; no new navigation version is claimed.

1. Audit repeated exact seeds and intervening input refreshes in the original v50 logs.
2. Reuse the v50 native replay harness on its own difficult recorded states: the
   worst pre-corner round, the overall worst round and the worst late round.
3. Repeat with the same source, goal precheck enabled and fixed inputs/clock;
   compare accepted geometry and failures to expose what this replay can reproduce.
4. If the live failure is not reproduced, capture the missing native state/input
   sequence before any cache or retry change; do not infer a fix from seed equality.

Ranked hypotheses: (1) repeated work under unchanged inputs; (2) fresh inputs
change the problem during a round; (3) old reference start becomes occupied at
corner recovery. Equal seed bytes alone do not prove equal map, support or time.

Owned files: this audit's analyzer, converter, native replay harness, build/remote
runner and compact reports. Native source is compiled/read unchanged from v50.
Run only a bounded offline replay on gpu5070ti; do not launch physics here.
Raw converted inputs, compiled probe and complete logs stay on gpu5070ti under
`/home/sun/vla_exec/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-02_cold_tail_replay/attempt01`.
Return compact results, source/input hashes and reproduction commands only.
