# v170: renew recovery budget only after measured spatial progress

Stage: experiment and analysis. Native parentv167; Mac hostparentv169. Localv169
ran74.060m, all6replacement handoffs qualified, then the seventh distinct stop
aborted the mission. Stock Foxy RecoveryNode only clears its6retry counter at
childSUCCESS (the final goal), so successful traversal between stops never renews
it. Seven recorded failure poses are retained for a real stock/new BT regression.

Adapt the exact Navigation2 0.4.7 Apache-2.0 two-child control node, pinned commit
a947ab5656e46ae3aa1afdf95e1706a16e478974. Keep its child state transitions and
WaitForScanStop intact. At primary-child ticks only, a measured world/base_link
TF no older than100ms may renew the budget after entering a position at least2m
from every prior checkpoint. Duplicate, stale, future data cannot renew; revisits
cannot renew. Cap256checkpoints. Halt clears mission state; no callback changes
commands, goal success, collision, planner timing or physical stopproofs.

Test actual stock/new trees on the seven captured poses, stationary exhaustion,
revisiting space, stale/future TF, recovery failure and pending physical stop,
primary success and halt reset. Build onlyBT/bridge overlay; SCANv167unchanged.
Require local original-start fullroute before a new Linux cohort. v168 remains a
built but physically unqualified intermediate Linux candidate.
