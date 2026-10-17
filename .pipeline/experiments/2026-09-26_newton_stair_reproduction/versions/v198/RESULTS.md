# v198 results

The execution feedback interface and bridge are implemented and component-checked.

- `lite3_nav2_interfaces`: built in the restored ARM64 ROS 2 Foxy environment.
- Six host regressions passed, including a real TCP priority transport test and byte comparison against the unchanged v196 protocol.
- Real TCP to Foxy bridge to typed ROS subscriber passed ten assertions/scenarios (see `verification/ros_smoke.log`).
- 612 protected files unchanged. No physics steps, navigation goals, or full-route experiments.

This is an additive execution-state seam. GoalChecker does not consume it yet.
No whole-system navigation acceptance is claimed. The previous v196/v197 runtime remains available.

The new producer is `newton_episode.py`, which pins this version's bridge through `bridge_adapter.py`.
Launch the bridge with this version's `runtime/bridge` on PYTHONPATH and the new interface overlay sourced.
The producer wiring was syntax-checked and its sampling helper tested; the simulator entrypoint was not executed.
