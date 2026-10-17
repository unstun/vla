# Lite3 app control path and hardware research

This note records the investigation and first bounded hardware test performed on
2026-09-19 with a physical DEEP Robotics Lite3 and the Android **DEEP Robotics
Lite3** app on a Retroid controller. It is an evidence record and implementation
input. The existing ROS/Gazebo launch targets remain simulation-only.

At the end of the test the robot reported `robot_basic_state = 1` (sitting). No
motion process or persistent robot configuration was changed. Temporary packet
captures were removed and no capture process was left running.

Do not store the robot password, API keys, or other credentials in this
repository.

## Network arrangement used

The development computer retained internet access through USB tethering while
using Wi-Fi exclusively for the robot:

```text
Internet
   |
   | USB tether, computer address 10.43.155.23
   v
Windows host / WSL
   |
   | robot Wi-Fi, computer address 192.168.2.28
   v
Lite3 access point and motion host, 192.168.2.1
   ^
   | robot Wi-Fi, observed Retroid address 192.168.2.196
   |
Retroid controller
```

Windows kept its default internet route through USB tethering. WSL could ping
`192.168.2.1` and reach SSH and the robot UDP network through the Wi-Fi route.
This allowed documentation and development traffic to use the internet without
routing robot commands away from the direct robot network.

The observed robot Wi-Fi SSID was `YSC-JYML-he2asx-5G`.

The observed robot interfaces were:

- `p2p0`: `192.168.2.1/24`, used by the direct Wi-Fi network;
- `eth1`: `192.168.1.120/24` and `192.168.137.120/24`, used by the internal
  motion/perception network.

## Confirmed app control path

```text
Retroid physical controls
        |
        v
DEEP Robotics Lite3 Android app
        |
        | Wi-Fi, little-endian UDP command packets
        v
Lite3 motion host at 192.168.2.1:43893
        |
        v
jy_exe / DEEP Robotics locomotion controller
```

The full Lite3 app is a high-level robot controller. It selects operating modes
and sends command codes and axis values to the motion host. It does not expose a
ROS `/joy` or `/cmd_vel` publisher to this workspace.

The manufacturer architecture includes a return path for robot status. Camera
video is documented separately at `rtsp://192.168.2.1:8554/test` when the
corresponding robot hardware and service are enabled. The video stream was not
tested during this session.

## Connected robot inventory

The following was observed through SSH, socket inspection, configuration reads,
and binary version strings:

- Hostname: `ysc`.
- Operating system: Ubuntu 20.04.5 LTS on `aarch64`.
- Kernel: `5.10.160`.
- SSH service: OpenSSH 8.2 for Ubuntu.
- ROS: `rosversion` was absent; the tested motion-host path does not use ROS.
- Motion executable: `/home/ysc/jy_exe/bin/jy_exe`, running as root.
- `jy_exe` was a link to the deployed `backup/deeprcs` binary.
- UDP listeners owned by the motion process included `43893` and `43899`.
- Robot profile: `professional_1`.
- Local robot metadata identified the product family as `JY-S5` and the profile
  as `standard`.
- Reported software strings: DeepROS `0.2.24(39)`, Profile `1.1.9(36)`, and
  Deeprcs `2.0.153(153)`.

The deployed `network.toml` contained:

```toml
ip = "192.168.1.103"
target_port = 43897
local_port = 43893
```

This matched the observed internal telemetry flow from
`192.168.1.120:<ephemeral>` to `192.168.1.103:43897`. No configuration file was
edited.

## Two different DEEP Robotics Android apps

DEEP Robotics publishes a separate generic Retroid forwarding app in the
official [`DeepRoboticsLab/gamepad`](https://github.com/DeepRoboticsLab/gamepad)
repository. Its documentation and APK describe a development tool that sends
raw Retroid button and joystick events to a configurable development computer.
Its example receiver uses UDP port `12121` and a packed gamepad structure.

That forwarding app is different from the blue **DEEP Robotics Lite3** app used
here. The full Lite3 app sends high-level motion-host commands to UDP `43893`.
Code written for the port-12121 gamepad format will not control the Lite3 motion
host directly.

## Captured behavior of the full Lite3 app

With the full app connected and its joysticks untouched, the Retroid sent from
`192.168.2.196:43897` to `192.168.2.1:43893`. Twelve consecutive sampled
packets were all the same 12-byte simple command:

| Field | Value |
| --- | --- |
| command code | `0x21040001` (heartbeat) |
| command value | `0` |
| command type | `0` (simple command) |

No joystick, pose, gait, action, Stand/Sit, or STOP command appeared in that
sample. This confirms that the installed full app maintains the documented
heartbeat while idle. It does not establish how competing non-heartbeat motion
commands are arbitrated.

## Motion-host command protocol

The primary local reference is
[`Jueying Lite3 Motion Host Communication Interface(beta) V1.0.7-0`](../../lite3-robot-docs/Lite%203%20secondary%20development/Jueying%20Lite3%20Motion%20Host%20Communication%20Interface(beta)%20V1.0.7-0.md).
The matching vendor PDF remains authoritative for tables and diagrams.

Commands use UDP with little-endian fields. The robot target is
`192.168.2.1:43893`. A simple command is exactly 12 bytes:

```c
struct CommandHead {
    uint32_t code;
    uint32_t parameter_or_size;
    uint32_t type;
};
```

For a simple command, `type` is zero and the second word carries the command
value. When a command has no meaningful value, the second word is zero. A
complex command sets `type` to one and appends a body whose byte length is in
the second word. No checksum or envelope was required for the two validated
simple commands.

The exact packet encodings used successfully were:

| Command | Little-endian words | Bytes |
| --- | --- | --- |
| Heartbeat | `0x21040001, 0, 0` | `01 00 04 21 00 00 00 00 00 00 00 00` |
| Stand/Sit toggle | `0x21010202, 0, 0` | `02 02 01 21 00 00 00 00 00 00 00 00` |

Relevant documented behavior and commands:

- Heartbeat `0x21040001` must be sent at least at 2 Hz.
- Stand/Sit `0x21010202` toggles between the two states. It is not a separate
  state-setting command.
- Software STOP `0x21020C0E` makes the robot go down immediately and is intended
  for an emergency. It was not transmitted during this test.
- Reset/zero uses `0x21010C05`.
- Pose mode uses `0x21010D05`.
- Move mode uses `0x21010D06`.
- Manual mode uses `0x21010C02`.
- Navigation mode uses `0x21010C03`.
- Pose axes return toward the normal standing pose if no axis command arrives
  for more than one second.
- Move axis commands must be published at 20 Hz or faster. The robot stops the
  commanded movement if updates cease for more than 250 ms.

The same axis command codes are interpreted according to the selected mode:

| Code | Pose mode | Move mode |
| --- | --- | --- |
| `0x21010131` | body roll | left/right velocity |
| `0x21010130` | body pitch | forward/back velocity |
| `0x21010135` | body yaw | turn rate |
| `0x21010102` | body height | not used as a movement axis |

The documented pose-value bounds are:

- Roll: `[-12553, 12553]`; positive rolls right.
- Pitch: `[-6553, 6553]`; positive lowers the head.
- Height: `[-20000, 20000]`; positive raises the body.
- Yaw: `[-9553, 9553]`; positive rotates the body right.

These are protocol limits, not suitable emotion-expression defaults. A hardware
expression bridge must use materially smaller configured limits and rate limits.

## App control mapping

The controls described in the
[`Lite3 Pro User Manual V1.0.7-0`](../../lite3-robot-docs/Lite%203%20user%20manual/Jueying%20Lite3%20Pro%20User%20Manual%20V1.0.7-0.md)
match the full Lite3 app:

- In Move mode, the left joystick controls planar translation and the right
  joystick controls rotation.
- In Pose mode, the left joystick controls pitch and roll and the right
  joystick controls height and yaw.
- UI controls select Stand/Sit, Move/Pose, Flat/RUG, gait speed, voice features,
  and built-in actions.
- The app STOP control makes the robot go down immediately and is intended for
  loss of control or another emergency.

## Observed telemetry

The motion host continuously transmitted complex status messages from the
internal `eth1` interface to `192.168.1.103:43897`. Every observed message began
with the same 12-byte little-endian header used by commands.

A 200-packet sample contained:

| Count | Code | Body bytes | UDP payload bytes | Interpretation |
| ---: | --- | ---: | ---: | --- |
| 18 | `0x0901` | 200 | 212 | documented `RobotStateUpload` |
| 18 | `0x0902` | 96 | 108 | documented 12 joint angles |
| 18 | `0x0903` | 96 | 108 | documented 12 joint velocities |
| 18 | `0x0904` | 4 | 16 | present, not decoded in this investigation |
| 18 | `0x0905` | 48 | 60 | present, not decoded in this investigation |
| 92 | `0x0906` | 368 | 380 | present, used by bundled SDK code, not decoded here |
| 18 | `0x010901` | 40 | 52 | present, not decoded in this investigation |

The first four bytes of the `0x0901` body are the little-endian signed integer
`robot_basic_state`. The states relevant to the validated test are:

| Value | Meaning |
| ---: | --- |
| `1` | sitting |
| `4` | prepare |
| `5` | sit-to-stand transition |
| `6` | torque-control state, standing |
| `7` | stand-to-sit transition |
| `8` | lose-control protection |
| `9` | posture adjustment |
| `17` | reset-to-zero |

The vendor manual documents `0x0901` at 50 Hz. The internal telemetry target is
fixed by robot configuration rather than automatically replying to each command
sender. During this test, state was verified by passive capture on the robot's
`eth1` interface. A development-host bridge will need an intentional telemetry
route or a read-only status relay instead of changing that target ad hoc.

## Validated Stand/Sit test

The test was explicitly authorized with the robot on a clear floor and a human
holding the Retroid controller with its STOP control available.

Before transmission:

- live `0x0901` telemetry reported state `1` (sitting);
- the Retroid app was connected;
- twelve consecutive Retroid packets were heartbeat-only;
- the target and listener were confirmed as `192.168.2.1:43893`;
- the host had no ROS installation, so no ROS node or topic was involved.

### Stand transition

The development computer used one UDP socket and:

1. sent four heartbeat packets at 4 Hz;
2. sent one Stand/Sit toggle;
3. sent 28 further heartbeat packets at 4 Hz over seven seconds;
4. stopped transmitting and read the robot's status stream.

Observed state progression:

```text
1 sitting -> 4 prepare -> 5 sit-to-stand -> 6 standing
```

The final state `6` was confirmed with a separate fresh telemetry sample after
the transition capture ended.

### Sit transition

Starting from confirmed state `6`, the development computer:

1. sent four heartbeat packets at 4 Hz;
2. sent one Stand/Sit toggle;
3. sent 36 further heartbeat packets at 4 Hz over nine seconds;
4. stopped transmitting and read a fresh robot-state packet.

The final telemetry value was `robot_basic_state = 1`, confirming that the robot
returned to the sitting state. The transition-state capture did not run because
its background `sudo` command paused for authentication, so states `7 -> 1` were
not recorded as a sequence. No second toggle was sent. A direct final-state
sample was used to avoid acting on an assumption.

No STOP, gait, joystick, pose-axis, action, joint, or torque command was sent in
either direction. The Retroid continued to provide its heartbeat. The specific
combination of Retroid heartbeat traffic and one custom Stand/Sit toggle was
therefore validated; concurrent motion commands from two controllers remain
untested.

## Required state-aware Stand/Sit procedure

Because `0x21010202` is a toggle, it must never be treated as an unconditional
"stand" or "sit" command. A repeatable implementation must:

1. Receive and parse a fresh `0x0901` packet.
2. Require state `1` before requesting stand, or state `6` before requesting sit.
3. Refuse the toggle in a transition, action, protection, unknown, or stale
   state.
4. Confirm the Retroid is heartbeat-only and keep a human ready at STOP.
5. Establish a heartbeat at no less than 2 Hz; 4 Hz was validated here.
6. Send exactly one 12-byte Stand/Sit packet.
7. Continue the heartbeat through the transition.
8. Observe the expected transition and require final state `6` for stand or `1`
   for sit.
9. Do not retry blindly after a timeout. Read a fresh state and let the operator
   inspect the robot first.
10. Stop custom transmission and leave the robot in a confirmed stable state.

The software STOP command is an emergency action that makes the robot go down
immediately. It should not be used as ordinary timeout recovery.

## Implication for emotion-bot hardware support

The first hardware implementation should preserve the existing separation
between emotional reasoning and actuation:

```text
emotion-bot state
        |
        v
bounded expression mapper
        |
        v
explicitly enabled Lite3 UDP bridge with watchdog
        |
        v
pose mode plus bounded height/roll/pitch/yaw commands
        |
        v
192.168.2.1:43893
```

Initial hardware work should use small posture changes while standing. Walking,
hops, stomps, direct joint/torque control, and built-in dynamic actions require
separate tests and safety decisions.

A hardware bridge needs all of the following before it can transmit expressive
motion:

- explicit physical-robot enablement separate from simulation motion enablement;
- confirmed robot identity, deployed software, network target, and current state;
- a clear operating area and a human holding the Retroid controller;
- a tested STOP path and documented manual takeover procedure;
- bounded pose values, rate limits, and exact neutral output on stale state;
- heartbeat ownership and deterministic shutdown behavior;
- a watchdog that stops pose output and returns to neutral on failure;
- state feedback that rejects stale or incompatible operating states;
- protection against conflicting motion commands from the app and custom bridge.

## Remaining unknowns and next checks

- Capture each app UI action separately and map its exact command sequence.
- Determine whether the full app changes heartbeat cadence during motion.
- Record the installed full Lite3 app version from its General screen.
- Identify and decode observed telemetry codes `0x0904`, `0x0905`, `0x0906`, and
  `0x010901` from the exact deployed software version.
- Establish a supported telemetry path to the development computer without
  disrupting the existing perception-host destination.
- Test the RTSP stream and its ownership behavior.
- Measure safe posture amplitudes and rates before connecting emotion output.
- Verify neutral recovery and watchdog behavior on packet loss.
- Determine command arbitration when the app and bridge are both present. Do not
  test conflicting movement commands casually.

## Split-host implementation status

The wrapper now contains a separate fail-closed package under `hardware-ws/` and
a brain-only launch in `emotion_bot_ros`. The initial implementation change was
offline-tested safety logic, not a completed physical commissioning record.
`0x0901`, transport framing, passive STOP recognition, shared-memory sequencing,
supervisor exclusivity, exact neutral, cooldowns, and action phase transitions
have offline tests.

Later on 2026-09-19, the fail-closed package was deployed read-only. Separate
systemd services constrained raw-socket capability to the motion-host STOP
observer and perception telemetry tap. Live `0x0901`, the authenticated Retroid
relay, the SSH-tunneled affect stream, and one OpenAI chat turn were verified.
The deployed `0x0901` battery field used percentage units. Final robot state was
`1`, supervisor state was `DISARMED`, and the link became stale after teardown.
No posture transmission, STOP-preemption test, MotionSDK takeover, hop, stomp,
or other physical movement was performed.

The public MotionSDK documents a one-second command timeout but does not identify
its `0x0906` layout as compatible with the deployed Deeprcs `2.0.153`. The package
therefore requires explicit reviewed offsets and value validation and keeps all
direct-joint gates false by default.

## Split-host posture commissioning attempt — 2026-09-19

A subsequent explicitly authorized session attempted the first height-only
emotion expression while the robot was standing on a clear, level floor. A
human held the Retroid with its STOP control open and ready. The result of all
three trials was **zero visible physical movement**, as reported by the operator.

### Approach under test

This commissioning path deliberately stayed above joint and torque control:

```text
development computer: offline EmotionBot brain and chat (`event:joy`)
        |
        | loopback-only SSH tunnel, versioned emotion state
        v
perception computer: mapper -> safety supervisor -> posture rate limiter
        |
        | vendor ROS `SimpleCMD` messages on `/simple_cmd`
        v
vendor `transfer` process -> motion host `jy_exe` at UDP 43893
```

Only the documented high-level body-height command `0x21010102` was allowed.
Roll, pitch, yaw, walking, built-in actions, direct joints, and torque commands
remained disabled. Dynamic actions stayed disabled throughout.

The installed configuration was not edited to permit motion. Each trial used a
temporary configuration under `/dev/shm` with a single nonzero joy height,
explicit height limit, and rate limit. Arming required all of the following:

- fresh `0x0901` telemetry with `robot_basic_state = 6` and no error flags;
- validated, fresh vendor ROS `/joint_states` and `/imu/data` feedback;
- a fresh AI link;
- fresh passive Retroid observation, centered axes, and STOP false;
- a neutral posture intention before entering `POSTURE_ARMED`.

After each trial, joy was changed to neutral, the output returned to exact zero,
the posture channel was disarmed, the temporary configuration was removed, and
the persistent service was restored with `transmit_enabled=false` and
`dynamic_actions_enabled=false`.

### Retroid reference and trial results

A separate passive capture of the Retroid in Pose mode registered right-stick-up
as a negative height value, reaching approximately `-27606`. The vendor protocol
limit is `[-20000, 20000]`, so the Retroid-derived trial preserved the observed
negative direction but capped its magnitude at `-20000`. This observed sign was
not interpreted as proof of which physical direction the body should move.

| Trial | Joy height limit | Rate limit | Evidence and physical result |
| ---: | ---: | ---: | --- |
| 1 | `+1000` | `500` units/s | Bounded height-only request; operator reported zero movement. |
| 2 | `+4000` | `1000` units/s | `/simple_cmd` reached `+4000` and later returned to `0`; operator reported zero movement. |
| 3 | `-20000` | `4000` units/s | Retroid-derived sign and protocol-capped magnitude; five-second ramp, approximately five seconds at the target, then a five-second return to `0`; operator reported zero movement. |

During trial 3, state remained `6`, Retroid axes remained centered, feedback
stayed healthy, and no supervisor fault or STOP was reported. The final observed
`/simple_cmd` value was exactly zero. The final supervisor state was `DISARMED`,
the temporary configuration was absent, and both persistent transmit flags were
false. After the development-side chat and brain link were closed, a separate
fresh telemetry read reported `robot_basic_state = 1` (sitting), `link_fresh=false`,
and the supervisor still `DISARMED`. The cause of the later stand-to-sit change
was not established by this test, so it is recorded as an observation rather
than attributed to the emotion bridge.

The ROS-side nonzero command is proven for trial 2, but the attempted filtered
motion-host capture did not prove that trial 3's nonzero value reached `jy_exe`.
The zero-movement result therefore does **not** yet distinguish among vendor
`/simple_cmd` forwarding, packet encoding/cadence, mode ownership, app
arbitration, or motion-controller acceptance. It must not be treated as evidence
that a larger value is needed.

### Follow-up read-only diagnosis — 2026-09-19

A later read-only inspection identified the exact vendor forwarding boundary
without transmitting another posture command:

- `/simple_cmd` had one publisher, the EmotionBot `posture_bridge`, and one
  subscriber, the vendor `/ros2qnx` node.
- The deployed vendor source at
  `~/lite_cog/transfer/src/message_transformer/src/ros2qnx.cpp` copies all three
  `SimpleCMD` fields into the packed 12-byte vendor structure and calls UDP
  `sendto()` for `192.168.1.120:43893`.
- The callback stores but does not inspect or log the `sendto()` result. A ROS
  `/simple_cmd` observation therefore still does not prove successful wire
  delivery or motion-host acceptance.
- The vendor perception manual requires enabling the app's Auto mode for its
  documented `/cmd_vel` procedure. It does not explicitly state that Auto mode
  gates `/simple_cmd` pose commands. Auto-mode or controller ownership is
  therefore a testable hypothesis, not a confirmed cause of the failed posture
  trials.
- The robot remained sitting in basic state `1`, with battery `56%`, zero error
  flags, centered fresh Retroid input, STOP false, supervisor `DISARMED`, and
  both persistent transmit flags false. The Pro manual recommends starting with
  at least `75%` battery, so no new motion attempt was made.
- The camera endpoint at `rtsp://192.168.2.1:8554/test` answered an RTSP
  `OPTIONS` request with `200 OK`. No video frames were decoded, so this proves
  service availability rather than usable visual evidence.
- `make -C lite3-noetic verify-hardware-offline` passed the clean Release build,
  launch enumeration, static checks, and all 14 protocol/safety unit tests.

The two robot computers also had inconsistent wall clocks during this check:
the motion host reported `2026-09-19`, while the perception host and ROS header
timestamps reported `2024-09-12`. Runtime safety uses local monotonic clocks,
but future captures must not correlate events across hosts by wall-clock time
until the clocks are explicitly synchronized or a shared sequence marker is
recorded.

The first instrumented Joy rerun established that the packet did leave the
perception host, but also exposed a command-serialization defect. ROS published
58 height messages while the vendor `/ros2qnx` callback, whose subscriber queue
depth is one, emitted only 16 height datagrams. The original posture bridge sent
height followed immediately by three zero-valued uncommissioned axes. Those
later messages could evict height before the callback ran; one observed height
gap was approximately `1.26 s`, longer than the documented one-second Pose-mode
validity window. The bridge was changed to serialize heartbeat, Pose-mode, and
only commissioned-axis commands one per timer tick. This finding proves neither
motion-host acceptance nor physical movement until a post-fix trial succeeds.

The post-fix rerun used the same bounded Joy height limit of `+4000` and
`1000 units/s`, with dynamic actions disabled. It produced the following result:

- the hardware mapper observed `joy` followed by `neutral`;
- ROS `/simple_cmd` reached `+4000` and later published exact zero;
- the passive wire observer recorded only heartbeat and height commands from
  `192.168.1.103` to `192.168.1.120:43893`, with no uncommissioned-axis traffic;
- the nonzero height stream had a median interval of approximately `54 ms` and
  a maximum interval of approximately `206 ms`, removing the earlier one-second
  expiry gap;
- a separately observed final height packet had value exactly zero;
- robot state remained `6`, with no error flags or supervisor fault; and
- the maximum measured joint-position span was approximately `0.00099 rad`,
  consistent with noise rather than an executed height change.

The operator-visible outcome was therefore still no confirmed posture movement.
This rules out missing EmotionBot state, missing `/simple_cmd`, and missing
perception-host interface emission as causes. The next investigation must focus
on motion-host acceptance, especially app Auto-mode/controller ownership and a
motion-host-side receive observation. Increasing the height amplitude is not
justified by these results.

### Auto-mode neutral-breathing trial — 2026-09-19

After the operator enabled Auto mode, a single bounded neutral-breathing trial
tested whether the default Gazebo idle rhythm would be accepted through the
physical posture path. Read-only preflight confirmed state `6`, zero errors,
fresh telemetry/joints/IMU, centered fresh Retroid input, STOP false, and no
publisher or output on `/cmd_vel`. Dynamic actions, locomotion, roll, pitch, yaw,
direct joints, and torque output remained disabled.

The Gazebo neutral profile uses a 0.25-second quintic entrance followed by a
1.375-second two-endpoint idle loop. For the first physical analogue, only its
height ratios and cadence were retained. A temporary configuration limited the
height command to `400` (2% of the documented `20000` protocol magnitude) at
`3000 units/s`; the idle endpoints were `+260` and `-156`. The requested sequence
lasted 5.5 seconds and then invoked the neutral/disarm service automatically.

Captured evidence showed:

- 109 neutral posture intentions, spanning the expected idle minimum of `-0.39`
  and a captured maximum of approximately `+0.696` normalized height;
- ROS `/simple_cmd` height values from `-156` to `+260`, with heartbeat traffic
  and no roll, pitch, or yaw commands;
- perception-host wire height values from `-156` to `+260`, with an approximate
  51 ms median and 104 ms maximum inter-height interval;
- robot basic state `6`, zero error flags, fresh/centered Retroid input, and no
  supervisor fault throughout the captured armed interval; and
- maximum measured joint-position span of approximately `0.00084 rad`, with only
  small IMU/attitude variation consistent with noise rather than an executed
  breathing motion.

No meaningful physical breathing movement was therefore measured. Auto mode did
not make this small posture sequence observable, but the test still does not
prove whether `jy_exe` accepted the nonzero command: the motion-host capture of
the nonzero interval was inconclusive. A subsequent exact-neutral check did
prove all three zero boundaries: `/simple_cmd` value `0`, perception wire value
`0`, and a 12-byte `0x21010102` value-`0` datagram arriving on motion-host `eth1`
from `192.168.1.103` to `192.168.1.120:43893`.

The trial also closed a mapper-failure gap found during research. Neutral
breathing is now an explicitly configured, disabled-by-default height-only
animation. The posture bridge expires stale posture intentions to exact zero,
and the mapper and posture bridge are required roslaunch nodes. A shutdown race
that attempted to publish after ROS had closed the topic was guarded without
weakening runtime publish failures.

Battery telemetry fell from `34%` during preflight to `26%` after the run and
`23%` in the final post-teardown read. No further nonzero command was sent. The
persistent service was restored with breathing and both transmit flags disabled,
supervisor `DISARMED`, robot state `6`, zero errors, and both hardware services
active. Repeat physical testing requires a charged replacement battery and a
reliable motion-host capture of a nonzero height datagram; the amplitude must not
be increased merely because this small trial showed no movement.

### Retroid-compatible direct neutral trial — 2026-09-19

The next investigation captured the missing app behavior and then reproduced it
in one explicitly authorized direct diagnostic. The Retroid reference contained
387 packets over 19 seconds. Its captured height values ranged from `-29332` to
`267`, and vertical right-stick traffic paired height with yaw command
`0x21010135`, mainly using companion value `32768`. The reference also showed
session establishment through Move followed by Pose.

The successful custom trial bound a Windows UDP socket to
`192.168.2.28:43897` and targeted motion host `192.168.2.1:43893`. After all
read-only gates were healthy, it sent this exact sequence:

1. four `0x21040001` heartbeats at 2 Hz;
2. one Move command `0x21010D06`, then waited 2.0 seconds;
3. one Pose command `0x21010D05`, then waited 1.5 seconds;
4. at 50 Hz, one yaw command `0x21010135` with value `32768`, immediately
   followed by one height command `0x21010102`; and
5. in the unconditional shutdown path, five yaw-value-`0` plus height-value-`0`
   pairs, with 20 ms between pairs.

The neutral height waveform used a 4-second rate-limited entrance and a
10-second period. The positive limit was `+10000`, 50% of the documented
positive protocol magnitude; its preserved `-0.39` waveform ratio produced the
negative endpoint `-3900`. Maximum height slew was `4000 units/s`. No Retroid
height sample was replayed, and the much larger captured app value was not used.

During 16.2 seconds, 810 height samples covered exactly `-3900` through
`+10000`. The whole-run maximum 12-joint position span was `0.2544403 rad`, and
the maximum IMU orientation-component span was `0.00856887`. Later
phase-isolated telemetry showed that most of this excursion belonged to the
Move-to-Pose transition; a full subsequent waveform window measured only
`0.0011444 rad`. This first waveform therefore did not prove continuing breath
motion. Robot basic state remained `6`, error flags remained zero, and battery
was 62% at the end; a subsequent fresh read reported 61%.

The operator explicitly selected 25% as the abort floor after being told that
the Pro manual recommends starting at 75%, and subsequently selected the same
floor for this hardware runtime. This is an operator override for this system,
not a revision of the manufacturer guidance. The test retained the normal
state, freshness, centered-Retroid, STOP, finite-feedback, and human coverage
gates.

The yaw value `32768` is outside the documented signed yaw posture range and was
not used as an intended yaw angle. It is recorded as an opaque Retroid-compatible
companion value for the tested deployed software.

A follow-up reset joint/IMU extrema only after the mode handshake and ramped a
fixed height from `0` to `-10000`. During that active-only interval it measured
`0.2484894 rad` maximum joint span and `0.0078653` maximum IMU
orientation-component span, while state remained `6`, errors remained zero, and
five zero pairs were acknowledged on exit. That is the first evidence here that
the height command itself, rather than only the mode transition, actuated the
body. It also showed that the earlier periodic `+10000..-3900` range did not
cross the deployed controller's useful deadband.

The maintained host bridge now implements the handshake, atomic pair input,
250 ms relay watchdog, independent input-age gates, exclusive ownership,
neutral-emotion check, two-second stable dwell, and acknowledged zero exit. It
starts by default with the hardware emotion launcher while the persistent
robot-side transmit flags remain false. The neutral waveform is `0..-10000`,
bounded to 50% of the documented magnitude. The final periodic profile could
not be re-run after telemetry fell below the operator-selected 25% floor; the
bridge correctly paused and is designed to resume after a replacement battery
restores all gates.

### Read-only direct-joint neutral-anchor capture — 2026-09-19

After the development computer was reconnected to the robot network, a new
request considered driving the neutral breathing animation from measured joint
positions instead of the Retroid-compatible Pose path. This session performed
read-only preflight and anchor measurement only. It did not send an SDK acquire,
release, joint, torque, pose, gait, action, Stand/Sit, or STOP command.

Live telemetry reported basic state `6` (standing), battery `96–97%`, zero error
flags, a compatible reviewed `0x0906` layout, healthy high-rate feedback, and
healthy contact indications for all four legs. The neutral anchor below is the
mean of 251 direct-feedback samples collected over approximately three seconds.
Values use the MotionSDK convention, which is sign-inverted relative to the
vendor ROS `/joint_states` positions:

| Leg | HipX (rad) | HipY (rad) | Knee (rad) |
| --- | ---: | ---: | ---: |
| FL | `0.0640573` | `-0.6807123` | `1.4064087` |
| FR | `-0.0756085` | `-0.6941565` | `1.4113382` |
| HL | `0.0465362` | `-0.6786010` | `1.3910077` |
| HR | `-0.0561386` | `-0.6704631` | `1.3976746` |

The maximum observed position span of any joint was `0.0009155 rad`. The
existing planted neutral profile is a six-second quintic cycle: three seconds
from exact measured neutral to 55% of its `0.012 rad` compression amplitude,
then three seconds back to exact measured neutral. At the `0.0066 rad` peak,
HipX remains fixed, every HipY moves `-0.0066 rad`, and every knee moves
`+0.0132 rad`. The resulting peak targets are:

| Leg | HipX (rad) | HipY (rad) | Knee (rad) |
| --- | ---: | ---: | ---: |
| FL | `0.0640573` | `-0.6873123` | `1.4196087` |
| FR | `-0.0756085` | `-0.7007565` | `1.4245382` |
| HL | `0.0465362` | `-0.6852010` | `1.4042077` |
| HR | `-0.0561386` | `-0.6770631` | `1.4108746` |

The derived target passed the planted-symmetry validator, and the 26 offline
hardware protocol, gate, mapping, waveform, and supervisor unit tests passed.
These offline results do not authorize physical transmission.

Physical direct-joint execution remained blocked for three independent reasons:

- the persistent direct-joint transmit flag was `false`, and there was no live
  direct command publisher, safety publisher, or MotionSDK bridge;
- the unprivileged hardware core was restart-looping because
  `posture_bridge.py` could not import `message_transformer`, so the supervisor
  and its fail-closed safety topic were absent; and
- `stop_preemption_verified` remained `false`. Ignoring the Retroid control path
  removes the only investigated human STOP observation and requires a hoist or
  equivalent independent restraint plus an independent physical power cutoff or
  emergency stop before SDK ownership may be commissioned.

The motion host clock reported `2026-09-20` while this record uses the
development-host date `2026-09-19`; the previously documented cross-host clock
mismatch therefore remains relevant.

### Hoisted direct-joint acquisition trials — 2026-09-19

The operator confirmed that the robot was attached to a load-rated hoist, an
independent physical cutoff was ready, and a human operator was present. The
robot's feet still supported its standing weight. Two bounded attempts then
tested whether MotionSDK control could take over the freshly measured standing
pose before applying the planted neutral waveform.

The first attempt used `hold_only=true` and a 10% commissioning scale. It sent
the freshly measured joint positions with zero requested offset. The operator
reported a short flinch followed by an apparent hold. The bridge exited through
its release path after approximately seven seconds. Comparing 203 stable frames
after release with the pre-test anchor showed asymmetric persistent stance
changes up to `0.05292 rad`; HipX changed up to `0.03776 rad` despite the planted
controller prohibiting HipX motion. The robot remained in basic state `6` with
zero error flags and healthy contacts.

Before the second attempt, the planted controller was corrected so a neutral
profile begins at exact measured neutral instead of an arbitrary monotonic-clock
phase. All 26 offline hardware unit tests passed. A pre-attached recorder then
captured the full 10%-scale attempt:

- the bridge published `DISARMED`, then `ACTIVE` with
  `SDK_ACQUIRED with measured hold`;
- only 38 joint-command samples were emitted before release;
- the largest requested change reached only `0.00000945 rad` at each HipY and
  `0.00001891 rad` at each knee; HipX requests remained exactly zero;
- measured joint spans nevertheless reached `0.32715 rad` HipX, `0.70900 rad`
  HipY, and `0.67650 rad` knee;
- the safety bridge detected `measured joint error exceeds limit`, sent the
  explicit release, and reported `FAULT_RELEASE_ATTEMPTED`;
- basic state remained `6`, error flags remained zero, and the persistent
  transmit flags remained false.

After teardown, 278 samples showed a stationary maximum span of `0.000839 rad`,
basic state `6`, battery `77%`, zero error flags, and healthy contacts. No direct
sender, command topic, bridge-status topic, or ownership marker remained.

A loopback-only capture of the official aarch64 MotionSDK on the motion host
then established the vendor semantics without targeting the robot:

- `Sender::ControlGet(SDK)` emitted the 12-byte simple command `0x0114`;
- `Sender::RobotStateInit()` emitted `0x31010C05`, documented as joint reset;
- `Sender::ControlGet(ROBOT)` first emitted a 252-byte `0x0111` damping command
  with zero positions and `kp=5`, waited two seconds, then emitted `0x0113`.

This proves that the locally generated packet shape and SDK acquisition code
matched the vendor library. It also disproves the assumption that `0x0114`
provides a bounded, seamless takeover from the vendor standing controller. The
acquisition transient dominates the tiny requested expression and cannot be
made safe by reducing the breathing amplitude. The direct bridge now has an
additional fail-closed `takeover_transition_commissioned=false` gate. Future
direct-joint work must implement and measure a vendor-supported SDK
zero-to-stand transition while fully suspended before any emotion offset is
re-enabled.

The gate was then built and deployed to the perception computer. A clean local
Release build, 26 unit tests, the MotionSDK packet test, and the loopback-only
ownership/graceful-release/crash-watchdog integration test passed. The deployed
executable was relinked explicitly after the robot computer's clock skew left an
older generated binary timestamp in the future; its compiled strings and packet
test confirmed the new gate. The final read-only audit found both persistent
transmit flags false, no direct controller or sender node, no ownership marker,
supervisor state `DISARMED`, basic state `6`, zero error flags, stable stand,
healthy joint/IMU/SDK feedback, and battery `68%`. No further robot command was
sent.

### Official MotionSDK zero-to-stand and continuous breathing — 2026-09-19/20

The next explicitly authorized, fully restrained commissioning sequence stopped
trying to acquire SDK control from a vendor-controlled standing pose. Every
attempt began in basic state `1` (sitting/initialized), called
`Sender::RobotStateInit()`, and used the vendor `PreStandUp` and `StandUp`
trajectories before any expression offset. The symmetric vendor stand target was
HipX `0`, HipY `-42 degrees`, and knee `+78 degrees` on all four legs. A stable
one-second exact-neutral hold followed the stand trajectory.

The runner reads the reviewed `0x0906` joint and IMU feed passively from
`/dev/shm/emotion_bot_lite3_telemetry`; it never binds or competes for UDP port
`43897`, which remains owned by `qnx2ros`. If that feed is initially absent
while sitting, only the initialized zero-position command is held for at most
250 ms to bootstrap SDK feedback. The stand trajectory cannot begin until a
fresh, finite frame exists. Exact 240-byte outgoing MotionSDK `0x0111` packets
are now consumed by the telemetry tap without publishing the high-rate packet as
ROS JSON, preventing diagnostic serialization from starving the safety feed.

Two early continuous attempts demonstrated why a single 100 ms hard timeout was
not sufficient. They completed feedback bootstrap, `RobotStateInit`, and
`PreStandUp`, then measured `0x0906` ages of `144.336 ms` and `165.787 ms`
during `StandUp`. Both attempts stopped immediately and executed the MotionSDK
return-to-robot sequence; neither entered breathing or retried. The release
caused the supported robot to lower rather than preserving the SDK stand.

The replacement two-stage watchdog does not hide those gaps. At 100 ms it
freezes trajectory time and sends the last validated positions with zero
velocity and torque. It requires 20 distinct finite frames at no more than 20 ms
age before advancing again. A 250 ms age, non-finite value, tracking violation,
signal, or other fault still causes an immediate no-retry return to robot. The
trajectory clock is capped to a 5 ms step after scheduling delays. An initial
continuous run with this behavior completed 12 five-second cycles; its maximum
recorded feedback age/update gap was `156.010/156.301 ms`. The watchdog paused
and recovered rather than advancing blindly. The operator ended that run after
independent telemetry showed basic state `8`; at that point state `8` was not yet
an automatic runner input.

The passive tap was therefore extended with a second sequence-locked record,
`/dev/shm/emotion_bot_lite3_robot_state`, containing each validated raw 200-byte
`0x0901` body. The runner checks it during initialization, both stand phases,
the neutral hold, and every breathing update. Basic state `8` or nonzero error
flags stop trajectory advancement and enter the same return-to-robot path. The
first test of this interlock released conservatively in `PreStandUp` after a
single sequence-lock collision. The reader was corrected to retain the last
fully validated state across transient contention while still enforcing its
real age; the offline hardware suite then passed all 27 tests, the aarch64
Release build passed, and the standalone C++ state-safety test passed.

The final live profile used the full commissioned symmetric compression
amplitude: every HipY commanded `-0.0120 rad`, every knee `+0.0240 rad`, and
HipX remained fixed. Each cycle used a quintic 2.5-second neutral-to-peak half
and a 2.5-second peak-to-exact-neutral half, with zero velocity at the start,
midpoint, and seam. It included no roll, yaw, gait, hop, stomp, or asymmetric
motion.

That run completed `RobotStateInit`, `PreStandUp`, `StandUp`, the stable neutral
hold, and 19 complete five-second breathing cycles (95 seconds). Across the run,
the largest measured span for each joint family was:

| Joint family | FL (rad) | FR (rad) | HL (rad) | HR (rad) | Overall maximum (rad) |
| --- | ---: | ---: | ---: | ---: | ---: |
| HipX | `0.0006866` | `0.0008392` | `0.0006104` | `0.0011444` | `0.0011444` |
| HipY | `0.0104523` | `0.0124359` | `0.0098419` | `0.0117493` | `0.0124359` |
| Knee | `0.0159454` | `0.0203705` | `0.0183105` | `0.0234222` | `0.0234222` |

Five recorded feedback gaps crossed the 100 ms pause threshold and all five
recovered. Maximum feedback age was `148.442 ms`, maximum consecutive update gap
was `148.665 ms`, and the longest recovery pause was `81.2722 ms`. During cycle
20 the independent safety record reported basic state `8`, error flags `0`, and
age `0.501792 ms`. The runner immediately aborted the active cycle, called the
MotionSDK return-to-robot sequence, removed its ownership marker, and exited
without retrying or sending STOP. The post-release observation was basic state
`1`, gait/motion states `0/0`, battery `41%`, error flags `0`, no runner process,
and no SDK ownership marker. High-rate SDK feedback was unhealthy after release,
as expected when SDK control and its command stream were no longer active.

This proves the official sitting-to-stand path, stable hold, full-amplitude
continuous symmetric breathing, gap-aware pause/recovery, independent state-8
preemption, and clean SDK release on this restrained Lite3. It does not prove
that the robot can or should remain standing after SDK release: the observed
vendor return path finished in state `1`. Continuous standing therefore means
continuing to hold SDK ownership until an operator signal or safety event, never
bypassing release on a fault.

#### Gazebo-shaped animal breathing — 2026-09-20

The operator requested a more intense physical neutral that felt like a
breathing animal. Source inspection established that Gazebo neutral is a
1.375-second alternating height, roll, and pitch loop; its yaw command is
exactly zero. Directly copying the simulation-only `0.100 m`/`0.625 rad`
envelope or introducing planted yaw was rejected. The hardware translation kept
HipX fixed, yaw zero, all four feet planted, and all existing watchdogs while
adding bounded differential leg compression for roll and pitch.

The new 3.25-second cycle has three zero-velocity quintic segments:

1. 0.75 seconds from exact neutral to `-0.008 rad` base HipY extension,
   `+0.004 rad` roll bias, and `-0.003 rad` pitch bias;
2. 1.25 seconds to `+0.020 rad` base HipY compression, `-0.004 rad` roll bias,
   and `+0.003 rad` pitch bias; and
3. 1.25 seconds back to exact neutral.

Knee displacement and velocity are twice each leg's combined HipY compression
scalar. Left/right and front/rear bias signs produce the planted torso sway. The
combined per-leg scalar is analytically bounded to `-0.015..+0.027 rad`, so the
largest knee offset is `0.054 rad`, below the existing `0.10 rad`
tracking-error abort threshold. A new pure C++ profile test checks the exact
neutral seam, zero endpoint velocities, finite samples, and those bounds.

Before transmission, the standalone profile test passed locally and on the
aarch64 robot host. The complete offline hardware verification also passed: a
clean Release build, all 27 Python tests, exact packet test, lease/graceful
release/crash-watchdog integration test, and launch enumeration. The live
preflight then found basic state `1`, gait/motion `0/0`, battery `37%`, error
flags `0`, fresh telemetry, compatible SDK layout, no runner or ownership
marker, the passive telemetry service active, and the existing `qnx2ros`
process unchanged. The battery was above the previously documented 25%
operator-selected floor but below the Pro manual's normal 75% start guidance.

The one authorized live attempt completed `RobotStateInit`, `PreStandUp`,
`StandUp`, the one-second neutral hold, and at least 27 complete animal-breath
cycles (87.75 seconds) by the handoff checkpoint. Maximum observed per-joint
spans through that checkpoint were:

| Joint family | FL (rad) | FR (rad) | HL (rad) | HR (rad) | Overall maximum (rad) |
| --- | ---: | ---: | ---: | ---: | ---: |
| HipX | `0.0019074` | `0.0016022` | `0.0014496` | `0.0017548` | `0.0019074` |
| HipY | `0.0296021` | `0.0481415` | `0.0154877` | `0.0315857` | `0.0481415` |
| Knee | `0.0450134` | `0.0708771` | `0.0212860` | `0.0467682` | `0.0708771` |

Maximum feedback age was `150.050 ms` and maximum consecutive update gap was
`151.049 ms`. Four gaps crossed the 100 ms pause threshold; all four held the
last validated command with zero velocity/torque and recovered after 20 fresh
frames. The longest recovery pause was `90.9427 ms`. No tracking error, state-8
event, nonzero error flag, signal, or dead-stream release occurred by the
checkpoint. The continuous runner and SDK ownership marker were intentionally
still present because the operator accepted the motion and had previously asked
that it keep looping. All fault paths, including fresh state `8`, remained armed
to release without retry or routine STOP.

### Remaining work

- Keep `direct_joint.takeover_transition_commissioned=false`; do not retry
  measured-anchor takeover from the vendor standing controller.
- Preserve the commissioned official MotionSDK sitting-to-stand path; never
  reinterpret it as permission for seamless takeover of an existing stand.
- Investigate why the deployed controller entered basic state `8` before any
  longer unattended run. Keep the state-8 interlock fail closed and never
  restart automatically after it fires.
- Retain the measured two-stage `0x0906` watchdog. The live feed still produced
  gaps up to `148.665 ms`; do not replace the pause/recovery logic with a larger
  blind trajectory-advance timeout.
- Keep the repaired robot-side core environment and both persistent transmit
  flags fail closed; require the supervisor and direct safety topic to remain
  live before any future fully suspended commissioning attempt.
- Verify direct-joint STOP preemption under a hoist or equivalent independent
  restraint, with a non-software emergency cutoff and a human operator ready.
- If those gates pass, begin with a measured-anchor hold-only acquisition before
  requesting even a scaled neutral compression cycle.
- Re-run the final periodic `0..-10000` profile after the replacement battery is
  installed and record a phase-isolated full-cycle joint span.
- Treat yaw `32768` as firmware-specific opaque framing and verify it again after
  any app, profile, or Deeprcs update.
- Keep the checked-in robot-side transmission and breathing flags false; the
  default direct host bridge remains a separately owned neutral-only path.

## Sources

- Local vendor manuals under [`lite3-robot-docs`](../../lite3-robot-docs/README.md).
- [Official Lite3 perception development manual](https://www.deeprobotics.us/wp-content/uploads/2025/10/Jueying-Lite3-Perception-Development-Manual-beta-V2.2.2-0.pdf).
- [Official Lite3 MotionSDK](https://github.com/DeepRoboticsLab/Lite3_MotionSDK).
- [Official Retroid gamepad repository](https://github.com/DeepRoboticsLab/gamepad).
