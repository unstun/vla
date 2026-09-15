# Execution design

- Stage: experiment and analysis. Parent local commit: `4aa2890` with pre-existing
  unrelated modifications retained.
- Local evidence/package root:
  `.pipeline/experiments/2026-09-08_tic_vla_dynanav_5070ti/`.
- Remote execution root:
  `/home/sun/vla_exec/2026-09-08_tic_vla_dynanav_5070ti/`.
- Upstream: `references/upstream/2026-08-20_tic_vla/source/TIC-VLA`, clean commit
  `9fa6f8b66b9e121d5df5df071297bba8e5353ebb`, UCLA Academic Software License.
- Model identities: existing TIC-VLA manifest; InternVL3-1B revision
  `4415a3b810e636d11dfa86b0e9ba40bb00535aa8`; checkpoint SHA-256
  `376263f89fad0f42c267d85655019232edc91d36e214e23424804dd4cd42e036`.
- Input: simulated RGB history, instruction and simulator body state. Preserve
  official frame/timestamp semantics and log wall time separately.
- Output: `(1,30,2)` waypoint array consumed by the upstream Nova Carter behavior
  and differential-drive controller. No external robot/network command path.
- Reuse an existing compatible Isaac runtime. Add missing Python dependencies in
  task-owned overlay/venv; do not replace global CUDA, drivers or the simulator.
- The first episode is the official hospital example (seed 36, 20 people,
  70 simulated seconds, 1.5 m success threshold). Removing the other three
  episodes is the declared scope reduction.
- Runtime compatibility and observation-only instrumentation changes are kept as
  local patches/scripts with identities. Preserve navigation decisions unless a
  concrete upstream defect prevents execution; record each necessary correction.
- Run the simulator with a 20-minute wall deadline and monitor resources; retain
  failed attempts. No more than three full episode attempts without new direction.
- Use actual rendered images for video. Preserve simulator result metrics and
  distinguish simulation duration from wall-clock throughput.
- Sync gate: exact source/config/script manifest matches before execution; logs,
  output JSON, video and checksum inventories match after sync back. Downloaded
  dependencies/assets retain URL, revision, hash and storage provenance.
- Rollback: stop only this task's recorded process group; keep environments,
  patches and evidence for review. Do not remove or alter other project work.

The optional compute-helper CLI is absent from the current project/environment;
use explicit SSH and rsync with these same sync gates instead.

## Interactive extension

- Isolate additions under the experiment's `demo/`; copy the 44 tested source
  files into `demo/work/` and emit a separate compatibility patch and manifest.
- A loopback HTTP bridge in the simulator receives versioned goal/stop/resume
  commands. Only the simulation thread touches Isaac objects and model state.
  Start held; stop overrides wheel commands at the next control tick, including
  commands received during inference. Stop remains latched until explicit resume.
- On a new goal or resume, zero commands, clear trajectory/history and reset the
  upstream semantic cache before admitting new model output. Stop does not wait
  for speech or semantic generation. This is simulation-only control.
- Project the model's body/FLU waypoints through its captured robot pose into
  world coordinates and the third-person camera. Composite colored lines on a
  copy of the RGB frame; model-facing pixels remain untouched. Retain projection
  matrices and trajectory timestamps. Drawing is an overlay, not occlusion-aware.
- Local Python HTTP server on 127.0.0.1:18765 serves the Chinese interface and
  CPU SenseVoice via sherpa-onnx; remote loopback port 18766 is SSH-forwarded.
  Browser MediaRecorder uploads a bounded clip; ffmpeg converts it to mono 16 kHz
  PCM. No audio leaves this Mac. Raw microphone clips are not retained.
- One command parser owns Chinese/English demo vocabulary; uncertain/unsupported
  input fails visibly without motion. A single spoken command auto-submits once
  recognized; text input remains available. Each command has one ID and an ack.
- User-triggered simulator starts and validation attempts have a 600-second wall
  deadline. The existing scene, crowd and success threshold remain unchanged;
  camera render products use 960x540 for this interactive variant. Completion
  remains the evaluator's distance stop, not a learned stop claim.
- Verify model files with pinned revision and hashes before ASR load. Pin package
  version, preserve model license/provenance, and use path-specific ignores for
  environment/model/work bytes. All scripts/UI/config stay local source of truth.
- Test audio -> ASR -> command -> simulator and stop/resume using identified
  synthetic Mandarin clips. Browser microphone permission and real human speech
  are a separate manual gate. Preserve actual wall timestamps in demo videos.

## Offline delivery replaces the online interface

Use `demo/录音并生成视频.command` to record six seconds on the Mac, recognize
locally, map the supported goal and dispatch a detached bounded run via SSH.
`--audio PATH` exercises the identical path with an existing audio file.
Offline mode opens no HTTP listener and sends no live images. Poll only compact
run completion metadata, recover interrupted transfers, verify video hashes and
open the local MP4 after completion. Preserve the prior online run separately.

## Top-down recording

Add `--view top_down` to the local/batch/remote command chain; default remains
`third_person`. In top-down mode, replace only the output camera with a fixed
orthographic USD camera at world `(4, 0.5, 8)` pointing along `-Z`. Its 20 m by
11.25 m footprint covers the start and vending-machine goal. A 5.6 m near clip
removes ceiling obstruction from this output view without changing scene geometry
or the front-camera observation. Record at 1280x720 and keep matrix/view metadata.
This is a new simulator run, not a reconstructed view of the prior episode.

## Verbatim language input

`voice_to_video.py --instruction TEXT` bypasses recording/ASR for a direct text
test; recognized speech follows the same verbatim path. A bounded UTF-8 JSON
request is copied to the remote request directory, never interpolated into shell
code. Offline runs require this request. The runner creates a per-run copy of
the hospital YAML with exactly that instruction, exports the same text to the
behavior, and records request/config hashes. Audit every model invocation's
instruction. Preserve the English system prompt and all non-language settings.

## Matched pair execution

Allow the literal full Chinese command through existing goal validation without
translation. Add an optional `inference_seed` to the UTF-8 request and reset
Python/NumPy/Torch RNGs after the initial offline model cache reset, before the
first prediction. Use seed 36 in both fresh processes; do not change the upstream
sampling configuration or claim fully deterministic asynchronous rendering.
Execute the Chinese and English runs sequentially on the same GPU/source manifest.
Store the declared pair before launch and retain both results regardless of outcome.

## Frozen-input diagnosis

Isolate the harness in `demo/frozen_replay_2026-09-08/`. Use the two archived
frame-120 JPEGs and frame-120 robot-state JSONs. The first-call history contains
one image, prior-waypoint text is copied from stdout, and delay is zero. Run the
unmodified `predict_async` first-call path after cache reset and seed reset.
Predeclare seeds 36, 37, 38 and a reversed-order seed-36 repeat for each image.
Capture exact action-head arguments with a read-only forward pre-hook; hash
current features, scalar state and the cache. Replay both language caches with
the same current features/state and compare to their original outputs. This
intervention locates an interface effect, not a unique VLM or action-head defect.
Extract the controller's AST statement slice from the verified source and check
its first-command parity against both recorded stdout values before interpretation.
No Isaac process or motion is needed. A 300-second subprocess deadline bounds the
probe. Verify all 65 existing source hashes, model/checkpoint identities, fixture
and harness hashes before inference; retrieve and hash all resulting artifacts.

## Metric-distance stop probe

Create `distance_stop_2026-09-08/` beside `demo/`, starting from its verified
65-file snapshot. The original demo and frozen-replay inputs stay unchanged.
Use one verbatim Chinese 3 m instruction, seed 36, the same hospital/start/crowd
and overhead camera. The diagnostic goal is the initial-heading point 3 m away;
its numeric coordinates are evaluation-only and never fed into the policy.
Disable benchmark goal termination and disable automatic stuck/back-up recovery
in this isolated probe, since both would confound voluntary stopping. Retain
the existing action head, pure-pursuit controller, slew limits and startup gate.
Use 34 frame-derived episode seconds (about 30 after frame-120 startup), plus
the existing 600-second process deadline. Do not terminate early on 3 m arrival.
Record real timeline timestamps separately from frame and wall clocks.

Anchor measurements to the pose when the instruction is applied. Record forward
displacement along the initial heading, cross-track displacement, cumulative
planar path, actual body speed/yaw, desired and applied commands, and recovery
flags. A provisional stopped-at-target event requires forward 3 +/- 0.25 m,
cross-track within 0.25 m, actual and desired planar/linear speed below 0.05 m/s,
actual and desired yaw rate below 0.10 rad/s, and a continuous two-second
timeline window without holds or recovery. Report later departure and collision
separately; stationary far from 3 m or hitting an obstacle is not success.
Output-only overlays show target and measurements. Verify source/model identities
before execution and local artifacts/video after download.

The first metric attempt crashed with child SIGSEGV at frame 927, coincident
with a periodic 90-second traceback dump. A controlled retry removed that
diagnostic dump only and completed 1020 frames. Preserve both source manifests
and both outcomes; no unique native-crash cause is claimed. Actual recorded
timeline after the instruction was 15 s for 900 benchmark frames, so stop
duration uses timeline time. The parent zero exit and packaging success are
not sufficient completion gates; the analyzer rejects missing child results.

## Matched metric-language pair

Create `distance_language_pair_2026-09-08/` from the verified dump-free metric
probe manifest `cd3d13f7b90114b9ad211f7a97a86a00ab5906c32c6acc575264f38087e8eda2`.
Extend only the allowed instruction set and output caption/analysis routing;
preserve model, behavior, disabled external goal stop/backup, clocks and controls.
Run Chinese then English sequentially, each with a fresh process, seed 36 and
34 frame-derived seconds (expected 15 timeline seconds after instruction).
Keep both original wall-timestamp videos. The side-by-side comparison aligns
recorded simulator timeline after command application; label that playback time
basis explicitly. Retain all attempts, check actual input audits and matching
non-language configs, and do not infer bitwise-identical rendered scenes from
equal seeds. Inspect initial RGB and capture its identity as a comparison limit.
