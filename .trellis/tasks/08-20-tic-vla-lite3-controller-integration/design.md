# Technical design: TIC-VLA to Lite3 minimal closed loop

## 1. Design intent

This design keeps each existing component in its proper role:

- TIC-VLA decides a short local path.
- A small adapter converts the path to a conservative body command.
- A Retroid/VLA arbiter decides who currently owns the body command.
- `model_149999` converts that body command to joint actions.

No additional global planner, ROS graph, APK, or low-level VLA controller is
introduced in the first version.

## 2. Runtime topology

```text
Lite3 RGB -----------+                         external Orin 64GB
                     +--> frame buffer -----> TIC-VLA async runtime
robot pose/state ----+                         |  slow: VLM reasoning (~13 s observed)
                                               |  fast: current image + cached state
                                               v
                                         (30, 2) waypoints
                                               |
                                      validation + pure pursuit
                                               |
                                      bounded SI body command
                                               |
                                               +---- UDP ----+
                                                            |
Retroid UDP ------------------------------------------- command arbiter
                                                            |
                                                normalized [vx, vy, wz]
                                                            |
                                                V12 model_149999 @ 50 Hz
                                                            |
                                                         Lite3
```

The Orin process starts in `shadow`. Even in `active`, it cannot change the
robot motion state; the operator must place the existing state machine in RL
control. This preserves the current stand-up and damping path.

## 3. Upstream reuse boundary

The pristine source remains under
`references/upstream/2026-08-20_tic_vla/source/TIC-VLA/`.

The implementation should reuse these upstream behaviors:

- `DynaNav/ticvla.py::predict_async` for asynchronous VLM model-state refresh;
- four delayed images for the slow reasoning context;
- current-image feature extraction plus `ActionExpert` for fast decoding;
- `(30, 2)` body/FLU waypoint semantics;
- the Spot pure-pursuit calculation as the initial waypoint follower.

Jetson Python 3.8/CUDA compatibility changes remain explicit overlays. Isaac
Sim and DynaNav behavior classes are reference code only and are not runtime
dependencies on Lite3.

## 4. Proposed VLA package

The local source of truth will be `deploy/tic_vla_lite3/`:

```text
deploy/tic_vla_lite3/
  README.md
  config/safe_mvp.yaml
  src/tic_vla_lite3/
    model_runtime.py       # resident model and upstream async adapter
    frame_source.py        # replay plus one selected live RGB source
    state_source.py        # pose/state input and delayed-frame displacement
    trajectory_adapter.py  # validation, pure pursuit, cap, slew limit
    protocol.py            # strict packet encode/decode
    service.py             # lifecycle, shadow/active, logging
    cli.py
  scripts/
    run_replay_shadow.sh
    run_live_shadow.sh
  tests/
```

Only the replay source and the one live source found on the actual robot are
implemented. Abstracting several hypothetical camera systems is unnecessary.

## 5. Asynchronous inference lifecycle

1. Load and hash-check model assets once.
2. Fill the four-frame history buffer and start the first background reasoning
   generation.
3. Emit zero/invalid commands while no cached model state exists.
4. When the first cache arrives, run the fast path on each new current frame:
   current-image features, robot-state tokens, explicit delay, action expert,
   waypoint validation, and command conversion.
5. Start the next reasoning generation only when the previous one has finished;
   continue using the last valid cache meanwhile.
6. On instruction change or disarm, zero immediately, reset episode/cache
   state, refill context, and wait for a new cache.

The first-generation wait is expected and must be visible to the operator. A
13-second VLM latency is acceptable only because it is not in the recurrent
command path. The fast path must pass the 250 ms p95 gate on the actual Orin.

## 6. Observation handling

### Frames

`FrameSample` contains a local monotonic capture time, sequence, RGB bytes or
owned file path, dimensions, and validity. The frame buffer exposes the latest
frame and four history samples nearest 9, 6, 3, and 0 seconds. If the current
frame age exceeds the configured threshold, no command is valid.

### Robot state

`RobotStateSample` contains `vx_mps`, `vy_mps`, `wz_radps`, planar pose when
available, sequence, and validity. The service stores the pose at reasoning
generation start and computes current-frame `dx_m`, `dy_m`, and delay from it.

Preferred state source order:

1. an already running, timestamped Lite3/Fast-LIVO2 odometry source;
2. another verified body-state source already present on the controller host;
3. bounded command dead reckoning for the first open-lane integration only.

The selected source and any fallback must be recorded in the run manifest.

## 7. Trajectory validation and following

The adapter is deterministic and side-effect free. It:

1. checks exact shape `(30, 2)`, finiteness, sequence, and age;
2. rejects configured point/segment/path discontinuity bounds;
3. computes cumulative arc length and selects the first configured lookahead
   point, using the upstream Spot logic;
4. calculates heading error, filtered heading, curvature, forward speed, and
   yaw rate;
5. forces lateral speed to zero;
6. applies `vx <= 0.30 m/s`, `|wz| <= 0.20 rad/s`, then slew limits;
7. returns zero plus a reason code on every invalid path.

The first version uses waypoint direction and curvature but does not claim the
upstream metric scale has been calibrated for Lite3. All gains and bounds live
in `safe_mvp.yaml` and appear in every run manifest.

## 8. Command packet

The first protocol is small strict JSON over UDP because its 4-6 Hz expected
rate is low and packet captures remain human-readable. Maximum packet size is
1 KiB. The accepted schema is:

```json
{
  "schema": "tic-vla-lite3.body-command.v1",
  "session_id": "uuid",
  "plan_seq": 42,
  "source_frame_seq": 811,
  "reasoning_generation": 3,
  "mode": "shadow",
  "valid": true,
  "vx_mps": 0.08,
  "vy_mps": 0.0,
  "wz_radps": -0.12
}
```

The receiver validates the schema, field set/types/ranges, configured source
address, session, and strictly increasing sequence. It stamps accepted packets
with receiver-local monotonic time. Duplicate/replayed packets are logged but
do not refresh the 500 ms watchdog. `shadow` packets never own the command.

No cross-host timestamp is used for safety. Frame age and inference age are
still logged on the Orin for latency analysis.

## 9. Controller integration

The `machine-dog` task adds a drop-in user-command implementation beside the
existing Retroid interface, proposed as:

- `interface/user_command/retroid_vla_command_interface.hpp`;
- `interface/user_command/vla_command_packet.hpp`;
- focused arbitration/protocol tests;
- the smallest state-machine construction and build-file changes.

It reuses Retroid packet decoding and returns the existing `UserCommand`; no
policy observation or action contract changes. SI commands are divided by the
existing `[0.4, 0.2, 0.6]` controller caps to form normalized input, after the
smaller VLA caps have already been enforced and rechecked.

### Arbitration state

```text
DISARMED --fresh Retroid + centered sticks + R1 rising edge--> VLA_ARMED
VLA_ARMED --manual stick--> MANUAL_LATCHED
VLA_ARMED --R1 release / stale packet / invalid packet------> DISARMED
MANUAL_LATCHED --R1 released---------------------------------> DISARMED
any state --two stick buttons / lower fault------------------> DAMPING/STOP
```

In `DISARMED`, the adapter returns zero unless the operator is actively using
the manual sticks. In `MANUAL_LATCHED`, manual control continues and VLA cannot
resume from merely recentering the sticks.

## 10. Fault behavior

| Fault | Required result |
| --- | --- |
| Model still warming or first reasoning incomplete | Zero command |
| Camera/state stale or invalid | Zero and VLA disarm |
| Waypoint invalid | Zero; do not refresh sequence/watchdog |
| VLA packet missing for 500 ms | Zero and VLA disarm |
| Duplicate/out-of-order/wrong-session packet | Ignore; do not refresh watchdog |
| Retroid packet stale for 200 ms | VLA ineligible; zero |
| Deadman released | Zero immediately on received release |
| Manual stick deflected | Manual wins and VLA latches off |
| Two stick buttons | Existing joint-damping transition |
| Policy/observation/posture fault | Existing lower-controller damping/fault path |
| VLA service restart | New session; old packets rejected; manual re-arm required |

## 11. Rollout and rollback

- Default configuration is shadow, zero side velocity, conservative caps, and
  VLA disarmed.
- Controller integration is a separate source change and build artifact; retain
  the pre-VLA controller binary and its startup command.
- Rollback is stopping the VLA service and launching the retained controller
  binary with the original `RetroidGamepadInterface`.
- Do not add autostart in the first version. Every test starts and stops the
  VLA path explicitly under supervision.

## 12. Deliberate limitations

- The first test validates an end-to-end VLA command path only in a cleared open
  lane. Human takeover is not an independent obstacle detector.
- A later wall/obstacle test requires a separate distance-based veto upstream
  of the command arbiter. The veto may use existing LiDAR/perception, but that
  integration is intentionally outside this minimal first slice.
- Command dead reckoning is acceptable only for bounded integration testing;
  it is not equivalent to measured odometry.
