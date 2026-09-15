# Phase A result: the V12 locomotion loop runs under our control on the rented 4090

Date: 2026-09-11. Stage: experiment + analysis. Label: **reproduced** for the command path; the sensor and
telemetry checks are not claimed at all (see the boundary at the end).

## Headline

A commanded body-frame velocity reaches the V12 policy **exactly**. Across all 451 recorded control steps of
`phase_a_flat_v4`, `command_observation_max_error` is **0.0** — not "within 1e-6", but bit-identical between the
commanded `(vx, vy, wz)` and the value sitting in the policy's own 450-dimensional observation at command-history
offset 60. That is AC1/AC2.

The robot then does what it was told:

| segment | commanded (vx, vy, wz) | measured body velocity |
| --- | --- | --- |
| forward | 0.30, 0, 0 | vx 0.268 |
| lateral | 0, 0.18, 0 | vy 0.151 |
| yaw | 0, 0, 0.40 | wz 0.379 |
| stop_zero | 0, 0, 0 | 0.007, −0.005, 0.021 |

Each axis responds on its own, with the under-tracking a velocity-tracking policy is expected to show. Supporting
facts from the same run: `nonfoot_contact_max_n` 0.0 (nothing but feet ever touched the ground), minimum root height
0.296 m, 99.3 % supported samples, no termination, all observations finite, zero command-sequence gaps, and exactly
one watchdog event — the disconnect the schedule deliberately triggers. 9.03 simulated seconds in 24.8 s of wall
clock. Adapter exit code 0.

## What was actually running

`runs/phase_a_flat_v4/runtime_import_identity.json` was written before anything physical happened, because an
editable install registers a meta-path finder that runs ahead of `sys.path` and can silently shadow a staged copy:

- `lite3_sim_bridge` from our staged tree, and `run_isaac_v12_fallback.py` hashing to
  `6104fe686bcd3bc0480c0afc1b41dde84d1a35d45a6dbbe9e51d98e6719ba3e3` — byte-identical to the module the accepted
  machine-dog-nav 74 m run loaded;
- `robot_lab` and `rsl_rl` from the pinned V12 tree, not from anything installed in the image;
- `isaaclab` 0.54.2 from inside the PyPI `isaaclab` 2.3.2.post1 wheel;
- checkpoint `a9d31dce…3d5450` re-verified on the host before launch, under the adapter's own fail-closed gate.

## The one real defect, and it is upstream

The run's self-declared status is **`INSTRUMENTATION_ERROR`**, not PASS: `runtime_error` is
`AdapterFailure("telemetry stream ended unexpectedly")` and the qualification telemetry sink consumed **0** frames.

Root cause, reproduced locally with stdlib only (`probe_sink_defect.py`, no Isaac, no GPU):
`FrameStreamClient.receive()` catches `OSError` and **closes the socket** before re-raising. `socket.timeout` is
`TimeoutError`, which is a subclass of `OSError`. The sink loop in `run_isaac_lite3.py:171-176` treats a timeout as
recoverable — `except TimeoutError: continue` — and loops back onto a socket that is already gone, so the next
`receive()` raises `ConnectionError("stream client is not connected")`, lands in the outer `except (EOFError,
OSError)` and is reported as a stream that "ended unexpectedly".

One read timeout therefore kills the sink permanently. With Isaac Sim taking seconds to reach its first telemetry
frame and the sink's timeout at 1.0 s, it dies during start-up every time. The counters agree exactly: publisher
`frames_sent` 1, `io_errors` 1, sink `sensor_frames` 0.

This is in `machine-dog-nav`'s code, on the qualification path. The accepted 74 m run used `--mode external` with a
real subscriber, which is why it never hit this. **Not fixed here**: AGENTS.md forbids editing `machine-dog-nav` from
a VLA task, and these bytes are hash-pinned to the accepted run. It is reported, not patched. Phase A's acceptance
criteria do not depend on the sink — the command evidence is computed in-process from the policy observation.

## Three failed attempts before this one, kept as evidence

Run ids are never reused or deleted.

| run | outcome | cause |
| --- | --- | --- |
| `phase_a_flat_v1` | Isaac Sim died during extension start-up, **exit code 0** | the image's user is `isaac-sim` (uid 1234) and the bind mount was owned by `ubuntu`, so `$HOME/.cache` was unwritable |
| `phase_a_flat_v2` | exit 126 | forcing `--user 1000:1000` made `/isaac-sim/python.sh` itself unexecutable |
| `phase_a_flat_v3` | driver aborted | `chown` to uid 1234 ran before the host shell wrote `gpu_before.csv` |
| `phase_a_flat_v4` | complete | keep the image's user, `chmod a+rwX` the two directories both sides write |

`v1` is the one worth remembering: **Isaac Sim can die during start-up and still exit 0.** The driver now gates on
the adapter's own `qualification_report.json` and rewrites a bare exit 0 into `rc=70 status=incomplete`, so a silent
failure can never again read as success.

## Claim boundary

Proven: the command path, the locomotion response, contact and support, and which source the interpreter loaded.
Not proven and not claimed: anything about sensors, depth, telemetry delivery, rendering, repeatability across runs,
or any behaviour with a camera or a VLA attached. `sensor_checks.nonempty` and every `depth_check` are false because
this run deliberately carried no sensor rig. Cameras stay off until Phase B, which is the render-cost go/no-go.
