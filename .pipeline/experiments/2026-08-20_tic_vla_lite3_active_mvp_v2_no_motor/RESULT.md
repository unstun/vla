# TIC-VLA Lite3 Active MVP v2 no-motor live result

Date: 2026-08-20

Stage: experiment + analysis

## Claim

The real D435i + Fast-LIVO2 -> Xavier bridge -> external Orin TIC-VLA ->
Xavier UDP relay -> RK3588 receive-only chain ran for a requested 120-second
Active service window. Active, bounded, non-zero body-command packets reached
and passed the native RK3588 protocol receiver. The receive-only program always
selected zero and never connected to or sent a motor command.

The strongest label is **integrated for the no-motor Active packet path**. This
run does not validate autonomous motion, obstacle avoidance, Retroid/WASD live
takeover, or the motor-capable `rl_deploy_vla` runtime.

## Source identity

- Local VLA commits: `58ee402127697b188515cde4f04ab7ed32ff99f9` and
  `4aa2890a2210a25435599016832ad4243e8964b6`.
- Local controller commits: `6a0ef1e92edbad394542c9dfdf73e154ae1664dc`,
  `00fe0fdfdc94fdbdb7043ec8326922d18e47c50c`,
  `e150064ee`, and `661a6b96b820bae3943651d8972a68234f698e8c`.
- The synced VLA v2 files on Orin matched the local SHA-256 values.
- The nine controller files synced to RK3588 matched the local SHA-256 values.
- Upstream TIC-VLA source commit:
  `9fa6f8b66b9e121d5df5df071297bba8e5353ebb`.
- InternVL3-1B revision:
  `4415a3b810e636d11dfa86b0e9ba40bb00535aa8`.
- TIC-VLA checkpoint SHA-256:
  `376263f89fad0f42c267d85655019232edc91d36e214e23424804dd4cd42e036`.

## Device-native verification

- Orin synced-copy tests: `27 passed in 0.46s`; Python compileall passed.
- RK3588 CMake configured natively and built:
  `tic_vla_controller_contract`, `tic_vla_receive_only`, and
  `rl_deploy_vla`.
- The native controller contract executable ran successfully.
- The motor-capable `rl_deploy_vla` binary was built but not launched.

Native binary SHA-256 values:

```text
0ac56be7358d088396f2961ff90eb1224b3f6c6990ee77a3de6be4ab88fc44bf  tic_vla_controller_contract
5764269e5a8cd7ae227918ca37bc9f32b7c1c2948834c45d05d3b1e2ceab1de7  tic_vla_receive_only
c42130d592b3a0f037c7a1a0342c9c9eecbf07b462882e24ffadb01937f703e7  rl_deploy_vla
```

## Real live run

The Active service recorded 411 strict packets over 119.734 seconds of summed
cycle time. Xavier forwarded all 411 packets from the allowlisted Orin source,
with zero relay rejections. RK3588 accepted all 411 packets with zero protocol
rejections.

Orin service results:

- 104/411 packets were valid and non-zero.
- 104 `ok`, 242 `stale_state_source`, 52 `history_gap`, 7 `stale`, and 6
  `generation_pose` records.
- First reasoning inference: 19.323 s.
- Resident fast-path samples: 111; p50 0.208 s, p95 0.675 s, maximum 0.924 s.
- Valid forward velocity range: 0.0164-0.2887 m/s.
- Every valid yaw command was `-0.2 rad/s`, the configured negative yaw limit.
- Frame-source age p95: 0.144 s.
- State-source age p95: 0.848 s, above the configured 0.25 s gate.
- Maximum packet size: 234 bytes, below the 1 KiB protocol limit.

RK3588 receive-only results:

- 11,532 complete 50 Hz records were parsed.
- 472 cycles observed a fresh, Active, non-zero eligible proposal.
- Selected non-zero cycles: 0.
- Motor command sent: false for every parsed record.
- One final partial JSON line was produced when the bounded receive-only helper
  was terminated after the Orin service had completed; raw evidence is retained
  unchanged.

## Current blockers before motion

1. Fast-LIVO2 is currently alive and reports no estimator fault, so the prior
   fault latch is recovered. However, its odometry updates are slow enough that
   242/411 service cycles exceeded the current 0.25 s state-age gate. Using this
   unchanged in the motor path would produce intermittent command expiry.
2. For the fixed instruction `Move forward safely and efficiently.`, every
   valid output saturated at `-0.2 rad/s` yaw. This proves that the model path is
   real, but it does not prove the proposed route is safe or even correctly
   aligned with the camera/robot coordinate convention. The retained frames
   show a low camera view with nearby wheels, cables, and no clearly open
   forward corridor, so this stationary scene is also unsuitable for judging
   whether the turn itself was a planning error.
3. Retroid and WASD takeover behavior passed the native software contract, but
   no physical Retroid/WASD input was exercised in this run.

The next motion-capable trial must first resolve or explicitly accept the state
freshness policy, visually verify camera/robot yaw sign and scene behavior, and
then obtain a separate real-actuation authorization.

## Evidence

- `orin/manifest.json`: pinned run identity and explicit Active mode.
- `orin/active.jsonl`: all 411 Orin service records.
- `orin/service.stdout.txt` and `orin/service.stderr.txt`: model runtime output.
- `orin/frames/`: retained real D435i frames from the end of the run.
- `xavier/bridge.stdout.txt`: live RGB and state callback counts.
- `xavier/relay.jsonl`: all 411 forwarded UDP packets.
- `rk3588/receiver.jsonl`: native receive-only 50 Hz records.

All task-owned bridge, relay, VLA service, and receive-only processes were
stopped after evidence capture. The existing perception stack was not stopped
or modified.
