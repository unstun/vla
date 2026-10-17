# v198 — execution state over the existing telemetry connection

Parent: v197 (display); implementation parent: v196.

The C++ navigation controller currently cannot observe the physical PD/RL
ownership. This version adds typed execution feedback before moving terminal
completion into the controller. It preserves every previous version.

- Add protocol message 9 without modifying messages 1–8.
- Sample stance, ownership, measured body twist and effective command from one
  completed Newton control update. Use original simulation time and run identity.
- Carry the sample on the existing priority telemetry connection; publish it
  once on `/quad_0/execution_state` as `RobotExecutionState`.
- Build the interface in the restored, hash-verified v196 Foxy environment.
- Check wire compatibility, source sampling, duplicate/foreign/stale handling,
  and an actual socket-to-ROS loop with synthetic samples (no physics).

Owned paths: this version's bridge snapshot, Newton producer, interface package,
tests and receipts. Existing runtime source and frozen versions remain intact.
Controller completion, PCT migration and LocalMotion consolidation follow in
separate integer versions. No new full-route experiment is authorized here.
