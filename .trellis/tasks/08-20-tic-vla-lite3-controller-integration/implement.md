# Implementation plan: TIC-VLA to Lite3 minimal closed loop

## Execution status (2026-08-20)

- Active MVP v2 reopened implementation for explicit active mode,
  Retroid/WASD takeover, latched manual ownership, and local no-motor tests.
  P5 remains blocked/not complete; P6 remains unstarted and unauthorized.

- P0-P4: implemented and directly tested. Evidence is under
  `.pipeline/experiments/2026-08-20_tic_vla_lite3_controller/`.
- P5: blocked, not complete. The furthest real end-to-end shadow attempt was
  27.577 seconds / 31 shadow packets. Two subsequent clean Fast-LIVO2 starts
  latched `imu_timestamp_gap` after 4.9267 s and 4.8088 s jumps and stopped the
  declared state source. See the experiment `RESULT.md`.
- P6: not started and not authorized.

## Execution rule

This file is an implementation plan, not authorization to run the robot. Start
the Trellis task only after Dr Sun approves the planning artifacts. Real-robot
actuation requires a second explicit approval after shadow evidence is ready.

## Phase 0: Freeze identities and discover the two live inputs

- [ ] Record the local VLA commit/diff, pristine TIC-VLA commit, all five Orin
      compatibility patches, base-model revision, checkpoint hash, and exact
      `model_149999` manifest/hash.
- [ ] Inspect the current Orin execution copy without modifying protected
      vehicle files; create only the new owned execution directory.
- [ ] Discover and capture ten seconds from the actual Lite3 RGB stream. Record
      interface, resolution, frame rate, rotation, and monotonic capture method.
- [ ] Discover the best existing pose/state source and prove its fields/units
      with a stationary capture. If no measured pose exists, record the bounded
      command-dead-reckoning fallback and its claim limit.
- [ ] Inspect the dirty `machine-dog` working tree, select an exact controller
      base without overwriting unrelated changes, and create a separate
      controller task before any edit there.

**Gate P0:** exact model/controller identities, one usable live RGB source, and
one declared state source exist. Otherwise stop and report the missing input.

## Phase 1: Prove the official asynchronous fast path on Orin

- [ ] Create `deploy/tic_vla_lite3/` and adapt upstream
      `DynaNav/ticvla.py::predict_async` through explicit task-local overlays.
- [ ] Implement a resident model wrapper with asset hash checks, one-time load,
      zero-before-first-cache, instruction reset, and clean shutdown.
- [ ] Run a deterministic replay using retained frames: wait for the first VLM
      cache, then execute at least 100 action cycles while background reasoning
      refresh continues.
- [ ] Record per-cycle current-image, action-expert, total fast-path, reasoning,
      GPU memory, temperature, cache-generation, and failure data.
- [ ] Test reset during active background generation and repeated startup/
      shutdown to expose executor/cache races.

**Gate P1:** 100/100 exact finite `(1,30,2)` outputs, no cache race or growing
memory trend, and fast-path p95 `<= 250 ms`. If this fails, optimize/diagnose
before implementing any command bridge.

## Phase 2: Implement the local observation and trajectory pipeline

- [ ] Add the deterministic replay frame source and the single selected live
      RGB source.
- [ ] Add a four-frame 9/6/3/0-second context sampler and latest-frame path.
- [ ] Add the selected robot-state source, generation-start pose capture, and
      calculation of `[vx, vy, yaw_rate, dx, dy, delay]`.
- [ ] Implement the pure trajectory validator with exact shape, finite, age,
      sequence, discontinuity, and bounds checks.
- [ ] Port the upstream Spot pure-pursuit reference into a pure tested adapter;
      force `vy=0`, apply safe caps and slew limits, and return reason-coded zero
      on rejection.
- [ ] Add `safe_mvp.yaml` plus schema validation so missing or unknown safety
      fields prevent active mode.

**Gate P2:** unit/property tests pass for straight/left/right/zero and malformed,
NaN/Inf, discontinuous, stale, out-of-order, cap, and slew cases.

## Phase 3: Implement shadow service and protocol

- [ ] Implement the strict `body-command.v1` encoder/decoder with maximum packet
      size, source/session/sequence/range checks, and no cross-host safety clock.
- [ ] Implement the service state machine: startup, warming, shadow, armed,
      disarmed, fault, reset, and shutdown.
- [ ] Make shadow the default. Log proposed commands but mark packets shadow so
      a receiver cannot actuate from them.
- [ ] Add structured JSONL logs with run ID, source/model/config identities,
      frame/state/waypoint/command sequences, ages, latency, state transitions,
      and rejection reasons.
- [ ] Add packet replay and fault injection for duplicates, reorder, corruption,
      sequence rollback, session restart, source mismatch, loss, and process exit.

**Gate P3:** packet and lifecycle tests pass; shadow mode has no path to an
active controller command.

## Phase 4: Add the minimal controller-side arbiter in `machine-dog`

- [ ] In the separately approved `machine-dog` task, add a drop-in
      Retroid-plus-VLA `UserCommandInterface`; preserve the original interface
      and binary as rollback.
- [ ] Receive/validate VLA packets without blocking the 50 Hz policy loop.
- [ ] Convert accepted SI commands to the existing normalized command fields;
      recheck the conservative VLA caps in the receiver.
- [ ] Implement Retroid freshness, configurable deadman (`R1` default), manual
      deflection latch, explicit re-arm, and existing damping-button priority.
- [ ] Ensure VLA never sets `target_mode`; only Retroid/existing state-machine
      logic can stand, enter RL mode, or damp.
- [ ] Add C++ truth-table, timeout, packet-replay, and concurrency tests plus a
      build-only verification of the real hardware target.

**Gate P4:** all arbitration cases pass, policy loop stays at 50 Hz, duplicate
packets cannot extend freshness, and the original Retroid-only binary remains
launchable.

## Phase 5: End-to-end no-motion tests

- [ ] Connect Orin shadow output to the real controller receiver with motors
      disabled or command application disabled.
- [ ] Verify the complete packet path and compare Orin proposed SI commands with
      controller normalized values and final selected owner.
- [ ] Run at least ten minutes on the live RGB/state sources.
- [ ] Inject VLA process exit, Orin link loss, camera freeze, state freeze,
      malformed waypoint, wrong session, Retroid loss, deadman release, manual
      stick takeover, and damping-button input.
- [ ] Summarize p50/p95/p99 fast-path latency, packet interval, command age,
      drops, state transitions, and zero-command timing.

**Gate P5:** no stale/invalid/shadow command is selected; VLA loss zeros within
500 ms, Retroid stream loss zeros within its 200 ms watchdog plus one policy
cycle, and deadman/manual/damping behavior is witnessed through the final path.

Stop here and present logs plus the proposed real-robot test card to Dr Sun.

## Phase 6: Supervised robot test (fresh authorization required)

- [ ] Prepare a cleared, level open lane with no wall approach, one robot
      operator holding the Retroid, one observer, and the retained original
      controller binary ready for rollback.
- [ ] Verify original Retroid-only stand, zero command, short manual motion,
      damping, and signal shutdown first.
- [ ] Launch the VLA path in shadow, then switch to active only after the first
      valid cache and centered sticks are visible.
- [ ] Test zero command while standing, deadman release, manual takeover, VLA
      packet loss, and VLA process stop before free-running motion.
- [ ] Run ten trials, each at most 5 seconds or 0.5 m, using straight and gentle
      left/right instructions within `0.30 m/s` and `0.20 rad/s`.
- [ ] Stop immediately on unexpected mode, sign, oscillation, acceleration,
      command age, posture, camera, state, or trajectory behavior.
- [ ] Save synchronized command/waypoint/state logs and video for each trial.

**Gate P6:** all ten bounded trials complete without fall, collision, unexpected
mode transition, or limit breach, and takeover/stop works through the same
active runtime.

## Phase 7: Review, sync, and claim

- [ ] Sync final Orin source, configs, commands, logs, packet captures, metrics,
      and videos into a dated `.pipeline/experiments/` directory.
- [ ] Review local diffs in both repositories and identify every controller-side
      file and its exact base.
- [ ] Report the evidence label precisely: `integrated` for a working end-to-end
      path; `validated` only for the bounded open-lane acceptance test.
- [ ] Record failures and unresolved camera/state/scale/collision limitations.
- [ ] Propose a separate independent distance/collision-veto task before any
      wall, obstacle, crowded, or unattended test.

## Test commands to provide during implementation

The implementer must add stable project commands for:

1. local Python unit/property tests;
2. Orin replay async benchmark;
3. live shadow launch;
4. protocol fault replay;
5. controller C++ unit tests and target build;
6. controller receive-only/no-motor launch;
7. supervised active launch and immediate rollback.

Exact commands are not invented in planning; they must be recorded after the
actual camera/state interfaces and controller build system are verified.
