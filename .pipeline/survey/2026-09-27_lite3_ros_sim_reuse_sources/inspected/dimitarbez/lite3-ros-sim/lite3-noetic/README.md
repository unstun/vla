# Lite3 Noetic conversational emotion simulator

This wrapper runs ROS Noetic and Gazebo in Docker on a WSL2/Ubuntu host. It preserves the original Lite3 workflow and adds a conversational simulation stack plus an explicitly separate, fail-closed split-host hardware package.

For a terminal-by-terminal walkthrough, start with the [usage guide](docs/USAGE.md).

The workspace repository pins the active Lite3_VMC and emotion-bot revisions as Git submodules. Its clean `lite3_vmc_upstream` reference checkout records the upstream base.

Normal simulation targets contain no physical-robot executable or robot UDP path. Hardware use requires the separately named hardware targets and the package under `hardware-ws/`; its checked-in configuration cannot transmit or arm.

## Setup

Clone the workspace with its pinned sibling checkouts:

```bash
git clone --recurse-submodules git@github.com:dimitarbez/lite3-ros-sim.git ROS
cd ROS
```

Do not run checkout or pull over a modified tree. Build and start the two images and the development container:

```bash
make -C lite3-noetic build
make -C lite3-noetic start
make -C lite3-noetic bootstrap
```

## Run it

For live streamed OpenAI responses, put the key in the persistent local file `ws/Lite3_VMC/.env`:

```dotenv
OPENAI_API_KEY=replace-with-your-key
```

Keep the file Git-ignored and mode `600`, then run:

```bash
make -C lite3-noetic run-emotion-sim-openai
```

The live target reads the local file, starts a disposable Python 3.12 sidecar on loopback, passes the key by environment-variable name, and removes the sidecar at shutdown. It does not put the key in ROS, the Docker image, a command argument, tracked source, or logs.

The terminal chat client is only the interface. When the stack was launched with `run-emotion-sim-openai`, completed live turns report `chat_backend=openai`. The separately reported `emotion_backend=deterministic` identifies the local EmotionBot appraisal engine, not the assistant-response provider. The offline simulator targets are retained only for deterministic testing and troubleshooting.

In another terminal, open the conversational client:

```bash
make -C lite3-noetic run-emotion-chat
```

Each input gets a turn ID. A newer input cancels the previous unfinished turn. The client prints deltas as they arrive, then the final reply and matching emotional state. The integrated simulator enables bounded motion automatically after controller readiness, model health, and stance settling. Motion can still be enabled again after a fault or manual disable with:

```bash
docker exec lite3-noetic-dev bash -lc \
  'source /opt/ros/noetic/setup.bash && rosservice call /emotion_bot/set_motion_enabled "data: true"'
```

Disable it with the same service and `data: false`. The deterministic demonstration enables motion only when requested and always disables it on exit:

```bash
make -C lite3-noetic emotion-demo EMOTION_MOTION=true
```

## Architecture

The ROS container stays compatible with Noetic's Python 3.8 and imports EmotionBot's reusable `EmotionEngine` from the read-only sibling checkout. Chat coordination is a separate node. The optional sidecar uses Python 3.12 and the pinned official OpenAI SDK with the Responses streaming API. It binds only to `127.0.0.1`; if it times out or fails, the chat node retries once and falls back to the deterministic backend without bypassing the motion safety layer.

Emotion state and actuation are separate. The mapper filters valence/arousal and blends/rate-limits each expression. A non-neutral category change now cancels the old choreography, returns to exact zero for 0.25 seconds, holds that canonical stance for 0.35 seconds, and only then starts the new emotion's entrance; previous pose residue cannot accumulate across switches. All nine chat profiles continuously loop expressive height/roll/pitch body language while their state remains active. Entrances use a 1.25 theatrical gain, while recurring idle motion uses 65% amplitude at 1.25x cadence for a calmer loop. Joy and surprise add centered hops, and anger adds recurring symmetric stomps. Normal profiles publish zero x/y/yaw and never select the unstable Lite3 walk gait. Simulation stance control also centers all four abduction joints to prevent crossed or V-shaped legs. The dynamic model remains unfixed and a bounded simulator-only recovery recenters incidental contact drift. The bridge clamps every command, expires stale sources, and publishes the simulator's sole Joy input. Initial and disabled output is zero.

## Verification

The offline repeatable suite is:

```bash
make -C lite3-noetic verify-emotion
```

It runs static checks, a clean Release catkin build, EmotionBot/package unit tests, an offline process-boundary streaming test, ROS integration, and the headless Gazebo physical-motion/safety test. It needs no key, internet, microphone, GUI, or robot.

The split-host protocol, packet, mapping, action-phase, and supervisor tests are separate:

```bash
make -C lite3-noetic verify-hardware-offline
```

## Split-host hardware development

With the robot sitting and connected, run the one-time fail-closed installer with
`make -C lite3-noetic setup-emotion-hardware`. It installs separate unprivileged
core and narrowly privileged passive-observer services without modifying vendor
software. Thereafter, terminal one uses
`make -C lite3-noetic run-emotion-hardware` and terminal two uses
`make -C lite3-noetic run-emotion-chat`. The first command owns the SSH tunnel,
OpenAI sidecar, development-computer brain, and default neutral-height bridge,
and cleans them up on Ctrl-C. Set `HARDWARE_NEUTRAL_BREATHING=false` only for a
brain-only diagnostic.
Neither target is called by a simulation target.

The robot-side package and its commissioning boundary are documented in [`hardware-ws/README.md`](hardware-ws/README.md). It is a separate catkin workspace and must not be copied into or used to edit vendor `lite_cog`/`qnx2ros`. The public MotionSDK does not establish a Deeprcs `2.0.153` byte-layout match, so direct-joint actions remain hard-disabled until a reviewed layout, independent STOP-preemption result, and measured trajectories exist.

A 2026-09-19 bounded direct diagnostic produced the first measured height
response by matching the Retroid app's Move-to-Pose handshake and paired axis
framing. The maintained launcher now runs that neutral-only host bridge by
default while the persistent robot-side graph remains fail-closed. See the
hardware workspace README and
[`docs/HARDWARE_APP_CONTROL.md`](docs/HARDWARE_APP_CONTROL.md) for the exact
sequence, measurements, shutdown boundary, and battery-policy caveat.

With a key in the shell, one live metadata-only smoke request is available separately:

```bash
make -C lite3-noetic emotion-openai-live-smoke
```

## Original Lite3 workflow

For baseline troubleshooting, run each target in its own real terminal:

```bash
make -C lite3-noetic run-gazebo
make -C lite3-noetic run-spawn
make -C lite3-noetic run-sim
make -C lite3-noetic run-keyboard
```

Press Enter once in `run-spawn` to start controllers and keep it attached. Do not send the second Enter until the test ends. The integrated launch avoids this stdin-sensitive path.

The wrapper mounts `lite3-noetic/` read-write at `/workspaces/lite3-noetic` and `emotion-bot/` read-only at `/workspaces/emotion-bot`. If an existing container has stale mounts, run `make -C lite3-noetic restart`.

See [usage](docs/USAGE.md), [the workflow](docs/WORKFLOW.md), [troubleshooting](docs/TROUBLESHOOTING.md), [verification record](docs/VERIFICATION.md), [hardware app-control research](docs/HARDWARE_APP_CONTROL.md), and [package reference](ws/Lite3_VMC/src/emotion_bot_ros/README.md).
