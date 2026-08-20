# TIC-VLA to Lite3 Active MVP v2

This package is the local source of truth for the task-owned TIC-VLA runtime.
It defaults to `shadow` and emits only the versioned high-level body-command
packet. Active output requires explicit `--mode active` selection. This package
has no joint-command or MotionSDK dependency.

The selected live inputs are the existing Xavier Fast-LIVO2 topics:

- RGB: `/camera/color/image_raw`, 640x480, approximately 13-14 Hz;
- pose/state: `/aft_mapped_to_init`, `nav_msgs/Odometry`;
- source host: `192.168.1.103` (Xavier), bridged read-only on demand.

At the 2026-08-20 preflight, Orin routed this destination through
`wlP7p1s0` with local source `192.168.2.70`; Xavier observed that connection
after the robot-network hop as `192.168.1.120`. The bridge allowlist is pinned
to the receiver-observed `192.168.1.120` for the run and must be rechecked after
a network restart.

The Xavier wall clock was observed to be stale during preflight. All safety
freshness decisions therefore use receiver-local monotonic timestamps.

Run local tests with:

```bash
PYTHONPATH=deploy/tic_vla_lite3/src python3 -m pytest -q deploy/tic_vla_lite3/tests
```

`shadow_service` requires `--config deploy/tic_vla_lite3/config/safe_mvp.yaml`.
Unknown or changed safety fields fail closed at startup.

Omitting `--mode` uses the config default (`shadow`). The controller owns one
priority order: damping/explicit stop, Retroid or WASD manual input, fresh
explicitly R1-authorized active VLA, then zero. `W/S` command forward/reverse,
`A/D` command yaw, and `X` returns keyboard input to neutral. Manual takeover
latches VLA off; release and press R1 again to re-arm.
