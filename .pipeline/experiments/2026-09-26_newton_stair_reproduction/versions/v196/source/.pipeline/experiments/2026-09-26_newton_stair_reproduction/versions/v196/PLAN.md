# v196 implementation and component qualification

Stage: experiment + analysis. Version parent: v195; navigation source parent:
v194; native version: v196; Mac ARM64 binary underlay: v176.

The local v196 directory is the source of truth. The isolated execution tree is
`/private/tmp/vla_stop_audit_20261012/recovery_v196`. Before edits, the requested
14 trees were inventoried in `evidence/v196_protected_before.json`: versions
v189-v195; recovery_v176/v189/v191/v194; v192/v194 Mac full attempts; video_v195.
All recursive files, hashes, modes, mtimes, directory entries and symlinks are
checked without exclusions. Parent execution trees are mounted read-only.

## Behavior contract

- Restore Foxy PipelineSequence with ComputePathToPose at 1 Hz, FollowPath,
  six recovery retries and a one-second Wait.
- First PCT acquisition must return a valid connected route. A same-owner,
  same-goal refresh may retain a deep copy of its last valid route for terminal
  approach (XY <= 1.0 m, Z <= 0.35 m), no route, empty/height-count mismatch or
  disconnected canonical connector. Cache use records status and count.
  Invalid inputs, nonfinite route output, cancellation and owner changes reject.
- Identical pose geometry refreshes update the tracker without publishing another
  /pct_path while a trajectory is active. Changed geometry or spline waiting
  immediately publishes, preserving the original bounded wait watchdog.
- Reference replanning invokes the initializer once per round, retaining the
  bounded prefix and fully validated steering fallbacks. Missing/expired curves
  and three failures restart from measured odometry. A new admitted route wakes
  failed/expired REPLAN_TRAJ. Later at-rest stalls can reuse steering on a route.
- Freeze accounting rebases at local trajectory publication and generation
  changes. A freeze increment is bounded by now. Already future-stamped inputs
  remain invalid to the independent complete-curve checker.
- v196 profiles explicitly set reactive_cloud_max_age to 0.35 s, covering the
  reported 0.275-0.300 s mapper jitter. The generic 0.25 s default remains;
  original timestamps, future-input rejection, geometric collision/support,
  body freshness and complete-curve checks remain. This expands the permitted
  observation age by 0.10 s; physical performance is untested in this step.
- Non-hover emergency replanning uses finite horizontal speed < 0.15 m/s so
  vertical stair motion does not delay it. Hover-stop exit is unchanged.

## Verification and freeze

Run full native build/tests for all 11 rebuilt packages, generated-profile tests,
V176_TERMINAL_CAPTURE_PASS and V196_CORNER_LOOKAHEAD_PASS. Run Mac host tests,
live graph preflight including actual loaded libraries and cloud-age parameter,
protected-tree verification, qualify_mac, freeze_host freeze and verify.
Every execution source must match native_sources.json and the local package
snapshot. Return compact evidence under verification and bind it to quality and
manifest hashes. Preserve failed attempts if any. No run_mac_full invocation,
navigation goal, physics advance or full-navigation acceptance is authorized.

The named audit file contains only its completion message. The supplied fix
specification and inspected v194 code are the implementation inputs; the missing
long audit text is not treated as inspected evidence.
