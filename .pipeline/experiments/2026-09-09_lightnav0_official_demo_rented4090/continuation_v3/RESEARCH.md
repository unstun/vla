---
origin: local_source_inspection+official_documentation+remote_preflight
reviewed: false
date: 2026-09-09
stage: experiment_and_analysis_preparation
---

# LightNav-0 continuation: evidence and visualization investigation

This investigation prepares a manual Opus package. No new LightNav inference or
navigation episode was run. Static renderer probes are explicitly separate.
Paths starting `UP/` refer to the pinned repository in
`references/upstream/2026-09-09_lightnav0_official_demo/source/LightNav-0`.
Paths starting `EXP/` refer to this directory's parent.

## Confirmed baseline and existing result

- Canonical source: https://github.com/lightorigins/LightNav-0, Apache-2.0,
  commit `d83fbfb9748ca6b497a2f2a7f4a3e95e2110e40c`.
- The live GitHub API still reported that pinned commit as the head; the two
  open issues concern EVT-Bench data collection and Windows path length, not
  this demonstration's target/stop behavior. `research/upstream_status.json`
  preserves the query time and original metadata. No source upgrade is needed.
- Checkpoint: https://huggingface.co/LightOriginsHQ/LightNav-0,
  revision `826dc5fbfa37afa8293d2e336d329b6ffc0bfb64`, original BF16.
- Official case: ProcTHOR `val_2_ceiling.xml`, TurtleBot, spawn `(6.5,13.8,0)`,
  instruction `move forward, then go to the trashcan on the right`.
- Round 1 produced 41/39/45 model records and 40/38/44 harness decisions.
  All three runs emitted native STOP and then remained still in the saved
  snapshots. Their terminal distances to the selected ashcan root were
  2.414/2.274/2.609 m, independently recomputable from the scene XML and
  `runs/rep_0*/episode.json`. This is not successful arrival at the trashcan.
- A complete official model-input stream survives in `records/`; the harness's
  first-/third-person capture streams are incomplete. The distinct failures
  and missing deliverables are enumerated in `review/LEAD_REVIEW_2026-09-09.md`.
- The separate 5070 Ti trial proves nine BF16 open-loop predictions with a
  12.35 GiB sampled total-card peak. It supplies no new closed-loop video.

## Current execution host

`research/remote_preflight.json` records the live read-only checks at
2026-09-10 02:46:38 UTC (2026-09-09 PDT):

- `rented4090` resolves to `ubuntu@117.50.179.202:22`, hostname `10-60-164-100`.
- RTX 4090: 24,564 MiB total, 2,907 MiB used, 21,175 MiB free; driver 575.57.08.
- Existing Isaac Sim process: PID 1251, start tick 2380, full command and boot ID
  retained in the JSON. The former PID 1247 is stale after restart.
- Ports 8050/8088 were free. Disk free space was 47 GiB.
- The model and demo environments remain installed. Versions: torch 2.10.0,
  vLLM 0.19.1, Transformers 5.8.0, CUTLASS DSL 4.5.2, MuJoCo 3.11.0,
  aiohttp 3.14.3, CasADi 3.7.2.
- All 20 checkpoint files were rehashed successfully: 9,709,350,260 bytes.
- 2,449 pinned source files matched. `mujoco_demo/uv.lock` differs from the
  pinned file; the earlier verifier explicitly ignored that runtime-resolved
  lock. Do not call the entire remote tree pristine. Recreate the v3 work copy
  from the local pinned snapshot and reuse the installed interpreter directly,
  avoiding an implicit `uv run` dependency re-resolution.
- Only rep_01..03 were present. Recheck at execution time before scheduling new
  repetitions; a package's existence is not evidence of dispatch.

## Code findings that change the recording design

| Finding | Source anchor | Consequence |
| --- | --- | --- |
| File names are derived from `index_file.tell() // 200` | `EXP/scripts/run_episode.py:fetch_camera` | Variable JSON row length causes collisions. The first/third streams retained only 56/51/58 of 87/79/90 polled frames. A unique counter and exclusive creation are required. |
| HTTP images carry no frame stamp or capture pose | `UP/mujoco_demo/vln_mujoco/server.py:camera_response` | Two independent HTTP GETs and a nearby health snapshot cannot establish exact same-frame alignment. |
| Native front and third-person frames share a capture pose and stamp | `UP/mujoco_demo/vln_mujoco/simulation.py:_run`, `CameraFrame` | Capture the original pair plus MuJoCo state at that render point; do not infer identity from poll order. |
| `stamp_ns` is wall time generated after rendering; `sim_time` is sampled separately by health | same source | Record monotonic capture time and the state time inside the capture lock as additional telemetry, without replacing the original stamp. |
| The model wire payload does not contain the camera stamp | `UP/mujoco_demo/vln_mujoco/vln_client.py:_connection` | Add a sidecar mapping of run/session/connection/seq to stamp and JPEG SHA-256; leave wire fields unchanged. |
| The server records after sending a result | `UP/src/lightnav/serving/ws_server.py:record_step`, `make_handler` | `received_at` is not camera capture time. Join model records by connection/seq and JPEG identity, not by nearest timestamp alone. |
| Native STOP and pending results cross asynchronous boundaries | `UP/mujoco_demo/vln_mujoco/server.py:update_loop`; `vln_client.py:_connection` | Record whether each response reached MPC, was consumed as STOP, or was discarded after shutdown. A post-stop inference record is not renewed robot motion. |
| Native third-person camera is attached to the robot | `UP/mujoco_demo/vln_mujoco/robots/turtlebot.py:third_person_camera` | It is a chase view, not a global overview. Add an offline world-fixed overhead view. |
| The upstream ribbon uses an automatic forward display offset | `UP/docs/VISUALIZATION.md`, `UP/src/lightnav/viz/projection.py` | The default overlay is illustrative. Use zero offset or calibrated full-camera projection for metric review; never interpret the shifted ribbon as the actual ground location. |
| HUD velocity is first waypoint divided by a display dt | `UP/docs/VISUALIZATION.md` | Show MPC requested command and observed robot velocity separately. Do not relabel the upstream HUD as executed velocity. |
| `realtime` clamps each step to 1..20 video frames | `UP/src/lightnav/viz/video.py:step_repeats` | Official overlay MP4s cannot be the wall-time truth source. Generate the primary film on recorded monotonic time with all stalls retained. |
| TurtleBot updates kinematic state, not contact-resolved locomotion | `UP/mujoco_demo/vln_mujoco/robots/turtlebot.py:step` | The result cannot establish quadruped behavior or contact safety. |

## Selected visualization architecture

Use a small, optional capture observer in the v3 execution copy. At the existing
camera-render point, copy the two original JPEG byte strings and a MuJoCo state
snapshot associated with the same immutable identity. Move disk writes to a
bounded queue. No additional live cameras, high-resolution renders or live video
encoding may run in the model/control loop.

After stopping the model and demo, restore saved state into a separate render-only
MuJoCo model. Render a high-resolution, world-fixed orthographic overhead camera.
Only this separate visualization model may hide named ceiling geoms. Re-rendering
must call `mj_setState` and `mj_forward`, never simulate inferred/interpolated
motion with `mj_step` or replay commands. Record the rendered view as **state replay**.
Original front and native chase JPEGs remain the evidence for what the live demo saw.

The public MuJoCo API documents `mj_stateSize`, `mj_getState`, `mj_setState`, and
`mj_forward` for restoring state without time integration:
https://mujoco.readthedocs.io/en/stable/APIreference/APIfunctions.html#mj-getstate
and https://mujoco.readthedocs.io/en/stable/APIreference/APIfunctions.html#mj-setstate.
Camera fields are documented at
https://mujoco.readthedocs.io/en/stable/APIreference/APItypes.html#mjvcamera.
The actual installed 3.11.0 renderer is checked by the static probe, rather than
assuming the rolling documentation exactly matches the installed binary.

## Static probe and an important failed assumption

`research/probe_visualization_v1.py` is the first probe. It advanced zero simulator
steps and loaded no VLA. State save/restore passed, but setting only
`MjvCamera.orthographic=1` left the actual GL camera in perspective mode
(`projection.orthographic=0`). Its JSON must not be treated as an orthographic PASS.
The original log/output are retained under `static_probe_01`.

The corrected `research/probe_visualization.py` additionally sets
`model.vis.global_.orthographic=1` and asserts the actual renderer's GL projection.
It passed in 4.64 seconds: actual orthographic flag 1, zero simulation steps,
exact state round trip, and unchanged native front pixels. Its returned files
were hash-checked locally and the overhead PNG was visually inspected.
The chosen static preset uses look-at `(8.8,11.5,0)`, elevation -90 degrees,
azimuth 90 degrees, distance 12 m, a 7 m vertical span, and 1024x768 output.
Only the ten `ceiling_*_visual_0` geoms are hidden in the visualization model.
The full integration state contains 3,034 float64 values in this compiled scene.
See `research/static_probe_02/result.json` for the actual result and source hash.
This proves static rendering feasibility, not moving-state replay or a new episode.

## What remains uncertain

The earlier explanation in `LEAD_ANALYSIS_2026-09-09_why_not_authors_result.md`
usefully identifies an early turn/straight divergence and later object-point
placement. Its stronger causal exclusions are not established by three runs:
similar average latency does not exclude asynchronous capture/control timing;
greedy decoding does not establish numerical identity; no saved logits prove a
near-tie. Treat these as hypotheses. The author GIF is a single demonstration,
not a success-rate baseline or an exactly replayable source trace.

Respect the recorded user decision to stay on official vLLM BF16. Do not reopen
HF-backend, FP8, prompt, controller, camera-input or checkpoint comparisons in
this package. Use the new traces to describe the first observable divergence;
propose any causal intervention separately after the fixed-case result is returned.

Detailed visual/temporal acceptance is in `VISUAL_SPEC.md`; the executable human
handoff is `EXECUTION_PACKAGE.md`.
