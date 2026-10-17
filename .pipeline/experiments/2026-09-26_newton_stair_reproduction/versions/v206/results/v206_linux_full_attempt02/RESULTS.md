# v206 Linux physical recording: terminal stand timeout

One moving original-start historical_full Building episode ran on gpu5070ti with
frozen v206. It ended FAILED at 126.402160645 simulation seconds. The original
full-route gate did not pass. No navigation code, model or parameter was tuned.

The robot traversed 76.2339 m and finished 0.09457 m from the requested XY goal.
It did not fall. Actual ControllerServer loaded the hash-bound v206 plugin and
native SCAN library. The final command was exactly [0,0,0], but StanceHold was
still STAND_SETTLING with policy_owns_joints=true and reason
waiting_for_support_balance. ControllerServer reported terminal_settle_timeout;
the original no-retry branch for this typed failure was preserved.

This identifies the terminal failure, not its exclusive root cause. Component
success does not qualify v206 as a replacement for physically accepted v204.
Linux wall measurements must not be pooled with the earlier Mac comparison.

The preceding attempt01 ended before integration: initial_state records time0,
step0. Its factory shim lacked executable mode inherited from the prepared Mac
source; the no-physics graph probe also left descendants in its container.
Attempt02 uses byte-identical executable shim copies and recreates the probe
container before the episode. Frozen versions were not edited. Preserve both.

Raw capture is retained on gpu5070ti. The verified ZIP contains 1,158 original
members (340,689,259 bytes); remote_artifacts.json holds its SHA-256 and retrieval
command. Shared applied-state verification passed. Compact reports are returned
locally; full raw data stayed remote. See v207 for the actual failed-run video.
