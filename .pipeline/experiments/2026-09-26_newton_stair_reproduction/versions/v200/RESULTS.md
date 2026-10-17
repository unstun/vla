# v200 results

The first architecture-refactor stage is implemented and component-checked:

- ControllerServer is the only velocity publisher; cancellation and failure clear SCAN execution and publish zero through that same server.
- FollowPath remains active until the goal checker observes two continuous seconds of actual FIXED_STAND, PD ownership, quiet measured motion and a fresh zero command.
- Terminal waiting resets the movement progress checker. Leaving the terminal area restores ordinary progress checks.
- A separate 10-second steady-clock deadline aborts terminal waiting. The behavior tree propagates FollowPath failure directly and contains no generic RecoveryNode/Wait replay.

Four ROS packages built. **79 distinct component cases passed** (88 colcon report entries including wrappers), including actual typed ROS receipt, server publication, terminal/progress tests, the actual BehaviorTree.CPP pipeline failure test and 300 original-tracker parity samples. Raw logs and test XML are in `verification/`.

The v198 real TCP-to-Foxy-to-typed-ROS check separately passed ten scenarios and six host regressions. Frozen v198/v199 sources and 612 baseline files were reverified unchanged.

## Scope and next implementation

No simulator steps or full-route experiments were executed. This is a native component overlay; the frozen v196 physical result and v197 display remain the previous route evidence. A complete v200 physics launcher is not claimed.

Use v198 `runtime/bridge` and its `newton_episode.py` when composing the later full runtime; the old bridge lacks execution-state message 9. The component build includes the v198 interface package.

Pending stages: direct C++ PCT call and fixed-input height/route parity; LocalMotion in-process interface; terrain/startup cleanup; first-goal/target-change/deviation-triggered planning. The existing 1 Hz planning child remains until that final migration. No dynamic blocked-area mask is implemented.
