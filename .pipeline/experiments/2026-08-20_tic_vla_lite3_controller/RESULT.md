# TIC-VLA to Lite3 controller integration result

Date: 2026-08-20

## Claim

P0-P4 are implemented and directly tested. P5 is **blocked and incomplete**:
the end-to-end shadow path reached the real Orin, D435i, Fast-LIVO2 bridge,
Xavier relay, and RK3588 receive-only controller, but the longest continuous
attempt lasted 27.577 seconds (31 shadow packets), not ten minutes. Two clean
Fast-LIVO2 restarts then latched `imu_timestamp_gap` after 4.9267 s and
4.8088 s timestamp advances, so the declared real state source ceased
publishing. No fallback dead reckoning was substituted.

The strongest evidence label is `implemented + partial live shadow`. It is not
`integrated` or `validated`.

## Post-run quality-review corrections

The local source was tightened after the blocked P5 attempts:

- reasoning-relative displacement and delay now follow the upstream bounded
  two-generation-start window instead of remaining anchored to service start;
- Orin receipt time is stamped after a complete bridge record arrives, not
  before the blocking read;
- the Spot-reference heading filter now uses the upstream first-sample and
  wrapped-angle update semantics;
- non-finite, boolean, negative, and unsafe configuration/time values fail
  closed, with regression tests.

These corrections pass the local test and Python 3.8 syntax gates recorded in
the final review. They were resynced to the Orin execution copy and its 16-test
suite passed, but they have not been rerun in live shadow because the declared
Fast-LIVO2 state source remains fault-latched. The older P5 logs prove only the
historical partial chain described below; they do not verify these post-run
corrections in a live chain. P5 therefore remains blocked.

## P0 identity and input gate

See `P0_IDENTITY_AND_INPUT_GATE.md`. The selected live inputs are D435i RGB
`/camera/color/image_raw` at 640x480 and Fast-LIVO2 odometry
`/aft_mapped_to_init`. The model and controller hashes are pinned there.

## P1 official asynchronous gate

- Official `DynaNav/ticvla.py::predict_async` through a task-local overlay.
- One first-cache wait: 19.266 s.
- 100/100 measured outputs: exact `(1,30,2)` and finite.
- Fast-path p50/p95/p99: 210.412/215.637/285.621 ms.
- One 917.166 ms outlier occurred; the declared p95 gate still passed.
- CUDA reserved range: 2,850,029,568 to 2,868,903,936 bytes; no continuing
  monotonic growth across the 100-cycle run.

Raw evidence: `orin_p1/p1_async_replay_1plus100.json` and matching stdout and
stderr files.

## P2 live observation and adapter gate

- Latest proven live sample: 20/20 strict records, RGB frame sequence 327-393,
  odometry sequence 65-77.
- Frame-source age p95: 117.227 ms; state-source age p95: 570.254 ms.
- The live bridge is request/response, so a slow reasoning generation cannot
  leave queued old frames to be mistaken for current frames.
- Unit tests cover straight, left, right, short/zero, malformed shape,
  NaN/Inf, discontinuity, stale, sequence, limits, and slew.

Raw evidence: `orin_p2/p2_live_bridge_latest.jsonl` and `xavier_p2/`.

## P3/P4 protocol and controller gate

- Strict 1 KiB JSON schema, exact fields/types/ranges, source/session checks,
  increasing sequence, receiver-local monotonic 500 ms watchdog.
- The original `rl_deploy` target remains unchanged as the rollback artifact;
  the new hardware target is separately named `rl_deploy_vla`.
- RK3588 native CMake build passed for `tic_vla_controller_contract`,
  `tic_vla_receive_only`, and `rl_deploy_vla`.
- After independent review, all three targets were rebuilt from the reviewed
  source on RK3588 and the contract test passed natively.
- The reviewed 250-cycle native replay accepted three increasing-sequence
  packets, rejected three duplicate/out-of-order/wrong-session packets, and
  immediately cleared the prior command when the increasing `valid:false`
  packet arrived. Shadow proposals were observable and nonzero, while selected
  velocity and eligibility remained zero/false for all cycles.
- `motor_command_sent` was false in every receive-only record.

Current reviewed-source evidence: `rk3588_p4/p4_post_review_native.jsonl` and
`rk3588_p4/native_binary_sha256_post_review.txt`. The earlier
`p4_native_faults_b.jsonl` and `native_binary_sha256.txt` are retained as
historical pre-review evidence only.

## P5 partial shadow and blocking failure

The furthest attempt produced 31/31 shadow packets through the real routed
chain and 4,766 recorded RK3588 50 Hz receiver cycles. All 31 proposed packets
were invalid/zero during history warmup or the first slow inference; controller
eligibility was false for every cycle and no motor command was sent. The
continuous shadow duration was 27.577 s.

That attempt first exposed and then safely handled two bounded service faults:

1. missing task-local Python dependencies caused a pre-model-load exit and no
   packet transmission;
2. the initial two-second bridge idle timeout closed during the official
   18.790 s first reasoning generation. The final source now uses a bounded
   30-second idle timeout.

The subsequent clean attempts could not enter the ten-minute gate because the
actual Fast-LIVO2 state source latched these faults:

- `p5d_10min_stack`: `IMU timestamp advanced by 4.9267 seconds`;
- `p5e_10min_stack`: `IMU timestamp advanced by 4.8088 seconds`.

In both cases Fast-LIVO2 stated that no further state or map updates would be
published until restart. All task processes were stopped. P5 metrics,
ten-minute fault injections, and live Retroid witness tests are therefore not
complete. No video was recorded because the shadow acceptance run never
reached its valid ten-minute start condition.

Raw evidence: `orin_p5/`, `xavier_p5/`, and `rk3588_p5/`.

## Reproduction commands

Local tests:

```bash
PYTHONPATH=deploy/tic_vla_lite3/src python3 -m pytest -q deploy/tic_vla_lite3/tests
python3 -m compileall -q deploy/tic_vla_lite3/src deploy/tic_vla_lite3/scripts
```

RK3588 focused build from the task-owned execution copy:

```bash
cd controller_source/lite3_rl_deploy_v0/build_tic_vla
make -j2 tic_vla_controller_contract tic_vla_receive_only rl_deploy_vla
./tic_vla_controller_contract
```

Orin shadow entry point (requires the recorded P1 dependency path and a fresh
session ID):

```bash
PYTHONPATH=deploy/tic_vla_lite3/src:/home/nvidia/sun/vla_exec/2026-08-20_tic_vla_orin_pretrained/python_deps \
python3 -m tic_vla_lite3.shadow_service --duration-s 600 --session-id NEW_SESSION \
  --config deploy/tic_vla_lite3/config/safe_mvp.yaml \
  --bridge-host 192.168.1.103 --controller-host 192.168.1.103 \
  --controller-port 45460 [model and output arguments from the run manifest]
```

Do not rerun the ten-minute gate until the D435i/Mid360/Fast-LIVO2 stack again
publishes continuous real odometry without an estimator fault latch.

## Safety boundary

P6 was not started. No VLA-commanded motion, joint target, stand transition,
RL-mode transition, training, checkpoint change, autostart, or system/global
dependency change occurred. The robot did not move because of this task.
