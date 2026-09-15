---
origin: lead_design+verified_upstream_interfaces
reviewed: false
date: 2026-09-09
status: execution_contract_not_yet_implemented
---

# Visual evidence specification

The user should be able to see the robot's complete route, the actual image the
model used, its predicted path/pointing, and the exact reason control stopped.
Deliver real, locally playable MP4 files. An HTML index or symlink is supplementary.

## 1. Primary film: one complete run per file

Create `media/rep_04/overview_wall.mp4`, likewise rep_05 and rep_06. Use
1920x1080 or 1920x1200, H.264/yuv420p, fast-start MP4, with a 20 fps presentation
timeline derived from recorded monotonic time. Use consistent fixed panel sizes,
preserve source aspect ratios with letterboxing, and keep essential text at
least 24 px at the master resolution. Source RGB is 480x270: label its native
resolution, and do not imply upscaling adds sensor detail.

| Panel | Required content | Time/meaning label |
| --- | --- | --- |
| A: robot view | Original native third-person chase JPEGs. Keep the robot visible. | `LIVE-CAPTURE CHASE`, capture stamp and frame age |
| B: model evidence | Exact JPEG attached to the latest completed model prediction; APOS mint, OPOS magenta, predicted waypoints blue, raw token text in a readable adjacent strip. | `MODEL INPUT`, request seq, capture time, result time, input age |
| C: route overview | World-fixed, orthographic overhead render of the saved MuJoCo state; actual path up to the current time, heading arrow, current MPC path, spawn, trashcan and dog-bed labels. | `OFFLINE STATE REPLAY`, state stamp, fixed scale/axes |
| D: behavior | Distance to trashcan, actual forward/yaw velocity, applied command, inference round-trip latency and MPC solve time, on a common time cursor. | Actual velocity vs requested/applied command must be separate |

Put the exact instruction, run ID, GPU/backend/precision, and episode wall time
in a top bar. Put simulator time, camera count, prediction count, recording loss
count, and control/termination state in a compact footer. Use color consistently:
actual path white/cyan, predicted path blue, intended trashcan green, dog bed amber.
Never use the model's OPOS color as a ground-truth target marker.

Model results lag image capture. All panels use one presentation clock, but
Panel B deliberately shows the older image associated with a completed result.
Display its age prominently. Do not overlay old APOS/OPOS pixels on a newer camera
image or show a result before its recorded arrival. During initialization or
inference stalls show `WAITING FOR RESULT` with the advancing wall clock.
If a completed result was discarded after STOP, mark it `NOT APPLIED`; never
replace the displayed applied MPC path or control state with that result.

Retain the whole instruction-to-termination interval and the measured two-second
post-stop observation. Do not remove stalls, failures, collisions, or excursions
outside the initial frame. Any extra held end card is separately marked editorial
time and excluded from measured duration. No retiming to resemble the author GIF.

## 2. Required supporting files for each new run

- `native_front_wall.mp4`: unannotated original simulation camera frames.
- `native_third_wall.mp4`: unannotated original native chase frames.
- `topdown_state_replay_wall.mp4`: offline state-rendered world-fixed overhead.
- `model_decisions.mp4`: exact model JPEG plus prediction, one decision per
  presentation unit, explicitly labelled `DECISION REVIEW / NOT WALL TIME`.
  It may show the post-hoc prediction on its capture frame; do not confuse this
  inspection view with the availability-aware primary film.
- `overview_share.mp4`: readable compact copy; aim below 10,000,000 bytes if
  feasible. Preserve the master. If that size would make labels unreadable,
  retain a larger share copy and state its size instead of degrading evidence.
- Start, first-turn, native-stop/termination, and final keyframe PNGs.
- `video_metadata.json`: codec, width/height, frame count, PTS duration,
  measured source-time span, unique source frames, output repetitions, gaps,
  SHA-256, and `live_capture`/`state_replay`/`decision_review` labels per file.

Make an ordered `media/ALL_RUNS.md` with actual MP4 links and a compact result
table. An optional local HTML player may synchronize already-produced videos;
it must not become the main deliverable or require an external service.
Stream offline high-resolution renders into the encoder rather than retaining
every intermediate PNG. Preserve the designated keyframes, full state/native
JPEG evidence, renderer settings and commands so each film can be regenerated.

## 3. Capture identity and source preservation

Implement an opt-in capture observer at the existing `Simulation._run` render
point. Inside the existing capture lock, retain capture pose, `data.time`,
monotonic time and a copy of `mjSTATE_INTEGRATION` state. Associate them with the
same original `stamp_ns` and the original front/third JPEG bytes after encoding.
Capture-time camera extrinsics/intrinsics must refer to that state, not a later
health snapshot. Do not replace the original stamp or change when frames are
offered to the policy.

Use a bounded nonblocking writer queue, a monotonically increasing integer
frame ID, exclusive creation, full SHA-256 and an explicit per-frame index.
Queue overflow, writer failure, duplicate file names or malformed rows are
recording failures. Preserve the run and stop it through the harness with a
recorded cause; never stall the controller waiting for disk or silently drop data.
Do not re-encode model JPEGs or modify frames before inference.

For a successful capture, prove:

```
captured pair count == index rows == front files == third-person files == saved states
duplicate filenames == queue drops == unreported write failures == 0
```

Record:

| Trace | Minimum fields |
| --- | --- |
| Frame | run UUID, frame ID, original stamp_ns, capture monotonic ns, simulation time, capture pose, state index/signature, front/third file hashes, camera geometry |
| Request | run/session/connection ID, seq, frame stamp, JPEG SHA-256, verbatim instruction hash, send monotonic ns |
| Response | matching ID/seq, receive monotonic ns, raw wire response, model-record path, decode status |
| Consumption | response ID, capture pose used by MPC, consume time, `applied_to_mpc`, `native_stop_consumed`, or `discarded_after_stop`; no invented consumption event |
| Control | timestamp, requested MPC command, applied/clamped command, watchdog-zero events, measured state velocity and control owner |
| Lifecycle | reset, instruction send/accept, connection/reconnection, native STOP, harness stop, timeout, error, post-stop check and cleanup |

The model wire format stays unchanged. Join the sidecar trace to official
`actions.json[l]` using connection/seq plus the exact JPEG hash. Same-looking
frames and nearby timestamps are not sufficient join keys. Preserve all
post-stop model responses and label whether they were discarded.

## 4. Offline rendering and geometry

Use `mj_getState`/`mj_setState` with the stored signature and shape; restore state
and call `mj_forward` only. Never integrate commands to invent intermediate
positions. Use held recorded states for presentation frames between captures,
and record the resulting sample age. Work in a separate render-only model and
never feed the overhead view or ground-truth coordinates to LightNav/MPC.

The checked starting preset is in `research/static_probe_02/result.json`:
orthographic look-at `(8.8,11.5,0)`, elevation -90 degrees, azimuth 90 degrees,
distance 12 m, 7 m vertical span, 1024x768 rendering. Set both the requested
camera and `model.vis.global_.orthographic`, then inspect the actual GL camera
flag and frustum. The first probe showed that checking only the requested
camera field can silently leave perspective projection active.

Only the ten named ceiling geoms listed in that result may be hidden, and only
in the separate overhead render. Keep robot, target, distractor, walls, furniture
and obstacles. Log the view-only change. A run that leaves the preset bounds
gets a larger fixed full-trajectory view for that entire run; no unrecorded pan,
perspective warp or clipping of an inconvenient trajectory. Use a common fixed
view covering all runs for cross-run comparison.

Predictions are robot-local `[forward,left,yaw]`. Convert their XY positions
using the **capture** pose before drawing them on the world map:

```
x_world = x_capture + cos(yaw_capture)*forward - sin(yaw_capture)*left
y_world = y_capture + sin(yaw_capture)*forward + cos(yaw_capture)*left
```

For native-camera ground overlays use the compiled camera transform, including
its forward offset, height, orientation and vertical FOV; reject points behind
the camera. Ground-plane Z is a declared display assumption. The official
`--forward-offset 0` overlay is useful as a comparison, but its simplified
pinhole model is not a substitute for the compiled extrinsics. Never use the
automatic shifted ribbon as metric evidence. Preserve a no-overlay JPEG.

Check known left/right points and target-body projections. For overhead use
the effective mono camera projection (or zero IPD on the separate renderer),
not one stereo eye's matrix by accident. Save the matrices and scale.

For object-point analysis, an optional offline native-view segmentation render
can identify whether OPOS lies on visible trashcan/dog-bed geometry. Verify
state-to-native-view alignment first; restore ceiling visibility for this pass.
List body/descendant geom IDs and out-of-view/occluded/uncertain cases. A pixel
landing on an object supports an observed pointing association, not a unique
explanation of the model's internal reasoning.

## 5. Stops, arrival and honest comparison

Use separate result fields:

1. Was a native model STOP actually consumed by the demo?
2. Did commanded and observed motion remain near zero afterwards?
3. Where did the robot stop relative to the requested trashcan and dog bed?

For the new stillness check, start the window at the first qualifying sample
within 0.2 s after native STOP. Require at least 2.0 s in both monotonic and
simulation time; adjacent samples must be no more than 0.15 s apart. Across
the window require absolute commanded/observed linear and yaw rates <=0.01
in m/s and rad/s, planar pose drift <=0.01 m and yaw drift <=0.01 rad. Report
all measurements even if the check fails; a timeout or harness stop cannot
become a native model stop. This is sampled stillness evidence.

Report planar distance to the selected target root and dog-bed root at every
native stop. Show diagnostic radius memberships at 1.0/1.5/2.0 m; do not pick a
radius after seeing outcomes or call these official benchmark success rates.
Give a visual arrival assessment (`at_requested_object`, `short_stop`,
`other_object`, `unclear`) with terminal frames and geometry. A correct STOP
mechanism at the wrong location remains a navigation failure.

## 6. Legacy runs and media QA

Keep original rep_01..03 and their original videos immutable. Create any new
legacy derivatives under `media/legacy_rep_0*/`. Missing historical frames must
stay visible as gaps/stale-frame labels. Do not reconstruct missing RGB from a
new run. No exact-state overhead replay can be claimed where state was not saved;
use a clearly labelled XY trajectory diagram instead. Report legacy and new
repetitions as separate cohorts.

Every delivered MP4 must fully decode with ffmpeg. Check PTS duration against
its declared time basis; the primary film's measured segment must match the
source monotonic duration within one 20 fps frame (plus explicitly identified
editorial holds). Inspect start, first-turn, mid-run, stop and final frames, then
watch each primary film. Check readable labels, preserved aspect ratios, no
clipped robot/target, no future path leakage, and no model points attached to
the wrong image. A player opening or a valid codec alone is insufficient.
