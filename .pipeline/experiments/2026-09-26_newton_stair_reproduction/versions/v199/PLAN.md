# v199 — one velocity publisher

Parent: v198; native algorithm source: restored and hash-verified v196.

The plugin currently publishes Twist from `computeVelocityCommands`, emergency
callbacks and `stop`, while the server calls a no-op output hook. Replace this
split ownership with the standard compute-return-publish contract.

- ControllerServer owns `/quad_0/cmd_vel`, including every existing cancellation,
  failure and lifecycle stop path.
- SCAN returns velocity and clears trajectories on stop. It has no command
  publisher. Emergency spline handling produces zero on the next controller tick.
- Keep only an `ExecutionControl::stop` hook for clearing cancelled execution.
- Update both launch entrypoints and remove the obsolete plugin output parameter.
- Preserve tracking math and run its existing 300-sample parity regression.
- Add actual ControllerServer publication regressions with the real SCAN plugin.

This version does not yet move terminal PD confirmation into GoalChecker or
change PCT/BT replanning. Those remain explicitly pending in the HTML plan.
No physics, full-route experiments, policy changes, or robot actuation.
