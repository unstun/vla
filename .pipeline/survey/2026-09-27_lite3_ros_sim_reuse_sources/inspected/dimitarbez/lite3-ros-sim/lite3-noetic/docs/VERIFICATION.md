# Verification record

Implementation checkpoint for Lite3_VMC upstream base `724aa54dee0cc374bd5417c86d649fb08d4d309a` and EmotionBot checkout `20c0c1361434bcf9ebaec4e8a5c9385e61c9c3e2`.

## Baseline

- Started the unmodified simulator with the original four attached targets.
- Pressed Enter once in the spawn terminal and observed all 13 controllers running.
- Received 12 joints on `/lite3_gazebo/joint_states`.
- Confirmed the keyboard publishes `sensor_msgs/Joy` on `/joy` and moves the Gazebo model.
- Source inspection confirmed the simulation executable subscribes Joy and does not instantiate its `/cmd_vel` receiver. Only the real executable starts the motion SDK receive path.

## Integrated implementation

- The read-only sibling EmotionBot checkout supplies the reusable `EmotionEngine`; no CLI/stdin automation or copied emotional core is used.
- A separate coordinator provides deterministic or OpenAI chat, immediate accepted events, incremental deltas, bounded context/requests, retries, deterministic fallback, cancellation, and turn ordering.
- The current official OpenAI SDK runs in an isolated Python 3.12 loopback sidecar because its dependency floor is incompatible with Noetic Python 3.8. The ROS image remains headless and compatible.
- State contract 1.1 includes turn correlation. Only accepted user and current completed assistant events update emotional state.
- The fixed-rate expression controller filters affect, blends and rate-limits motion, and resets every non-neutral category change through a 0.25-second exact-neutral return plus a 0.35-second canonical hold before starting the new entrance. A downstream bridge clamps again, arbitrates bounded manual input, applies watchdogs, and defaults disabled/zero.
- The integrated launch avoids the stdin spawner, loads all controllers through services, waits for readiness, and keeps the safety bridge required.

## Latest verified results

- Static shell and Python checks: passed in both runtime images.
- Clean Release `catkin_make`: passed; only pre-existing upstream Gazebo deprecation/CMake warnings.
- Unit suites: 58 Python tests and 5 controller-side C++ trajectory tests passed.
- Offline OpenAI process-boundary stream: 1 passed without key/network.
- ROS integration: 1 passed, 0 failures/errors, including generation-aware cancel-before-start and queued stance transitions.
- Both isolated headless Gazebo sweeps passed with 13 controllers and 12 joint states.
- Every chat emotion is centered. In the latest two-loop animation sweep, maximum per-profile contact-model drift remained below 0.025 m; the guard rejects more than 0.10 m.
- Anger emitted three full stomp occurrences and completed three recoveries across its entrance and two-loop hold, with the adopted 2.25-2.65-second recurring cadence. Joy and surprise also executed their controller-side hops in stance.
- Both Gazebo sweeps enforced a 0.30-rad anti-splay limit on all four HipX joints. A separate 15-second live anger sample after eight chat-driven switches peaked at 0.228 rad, versus the previous hard-limit drift near 0.523 rad. The correction is a simulation-only 40 Nm/rad abduction centering term; physical-robot control is unchanged. Mirrored stomp, recovery, height, tilt, finite-value, and containment checks passed.
- Every direct non-neutral profile change produced at least five consecutive exact-zero mapper samples before the new entrance. Disabled/final stop speeds were 0.0250/0.0021 m/s in the animation run. Watchdog status reached exact zero, manual priority/source were observed, and health permission stayed enabled throughout commanded phases.
- Teardown contained no configured controller/process failure markers.
- No `example_lite3_real`, `message_transformer`, motion-host UDP port, or hardware target address was used. The only inspected UDP use was benign loopback ROS/Gazebo traffic.
- WSLg GUI launch has been checked with both `gzserver` and `gzclient`, using the close orbit camera in `earth.world`. Repeated chat-driven joy/anger/fear/surprise/sadness/disgust switches were captured and inspected after the anti-splay change; the robot stayed upright, returned through the fresh stance, and kept its feet separated.
- The exact natural-language sequence `I am extremely happy and excited that this finally works!`, `I am frightened and uncertain about what will happen.`, and `This is making me very angry.` produced `joy`, `fear`, and `anger` through `run-emotion-chat`. The live controller logged the hop and stomp, a repeated anger turn started another stomp without freezing, and final status was healthy/non-stale at 0.0058 m from home.
- A real `gpt-5-mini` Responses stream passed through the disposable sidecar: 14 delta events, 47 response characters, 2.999 seconds. Output was metadata-only and the key was not persisted or printed.

The repeatable offline authority is:

```bash
make -C lite3-noetic verify-emotion
```

The intentionally separate live check is `make -C lite3-noetic emotion-openai-live-smoke` with `OPENAI_API_KEY` in the current shell. Gazebo measurements can vary slightly while remaining inside the harness thresholds.

## Split-host read-only hardware deployment — 2026-09-19

The fail-closed hardware working tree based on wrapper
`6de76b66b4209e1517a5b2e9e6284b1505700f8c`, Lite3_VMC
`fbe99b96395ca699bb2fbb121516b0830e08032b`, and EmotionBot
`7ae69828038c2f3563fc00d17fbfb2e3927abf57` was deployed read-only to the
connected Lite3. The changes were uncommitted at verification time.

- Existing SSH public-key authentication was installed on the motion and
  perception hosts; no credential was printed, committed, or stored in a script.
- `transfer.service`, `/joint_states`, `/imu/data`, and `/simple_cmd` were already
  live on the perception computer. No vendor workspace, service, `jy_exe`, or
  `network.toml` file was changed.
- The ROS-less motion-host observer ran with only `CAP_NET_RAW`; its authenticated
  relay reported fresh Retroid traffic, zero axes, and STOP false. The perception
  telemetry service separately held only `CAP_NET_RAW`; the ROS core was
  unprivileged.
- Live `0x0901` decoded state `1` (sitting), zero error flags, bounded attitude,
  and deployed percentage-form battery values. `0x0906` stayed incompatible and
  all high-rate direct-action gates stayed false.
- `make -C lite3-noetic run-emotion-hardware` opened the loopback tunnel and made
  the robot AI link fresh. `run-emotion-chat` produced a live `gpt-5-mini`
  Responses reply and the correlated `curiosity` state arrived on the perception
  computer.
- Throughout the run, `transmit_enabled=false`,
  `dynamic_actions_enabled=false`, supervisor state `DISARMED`, posture and
  dynamic arming false, robot state `1`, and no command was sent to UDP `43893`.
- Ctrl-C removed the OpenAI sidecar and SSH tunnel. Within the stale timeout the
  robot reported `link_fresh=false` while remaining `DISARMED`; all three passive
  services and vendor `transfer.service` remained active.

This verifies installation, passive telemetry, STOP observation, tunneled affect,
OpenAI chat, and fail-closed teardown only. It does not commission posture,
MotionSDK ownership, STOP preemption, hop, stomp, or any physical movement.

## Split-host height-only commissioning — 2026-09-19

With explicit operator authorization, the robot standing on a clear level floor,
and the Retroid STOP control ready, three posture-only joy trials were run through
the split-host mapper, supervisor, rate limiter, and vendor `/simple_cmd` path.
Dynamic actions, locomotion, roll, pitch, yaw, direct joints, and torque output
remained disabled.

The attempted height limits and rate limits were `+1000` at `500` units/s,
`+4000` at `1000` units/s, and `-20000` at `4000` units/s. The final value used
the sign observed from a passive Retroid right-stick-up capture (approximately
`-27606`) while capping it at the vendor's documented `20000` magnitude. The
operator reported **zero physical movement in all three trials**.

Trial 2 proved a nonzero `+4000` ROS `/simple_cmd` and exact return to zero.
Trial 3 retained healthy telemetry, joint/IMU feedback, centered Retroid axes,
state `6`, and no STOP or supervisor fault, but its filtered motion-host capture
did not prove delivery of the nonzero packet to `jy_exe`. This is a transport,
mode, ownership, or arbitration investigation result—not justification to raise
the amplitude.

After the final trial, `/simple_cmd` was zero, the supervisor was `DISARMED`, the
temporary `/dev/shm` commissioning configuration was removed, and the persistent
service was verified with `transmit_enabled=false` and
`dynamic_actions_enabled=false`. The exact approach, evidence boundary, and
required packet-comparison work are recorded in
[`HARDWARE_APP_CONTROL.md`](HARDWARE_APP_CONTROL.md#split-host-posture-commissioning-attempt--2026-09-19).
After the local chat and brain link were closed, a fresh read showed
`link_fresh=false`, supervisor `DISARMED`, and `robot_basic_state = 1` (sitting).
The test did not establish what caused that later state change.

## Instrumented height-command rerun — 2026-09-19

The operator then requested a standing-state joy rerun with movement enabled.
Fresh telemetry showed that the robot had already reached state `6` (standing),
so no redundant Stand/Sit toggle was sent. The temporary commissioning profile
enabled only the joy height channel, with a `+4000` limit and `1000` units/s rate;
dynamic actions, locomotion, roll, pitch, yaw, direct joints, and torque output
remained disabled.

The first instrumented rerun exposed a bridge defect rather than a missing
emotion command. Joy followed by neutral produced 58 height messages on ROS
`/simple_cmd`, but the passive perception-host wire observer saw only 16 height
datagrams and a maximum inter-packet gap of approximately 1.26 seconds. Source
inspection showed that the vendor `/ros2qnx` subscriber has queue depth 1 while
the bridge was publishing height plus three zero-valued, uncommissioned axes
back-to-back. Those unnecessary messages could evict the height command before
the vendor bridge transmitted it.

The posture bridge was changed to serialize one command per timer tick and to
emit only commissioned axes. `make -C lite3-noetic verify-hardware-offline` then
passed its static checks, clean Release build, launch enumeration, and all 14
protocol/safety tests before the corrected bridge was deployed. In the post-fix
rerun:

- Joy and the following neutral state both reached the hardware mapper.
- `/simple_cmd` reached height `+4000` and returned to exact zero.
- The wire observer saw 39 height datagrams and 10 heartbeats, with no
  uncommissioned roll, pitch, or yaw datagrams. The median nonzero-height interval
  was approximately 54 ms and the maximum was approximately 206 ms.
- It observed the final exact-zero height datagram (`0x21010102`, value `0`) from
  the perception host to the configured motion-host endpoint.
- The robot remained in state `6` with zero error flags. Maximum measured joint
  span was approximately `0.00099` rad and IMU changes were similarly negligible;
  no meaningful physical movement was measured or visually confirmed.

This proves the EmotionBot state, mapper, supervisor, `/simple_cmd`, vendor packet
format, and perception-host network emission through exact neutral recovery. It
does **not** prove that motion-host `jy_exe` accepted or applied the command. The
remaining investigation boundary is motion-host-side receive observation plus
the full app's Auto-mode/controller-ownership behavior. A larger posture
amplitude is not justified until that boundary is resolved.

The temporary configuration and deterministic brain were removed after the
trial. The persistent service was restored fail-closed with
`transmit_enabled=false`, `dynamic_actions_enabled=false`, and supervisor
`DISARMED`; both hardware services were active with `Restart=always`. Final live
telemetry showed the robot still standing in state `6`, battery `37%`, and zero
error flags. The stale brain link after tunnel teardown was expected. No password
or other credential was written into the repository or verification record.

## Auto-mode neutral-breathing trial — 2026-09-19

With Auto mode enabled by the operator, the hardware mapper was extended with a
disabled-by-default height-only analogue of Gazebo's neutral breathing loop. It
uses the same 0.25-second quintic entrance, 1.375-second idle period, and
`+0.65/-0.39` idle endpoint ratios. A new 0.25-second posture-intent watchdog
forces exact zero if the mapper disappears while the AI heartbeat remains live;
the mapper and posture bridge are now required launch nodes.

The physical trial used a temporary `400` height limit and `3000 units/s` rate,
with every other posture axis, locomotion, and dynamic action disabled. Preflight
showed state `6`, zero errors, fresh feedback, centered Retroid input, STOP false,
and no `/cmd_vel` publisher. Offline verification had passed a clean Release
build, launch enumeration, static checks, and all 15 protocol/safety tests.

During the 5.5-second neutral sequence, `/simple_cmd` and the perception wire
observer both ranged from `-156` to `+260`. Wire height cadence had approximately
51 ms median and 104 ms maximum intervals. All captured robot states remained
`6` with zero errors, while the maximum joint-position span was only
`0.00084 rad`; no meaningful physical breathing movement was measured. Auto mode
therefore did not make this small height sequence observable.

The nonzero motion-host capture was inconclusive, so `jy_exe` acceptance remains
unproven. A separate exact-neutral observation did prove value `0` on
`/simple_cmd`, on the perception wire observer, and arriving as a correctly
encoded 12-byte height datagram on motion-host `eth1`. The run ended `DISARMED`
with persistent transmission, dynamic actions, and neutral breathing disabled.
The robot remained standing in state `6` with zero errors. Battery fell from
`34%` to `26%` during the trial and read `23%` after teardown, so no further
nonzero trial was performed; the next test requires a charged replacement and
reliable nonzero motion-host ingress capture.

## Retroid-compatible direct neutral-height trial — 2026-09-19

A later charged-battery trial bypassed the unproven `/simple_cmd` acceptance
boundary and sent bounded high-level UDP from Windows
`192.168.2.28:43897` directly to `192.168.2.1:43893`. It reproduced the captured
full-app session sequence: four heartbeats at 2 Hz, Move, 2.0 seconds, Pose,
1.5 seconds, then 50 Hz pairs of yaw code `0x21010135` value `32768` followed by
height code `0x21010102`.

The 16.2-second waveform used a 4-second entrance, 10-second period,
`4000 units/s` rate limit, and height bounds `-3900..+10000`. The positive bound
is 50% of the documented `20000` magnitude; the negative bound preserves the
neutral profile's `-0.39` ratio. Evidence recorded:

- 810 height samples, with observed minimum `-3900` and maximum `+10000`;
- maximum 12-joint position span `0.2544403 rad`;
- maximum IMU orientation-component span `0.00856887`;
- basic state `6` and error flags `0` throughout;
- battery 62% at completion and 61% in a later fresh check; and
- five final yaw-`0`/height-`0` pairs at 20 ms spacing on unconditional teardown.

The separate Retroid reference was 387 packets over 19 seconds, with captured
height range `-29332..267` and yaw companion mainly `32768`. Those app values
were evidence for framing only; the custom test did not replay the app's
full-range height. The operator chose a 25% abort floor for this session despite
the Pro manual's 75% start recommendation. This does not revise the normal
battery guidance.

The whole-run span was later separated from the mode transition. A complete
post-handshake waveform window measured only `0.0011444 rad`, so the first
`+10000..-3900` periodic range was ineffective. A fixed post-handshake
`-10000` trial then measured `0.2484894 rad` maximum joint span and `0.0078653`
maximum IMU orientation-component span during the active height interval, with
state `6`, zero errors, and five acknowledged zero pairs on exit. This proves
bounded height actuation at the 50% negative limit.

The maintained launcher now starts an exclusive neutral-only host bridge by
default. It uses the captured handshake, a 250 ms Windows relay watchdog,
per-topic freshness, neutral emotion, a two-second stable dwell, and a 25%
operator-selected runtime floor. The final `0..-10000` periodic profile was not
physically re-verified because telemetry crossed below that floor; output paused
as designed. Persistent robot-side services remain fail-closed, and the packet
capture is not committed.

## Official MotionSDK continuous neutral breathing — 2026-09-19/20

An explicitly authorized restrained hardware run commissioned the official
aarch64 MotionSDK path from sitting state `1`. It used
`Sender::RobotStateInit()`, the vendor `PreStandUp` and `StandUp` trajectories,
the symmetric `0/-42/+78 degree` HipX/HipY/knee target, and a one-second stable
neutral hold. It did not acquire SDK control from a vendor-controlled standing
pose and did not bind the `qnx2ros` UDP port.

The final profile was a continuous five-second quintic cycle at the full
commissioned amplitude: HipX fixed, HipY `-0.0120 rad`, and knee `+0.0240 rad`,
with exact neutral and zero velocity at each loop seam. Nineteen full cycles
(95 seconds) completed. Maximum observed family spans were `0.0011444 rad`
HipX, `0.0124359 rad` HipY, and `0.0234222 rad` knee.

The reviewed passive `0x0906` stream produced a maximum `148.442 ms` feedback
age and `148.665 ms` consecutive update gap. Five gaps crossed 100 ms; each froze
trajectory time and held the last validated positions with zero velocity/torque,
then recovered after 20 fresh frames. No gap reached the 250 ms hard-release
threshold.

During cycle 20, the independent sequence-locked `0x0901` feed reported basic
state `8`, error flags `0`, at `0.501792 ms` age. The new state interlock stopped
the trajectory and executed the no-retry MotionSDK return-to-robot sequence. It
did not send STOP. Final telemetry showed state `1`, gait/motion `0/0`, battery
`41%`, and error flags `0`; the runner had exited and the SDK ownership marker
was absent.

Supporting verification passed 27 offline hardware tests, the aarch64 Release
build, and the standalone C++ state-safety test. Earlier logs also prove two
fail-closed stand aborts under the former 100 ms hard freshness rule, followed
by a 12-cycle run that exercised the gap pause/recovery behavior. The complete
implementation and attempt history are recorded in
`docs/HARDWARE_APP_CONTROL.md`.

### Animal-like Gazebo translation — 2026-09-20

The physical neutral was updated from a one-sided five-second compression to a
3.25-second, three-segment quintic inhale/exhale modeled on Gazebo's alternating
height/roll/pitch neutral. Hardware commands base HipY from `-0.008 rad`
extension through `+0.020 rad` compression, knee at twice that scalar, roll bias
at `+/-0.004 rad`, and pitch bias at `+/-0.003 rad`. HipX and yaw remain exactly
zero; Gazebo neutral also has no yaw. Combined per-leg compression is bounded to
`-0.015..+0.027 rad` (maximum knee offset `0.054 rad`).

The profile bounds/endpoints test passed both in the Noetic environment and on
the aarch64 robot host. The full offline gate passed a clean Release build, all
27 Python tests, packet verification, lease/release/crash-watchdog integration,
and launch enumeration.

One restrained live attempt began from state `1`, battery `37%`, errors `0`,
with no existing owner. Initialization, both vendor stand phases, and the stable
neutral hold completed. At the operator-accepted handoff checkpoint, 27 full
cycles (87.75 seconds) had completed with no tracking or robot-state fault.
Maximum measured spans were `0.0019074 rad` HipX, `0.0481415 rad` HipY, and
`0.0708771 rad` knee. Maximum feedback age/update gap was
`150.050/151.049 ms`; four pauses all recovered after 20 fresh frames, with a
maximum pause of `90.9427 ms`. The continuous runner and ownership marker were
still active at handoff, with the independent state-8 and dead-stream release
paths armed.

## Cartoon-expression Gazebo sweep

The current simulation-only sweep is run from the repository root with:

```bash
make -C lite3-noetic emotion-clean-build
make -C lite3-noetic emotion-static-checks
make -C lite3-noetic emotion-unit-tests
make -C lite3-noetic emotion-ros-tests
make -C lite3-noetic emotion-gazebo-test
make -C lite3-noetic emotion-animation-gazebo-test
```

`emotion-gazebo-test` starts the complete headless stack with `allow_locomotion:=false` so its centered-profile assertions remain deterministic. It enables motion only after the prepared stance, injects `event:<emotion>` for every profile, measures torso pose and all 12 joints through Gazebo for both the entrance and idle phases, then checks rapid changes, disabled actuation, command watchdog expiry, mapper loss, adapter loss, manual priority, stop, controllers, joint-state publication, and the no-hardware boundary. A normal GUI launch additionally enables the 0.09 m/0.035 m simulator-only auto-recenter with a 0.20 m hard boundary.

`emotion-animation-gazebo-test` holds every emotion through two idle cycles. It additionally checks that every profile remains within a 0.10 m planted envelope, joints keep a 0.05 rad URDF margin, all HipX joints remain inside 0.30 rad, front hips remain mirrored during stomps, recovery returns near the prior stance, every category change contains an exact-neutral hold, and no NaN/fall/controller error or stale residual motion occurs. The latest measured maximum idle joint excursion for neutral/joy/sadness/anger/fear/surprise/disgust/curiosity/affection was respectively 0.1081/0.2378/0.1644/0.4017/0.1884/0.2932/0.2525/0.1026/0.1104 rad.

| Emotion | Gazebo-observed designed result |
| --- | --- |
| neutral | Soft 1.375-second breathing and alternating tilt while state remains fresh; exact zero after staleness. |
| joy | One full centered hop, large high/low entrance rocks, then a 1.40-second four-pose bounce loop. |
| sadness | Deep lowered bow with a slow 1.875-second low sway. |
| anger | Forceful symmetric multi-impact stomp, tense low rocking, and a stomp on every 2.4375-second idle loop. |
| fear | Sharp recoil into a full crouch and a fast 0.45-second side-to-side tremble. |
| surprise | Full centered hop into a tall pitched-back alert stance and a 1.60-second attentive loop. |
| disgust | Strong one-sided down-and-away recoil alternating between full and partial avoidance. |
| curiosity | Broad alternating head/body tilts on a 1.20-second loop. |
| affection | Broad, slow warm sway on a 2.75-second loop. |

The planted sweep rejects a profile unless it produces measurable Gazebo torso or joint movement in both its entrance and idle phases, maintains a standing torso, keeps x/y/yaw at zero, stays within the posture command and no-drift envelopes, and settles to zero on disable/shutdown. The normal runtime keeps the dynamic model centered with bounded simulator-only recovery rather than the unstable Lite3 walk gait.
