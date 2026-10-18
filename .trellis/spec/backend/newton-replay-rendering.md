# Newton recorded-state rendering

## 1. Scope

The2026-09-26 local stair experiment's `scripts/render_episode.py`. Display
corrections reuse immutable recorded body/joint states and native curves; they
do not execute another physics or sensing episode.

For new renders use the v51 streaming renderer through `scripts/run_managed.py`;
the original script and frozen versions remain historical references. See
[artifact retention](./newton-artifact-retention.md) for MP4 verification,
three-frame previews, raw-log archives and restoration. Do not retain full PNG
sequences by default or duplicate a run merely to prepare its video inputs.

## 2. Signatures

`render_episode.py --source-run RUN_ID [--limit N] [--view original|rear-right]` via `run_bounded.py` with a
new output run ID. `prepare_appearance(robot, human, out)` reads source USD;
`viewer_color(linear_rgb)` adapts linear USD color for the pinned GL shader.

## 3. Contracts

- Resolve each human mesh's bound material with `UsdShade.MaterialBindingAPI`
  and its `mdl` surface shader. Preserve the original albedo atlas and UVs.
- OmniPBR `diffuse_tint` multiplies the albedo. Do not merge differently tinted
  meshes into one white instance. Missing authored tint uses OmniPBR's1,1,1
  default. Record every material binding, source tint and texture hash.
- Newton c2ca70be's shader decodes object color with `pow(color,2.2)`.
  Encode authored linear USD tint/color with exponent1/2.2; applying the
  linear values directly would darken them twice.
- Respect inherited `UsdGeom.Imageable.ComputeVisibility()`. Authored
  invisible meshes must not appear in the visual replay.
- Read Building's authored diffuseColor and roughness instead of assigning
  an arbitrary display palette. Viewport illumination is explicitly declared;
  basic GL rendering does not establish RTX/MDL/ORM/normal-map equivalence.
- Preserve physics/sensor files. A display-only visibility fix does not repair
  prior ray-return evidence, which may need separate requalification.
- `--view rear-right` selects a fixed display camera at (-0.7,-1.1,0.7) m,
  looking at (-0.05,0,0.19) m with 45-degree FOV. This is behind/right for the
  factory trial's +X heading. Default `original` retains the previous cameras.
  Record camera position/target per frame and `display_camera_mode=rear_right`.
- The explicit `flat_empty_long` scene uses a 50-degree following camera at
  recorded base + (-1.2,-1.5,0.9) m, looking at base + (0.3,0,-0.05) m.
  Record `display_camera_mode=long_route_follow`. Its metre grid and overview
  are display-only. Label commanded velocity as `command vx`; total spline
  messages include stationary holds and must not be labeled moving curves.

## 4. Validation and errors

Missing bound shader/texture, nonfinite or out-of-range color, or UV/face count
mismatch raises. A video cannot establish corrected simulation evidence if
only its appearance changed. Record the unchanged source-state SHA and zero
render-time physics steps in `result.json`.
Unknown view values are rejected by argument parsing before rendering.

## 5. Cases

The source police-shirt tint is(0.3057325,0,0), and pants tint is approximately
(0.8312102,0.6637954,0.5559049). Four of nine meshes are authored invisible:
hat, radio and two vest parts. A white-clothed, hat-wearing replay violates the
source's appearance even if it uses the correct texture file.
The rear-right factory replay makes FR/HR the near-side legs for shell inspection;
do not rotate the robot state to achieve a camera change.

## 6. Checks

Read authored values directly, validate inverse color conversion against the
pinned shader, compare rendered visible-mesh count with USD, inspect preview
and full-video representative frames, decode the whole MP4, and verify all
source/frame/delivery hashes. Preserve previous videos.
For a camera-only change, inspect zero-return and standing frames from the new
view and validate the actual replay; another physics run is unnecessary.

## 7. Upstream basis

Pinned Newton `viewer.py`, `gl/shaders.py`, `gl/opengl.py` and
`example_basic_viewer.py` match the imported source manifest. NVIDIA's OmniPBR
documentation defines tint multiplication; OpenUSD's Imageable documentation
defines inherited visibility. Links and limitations are in the experiment's
`COLOR_CORRECTION.md`. Do not recolor rendered pixels or invent replacement
textures when the original material already supplies the answer.

## Robot material follow-up

The original Lite3 URDF supplies an explicit color on only one of13 base/leg
visuals. Do not present trimesh's default gray as an authored robot material.
The manufacturer USD at5695b809 explicitly supplies white defaults. The replay
fills missing colors from that pinned material reference by original link and
exact mesh match, retaining the one authored white and all sensor colors.
Require13 unique matches, unchanged nonselected shape colors and zero physics
steps. Do not copy hidden prototype visibility or new upstream geometry into
the recorded robot. Record source license, hash and the display-only scope.

## Mirrored URDF shell orientation

1. **Scope:** recorded robot visuals in `prepare_robot_appearance(robot)`.
   The pinned URDF loader bakes signed scale into vertices without adjusting
   winding/normals. The viewer's instance-scale mirror support does not cover it.
2. **Signature:** the existing function returns `base_visuals[]` with optional
   `display_orientation`: source scale, Trimesh version, winding change,
   invariant flags, and displayed index/normal SHA-256 values.
3. **Contract:** after exact original mesh/link matching, use pinned
   `trimesh.Trimesh.apply_transform` for unit-axis reflections. Create a visual
   copy only. Preserve vertex positions, geometric triangles, UVs, material
   values, shape transforms and all nonselected/collision objects. Keep source
   CAD cavities. No source STL modification or physical/sensor requalification
   follows from this display correction.
4. **Errors:** collision-enabled shape, non-unit scale, changed vertices or
   changed geometric triangles → reject the display adaptation.
5. **Cases:** unit scale → retain original object; one negative axis → reverse
   winding and transform normals; two negative axes → transform normals while
   retaining winding. Current affected links are FR_HIP, HL_HIP, HR_HIP,
   FR_THIGH and HR_THIGH.
6. **Tests:** `scripts/test_robot_rendering.py` checks the actual appearance
   seam against Trimesh and independent signed-volume/normal assertions,
   unchanged collision sources and zero physics steps. Compare identical-state
   replay frames and decode the whole MP4 before delivery.
7. **Wrong versus correct:** multiplying vertices by a negative scale alone
   makes exterior faces disappear under back-face culling. Transform vertices,
   normals and triangle orientation together in the replay visual copy. Do not
   disable culling globally or fabricate replacement shells.

## Mac recorded-state host port (v69, 2026-10-04)

1. **Scope:** display the externally stored v68 Mac recording without physics.
   Reuse frozen v51 streaming/material/timeline code and v61's close camera;
   preserve all native sources and original failure evidence.
2. **Signature:** `V69_TEMP_ROOT=/private/tmp/vla_newton_v69_UNIQUE ABS_PYTHON
   versions/v69/run_review.py --run-id UNIQUE --deadline 900 --retention archive
   -- ABS_PYTHON ABS_RENDER_REVIEW`. Both child paths must be absolute because
   the original supervisor changes cwd to its temporary root.
3. **Contract:** `display_contract.json` pins the physical root/run, analysis
   metrics, original state/archive/geometry hashes and parent manifests. The
   wrapper changes only external source selection, display overlay and camera.
   On Mac, unset global `PYGLET_HEADLESS` and use the native Cocoa context;
   `ViewerGL(headless=True)` still creates an invisible window. Keep the original
   causal wall grid and untimed-startup omission. Read already verified Mac
   metrics instead of comparing Linux event times directly to Mac monotonic.
4. **Errors:** changed input/manifest/snapshot or adaptation-string mismatch
   rejects rendering. Missing Cocoa access prevents viewport creation. Global
   pyglet headless requests unavailable EGL on this Mac. A relative interpreter
   fails before the child starts; retain the failed attempt and retry the same
   frozen source with absolute paths.
5. **Cases:** the same frozen v69 preview/full render passes; its first relative
   interpreter attempt fails before rendering. The physical v68 run remains
   FAILED heartbeat_stale even when the display process/retention succeeds.
6. **Checks:** original timeline3/3 and stream4/4 tests; full MP4 decode/count;
   every causal source index, native/display/camera timestamp; unchanged input
   hashes and zero physics steps; inspect stair, midpoint and final fault frames.
   Keep three representative PNGs, finished review MP4 and compact receipts.
7. **Wrong vs correct:** do not fabricate startup wall times, interpolate poses,
   hide the fault stop, or infer planner30Hz from video30FPS. Render the original
   navigation wall timeline. Its last causal grid frame may precede the last raw
   sample: v69 ends46.486080s versus46.506069s raw, after the visible fault stop;
   record this20ms sampling difference instead of adding synthetic end motion.

## Nav2 local curves and timing report (v116+, 2026-10-09)

The Foxy-owned native worker publishes /quad_0/planning/bspline. The historical
observer's /planning/bspline subscription records zero curves, even when the
robot moves. Qualify the actual DDS topic/type and inspect the captured count;
optimizer seed points are not a substitute for final native spline messages.
Record controller admission, command owner and cancellation alongside the curve.

Display only exact controller-admitted normal curves whose events preceded the
recorded source frame. Join the complete run/epoch/request/goal/route/command/
generation/map identity. Clear cancelled/stopped or stale-owner output and reject
emergency-hold curves. Latest accepted plans may replace an older command between
ticks; do not call a displayed plan the executed physical path. Preserve original
control points/knots and sample the native cubic with the existing BSpline contract.
Thick display markers are allowed at unchanged coordinates; their radius is a
visual property, not robot clearance. Check start/stair/final camera occlusion.

Plot complete native planning-round wall durations, including failed rounds and
spikes. Reconcile every recorded start/result and distinguish normal curves from
emergency holds. Use the original converged cross-host clock mapping and the
video's first timed source state; never substitute30FPS for planner rate. A video
seek after a computation must select a frame whose original observation already
follows completion, not merely a later30FPS display tick. A still newer result
may legitimately be displayed by that next frame. Test the real recorded seeks.

An offline HTML can embed the checked MP4, static scientific SVG plots and timing
data with interactive seeking. Verify embedded video bytes, full decoding, exact
source hashes, causal frame selections and actual browser behavior. Preserve prior
successful and new failed runs separately; a corrected plot is not navigation
acceptance. v116 attempt02 has900 timed rounds,895 normal curves and9 emergency
holds, and endsFAILED. Four selector/spline tests and900 actual seek checks pass.

## Linux/EGL recorded replay (v140, 2026-10-10)

Keep rendering on gpu5070ti. Actual headless EGL context passes with
`PYGLET_HEADLESS=1` and `PYOPENGL_PLATFORM=egl`; use installed Linux fonts and
FFmpeg. Reuse v120's causal controller-admitted overlay and v51 streaming
renderer/camera. The Linux analysis CSV uses `wall_s_host`; bind it to the
original converged clock samples. Construct the exact v40 robot model used by
v139, but advance zero physics steps. Parent/source/capture hashes must match
before and after replay. Do not infer a new experiment from the video.

v139_candidate_attempt08 is the passed fifth fresh comparison trial, with three
protected replacements. v140 displays54.867s/1646frames at30FPS,1349with native
curves. All frame source indices and nonfuture curve events, full video decode,
start/mid/final visual review and returned regular-file SHA pass. Keep raw/master
on/data and return the actual6,555,740-byte MP4, not a symlink or an index.
The first short preview's final active-goal label is a bounded preview result;
use the complete final video, whose terminal frame reports arrived.

### Explicit full-start video request (v141)

When Dr Sun requests the recording from the beginning, include original untimed
startup poses using their simulation timestamps and label that segment startup
sim. Never invent missing startup wall stamps or claim wall1:1for it. Join the
unchanged original wall-timed navigation segment on the display grid. No pose
interpolation; hold the last actual preceding state, preserve global source
indices, and show no future curves/solve timings during startup. Use a close
camera from the first frame so crouch/stand is visible. The v141 actual replay
starts at the earliest recorded pose (native0.08s), not an invented zero pose.
Its137startup source records map to329display frames, followed by1646navigation
frames. Full1975-frame/65.833s video decode and all source/clock/curve/visual checks
pass; earlier v140 remains unchanged. This is a display extension, no new physics.

### Actual native-zero request (v142 recording / v143 display)

The old factory video sampling begins after80integrations, at native0.08s.
If Dr Sun requires actual0.0s, the existing capture cannot provide that state.
Create a new integer recording version and record initialized body/joint arrays
before the first integration. Require both native clock exactly0.0 and step
counter0; compare state hashes before/after the read. Reject already-stepped
states rather than relabeling their time. Delegate the unchanged audited factory
initializer and prepend only the actual new zero-state sample to its video rows.

The display must require the zero-state witness and exact equality with the
first physical sample. Preserve causal held-state startup sampling and original
wall-time navigation, with no pose interpolation or fabricated wall stamps.
Keep prior0.08s videos intact. A new recording of nativev139 remains separate
from its completed six-run acceptance denominator.

### Original spatial start and complete route (v144+)

1. **Scope:** “from the start” in Dr Sun's corrected request means the original
   spatial spawn and complete route to the original goal. A native0.0s corner
   recording does not satisfy it.
2. **Signature:** `versions/v147/run_recording.py --variant candidate --attempt N`
   on gpu5070ti selects `--building-route historical_full` and records one
   uninterrupted physical episode. `verify_full_route.py --run-root ABS_RUN`
   checks the closed capture before a completed-route render.
3. **Contract:** pin `inputs/historical_full_building.json` SHA256, original
   spawn/yaw and upper-floor goal. Verify actual initial body pose; factory
   crouch height is ground+0.14m in the pinnedv40 model. Check original admitted
   goal, strictly increasing native clocks, continuous recorded positions,
   FINISHED arrival, final measured PD hold, no fall and applied-state copyback.
   Preserve startup, pauses, recoveries and final hold in the video. Each failed
   attempt remains separate; never join episodes or shift the spawn to finish.
4. **Errors:** corner profile, different spawn/goal, reset/nonincreasing clock,
   discontinuous pose, failure/no arrival or missing final hold/copyback fails
   the complete-route gate. A verified partial failure video is allowed with
   explicit failed status and cannot be called a complete-route delivery.
5. **Cases:** v144 starts correctly but fails after23.126m; v145 displays the
   whole recorded failure. v142 starts at0.0s in the corner fixture and must be
   rejected by `verify_full_route`, despite its arrived status.
6. **Checks:** execute actual full-profile selection and launcher-argument
   regressions plus rejection of the old arrived corner capture. Validate
   every closed raw/archive identity before rendering, all causal timeline
   indices and nonfuture curve events, complete MP4 decoding, start/mid/final
   visual inspection and returned regular-file hashes.
7. **Wrong versus correct:** resetting the video/native timer or prepending a
   zero-state frame does not restore the omitted route prefix. Select the
   original spatial profile and execute its complete path continuously. One
   completed episode remains separate from repeated-route reliability and
   earlier corner-only acceptance.


## Version-relative source snapshots in the v237 display adapter

1. **Scope:** v237 keeps current files and `source/<name>` snapshots relative
   to its version directory. The older v220 renderer treats the presence of
   `snapshot_locations` as a repository-relative layout; that inference fails
   before rendering (`repo/PLAN.md` missing). Keep the frozen manifest intact.
2. **Signature:** the audit's `verify_manifest(version)` delegates other versions
   to the original v220 checker; v237 resolves current/snapshot paths against
   `BASE/versions/v237` and returns the actual manifest SHA-256.
3. **Contract:** assert `frozen`, `source_identity_sha256`, every `source_files`
   current hash and its matching `snapshot_locations` hash. Preserve the failed
   render root and use `video_v237_render02` for the corrected replay.
4. **Errors:** missing current/snapshot, changed digest or identity mismatch
   rejects rendering. A layout mismatch changes path resolution only; it never
   permits skipping current/snapshot checks or changing the physical manifest.
5. **Cases:** old repository-relative parents still use their original checker;
   the version-relative v237 snapshot passes both current and preserved hashes.
   Treating all snapshots as repository-relative fails the first render.
6. **Checks:** run actual full recorded-state replay and the original causal
   frame/overlay/MP4 checker; assert zero physics and unchanged capture hashes.
   Keep first failed source/logs and the subsequent executed adapter identity.
7. **Wrong/correct:** do not delete `snapshot_locations` to appease an old
   consumer. Adapt the declared layout at the display boundary and verify both
   copies. Evidence:2026-10-17_v237_gpu5070ti_physical/render_run.py.
