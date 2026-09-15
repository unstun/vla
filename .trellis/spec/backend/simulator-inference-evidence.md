# Simulator inference evidence contract

## 1. Scope / Trigger

Use this contract for bounded inference trials of a pinned upstream simulator
before integrating a VLA model into the project's robot stack. It does not
select a navigation baseline or authorize physical actuation.

## 2. Signatures

The concrete reference is
`.pipeline/experiments/2026-09-08_tic_vla_dynanav_5070ti/`:

```bash
python3 scripts/download_assets.py EXPERIMENT_DIR
python3 scripts/probe_model.py
python3 scripts/run_bounded.py
python3 scripts/collect_run.py EXPERIMENT_DIR RUN_ID
```

`probe_model.py` and `run_bounded.py` consume the task-owned environment in
`configs/remote_env.sh`. `run_bounded.py` limits wall time to 1200 seconds and
records its own process group. Other simulator trials must declare their own
deadline and output shape instead of inheriting these defaults.

The local voice-to-video variant lives under the reference experiment's `demo/`:
`voice_to_video.py [--audio PATH] [--synthetic] [--no-open]` records/transcribes on
the Mac, `launch_batch.sh RUN_ID` dispatches a detached run, and
`collect_demo.py RUN_ID` packages the trajectory video. `run_demo.py --offline`
sets `TICVLA_DEMO_OFFLINE=1`, creates no HTTP listener and uses a 600-second wall
deadline. The Chinese `.command` entrypoint waits for Enter before recording.

`--view third_person|top_down` is forwarded through the local launcher, batch
script, worker and remote runner; `TICVLA_DEMO_VIEW` selects only the output
camera. Record the view in request, run metadata, telemetry and analysis.

`voice_to_video.py --instruction TEXT` bypasses microphone/ASR and sends the text
verbatim. Both text and audio paths transfer a bounded UTF-8 JSON request with
`instruction_mode=verbatim`. Offline runs require it, create a per-run scenario
copy and export `TICVLA_DEMO_INSTRUCTION` for the same behavior text.

For paired language trials, `--inference-seed N` adds a validated integer in
`[0,2**32)` to the request. The runner exports `TICVLA_INFERENCE_SEED`, and the
initial offline goal resets Python/NumPy/Torch RNGs after resetting the model
cache. Record the seed and actual reset marker. Do not infer bitwise deterministic
rendering or asynchronous generation from matching RNG seeds.

## 3. Contracts

- Before execution, pin source, model revision, checkpoint SHA-256, input config,
  runtime versions, and every local compatibility patch.
- The TIC-VLA case requires finite `(1,30,2)` trajectories, increasing simulation
  frame identifiers, actual controller commands, and rendered camera evidence.
- Record `meta.json` with `exit_code`, `timed_out`, `wall_seconds`, command and
  process identity; retain raw output and resource samples.
- Keep model-only CUDA allocation separate from sampled total GPU use. The
  reference's model-only probe reserved about 2.62 GiB, while its combined
  simulator trial sampled 15486 MiB of 16303 MiB.
- Video cadence, benchmark-reported time and wall time are distinct fields.
  Frame-count-derived duration is not proof of the simulator's physics clock.
- Runtime warnings must remain visible. A distance-threshold benchmark stop is
  not evidence of a learned stop action.
- For native metric-stop probes, use distance only for measurement and disable
  goal-triggered termination. Automatic stuck recovery can override an intended
  stop and must be separately controlled/reported. Require sustained near-target
  stillness together with low desired/applied commands; collision-induced
  stillness or timeout is not a learned stop. Distinguish forward displacement,
  net displacement and accumulated path. Use actual recorded timeline timestamps
  for hold durations; this probe observed a factor-two difference from frames/30.
- A zero parent exit code can conceal an episode child crash. Reject fallback
  results containing `error=no_result_file`, zero duration or infinite error as
  valid navigation/collision metrics. Partial media may be retained but must be
  labeled incomplete. Check child termination and a real episode result.
- Voice input is a separate ASR frontend. Keep `synthetic_audio`, recognized
  text, audio SHA-256 and the actual model instruction in the local request record.
  Enumerating a microphone is not recording evidence. The offline entrypoint
  accepts the pinned vending-machine goal; it rejects unsupported goals and
  interactive stop/resume commands. No raw audio is uploaded.
- Do not infer a checkpoint's language limits from a demo's command mapper.
  Current goal validation preserves the original text instead of replacing it
  with the old English constant. Every inference audit must match the per-run
  instruction; missing input requests or mismatches fail explicitly.
- Language comparisons must match directional/stop meaning as well as target
  words. Predeclare text/order/config/seed, retain all runs and compare semantic
  scenario objects after removing only instruction. One pair is exploratory,
  not a statistical language effect estimate or an occlusion/distance ablation.
- For frozen-input diagnosis, retain exact RGB bytes, sampled history, scalar
  state, prior-waypoint text, delay and seed. First verify original-output parity
  and identical-input repeats; matching simulation seeds alone is insufficient.
  Record actual action-head input hashes. Cache swaps must hold current features
  and scalar state fixed and report donor-output error. They identify an interface
  effect, not a unique VLM/action-head defect. Generated reasoning text is an
  observed output, not a reliable causal explanation.
- Controller diagnostics must distinguish desired commands from slew-limited
  commands and realized motion. Use the pinned consumer implementation and check
  it against recorded runtime values. Controller-only synthetic trajectory
  controls and first-frame model replays do not validate a closed-loop fix.
- Project waypoints with their captured body pose and the camera matrix. Draw
  annotations only on a copy of the third-person image, retaining raw model RGB.
  Wall-timestamp video and frame-derived simulator duration remain separate.
- A requested new camera view requires actual rendered evidence from that camera.
  The top-down mode uses an orthographic camera, not a perspective transformation
  of the earlier video. Verify a constant view matrix, visible scene/robot/path,
  and unchanged model-camera configuration. Declare ceiling clipping and that
  the footage is a separate run.

## 4. Validation & Error Matrix

| Condition | Required outcome |
|---|---|
| Truncated HTTP range or ignored Range header | Reject the range; preserve the verified prefix |
| Final asset hash mismatch | Do not load the asset |
| Imports/model constructor only | Report environment readiness only |
| Exit 0 without camera/trajectory/controller evidence | Reject the closed-loop claim |
| Finite trajectories and motion, benchmark goal failure | Report loop execution and navigation failure separately |
| Unresolved crowd/texture errors | Limit the result to compatibility evidence; no full benchmark claim |
| Missing local artifact or mismatched hash | Keep the sync gate incomplete |
| Unrecognized/unsupported speech | Show an error and do not launch motion |
| SSH disconnect during a detached batch | Preserve the bounded remote run and retry status/download |
| Missing source nested under `work/ticvla/models/` | Fail the source sync gate before simulator startup |
| Missing verbatim request or model-instruction mismatch | Fail explicitly; no English fallback |

## 5. Good / Base / Bad Cases

- Good: the reference run retained 184 finite trajectories, 184 nonzero model
  command records, two camera sequences, result JSON and matching local hashes.
- Base: a single-image offline forward establishes model compatibility only.
- Bad: an allocated GPU or a static scene at frame zero is presented as navigation.
- Good: a marked synthetic Chinese clip passes the real CPU recognizer and its
  mapped command produces a hashed local simulator video. Report the human
  microphone gate separately.

## 6. Required Checks

- Test truncated response rejection, ignored ranges and safe partial-file resume.
- For parallel acquisition, retain completed disjoint pieces after a failed
  request; assemble in byte order and verify the complete SHA-256.
- Check exact tensor shapes, finiteness, control source and actual pose change.
- Decode delivered videos and inspect representative frames; preserve the raw
  camera bytes or a hashed local archive.
- Verify local/remote artifact equality and absence of task runtime processes.
- Version-specific SDK overrides stay in task-owned patches. Isaac Sim 5.1 can
  re-enable material sync loading after `SimulationApp(sync_loads=False)`;
  inspecting a constructor flag alone is not an adequate regression check.
- `demo/scripts/test_protocol.py` checks unsupported/negated command rejection,
  verbatim Unicode JSON round-trips, absent-request rejection, latched command
  ordering and known body/camera coordinate transforms. The
  batch acceptance additionally requires real speech decoding, valid model
  output, video decoding and verified local raw-frame archive bytes.

## 7. Wrong vs Correct

- Wrong: infer that a 1B model's weight size proves the whole simulator fits.
  Correct: measure the complete episode's GPU/system memory with its actual
  scene, sensors and model resident.
- Wrong: equate a 10 FPS encoded clip with real-time execution.
  Correct: declare the playback time basis and retain wall-clock measurements.
- Wrong: exclude every directory named `models` when syncing a work copy.
  Correct: scope ASR-weight exclusions to root `/models/`, and verify the complete
  source manifest including nested model implementation modules.

Evidence: the reference experiment's `RESULT.md`, `runs/20260908T131741Z/analysis.json`
and `artifact_sha256.json`. Its compatibility workaround is not a global SDK
configuration recommendation.

## Habitat camera-condition preflights (added 2026-09-10)

Learned from the InternVLA-N1 camera ablation
(`.pipeline/experiments/2026-09-08_dualvln_rented4090/public_scenes/requests/2026-09-10_lite3_camera_ablation/`):

- Verify camera geometry from the simulator's own sensor state
  (`sim.get_agent_state().sensor_states[...]`: height above the agent, forward
  offset, pitch of the forward vector), not only from a rendered image.
- Habitat depth is z-depth along the optical axis. A flat floor at a row whose
  ray is theta below the axis reads `h / (sin p + tan theta cos p)`; the ground
  distance `h / tan(p + vfov/2)` holds only for a level camera.
- The agent origin sits on the navmesh, which can be 0.1 to 0.2 m above the
  rendered floor (height-quantized); bound the implied gap, never a raw ratio.
- A zero-amount `look_down` re-normalises the sensor quaternion by 1 to 2 ULP
  and flips about 0.3 percent of edge pixels; a "no-op" check must bound pitch
  delta and changed-pixel fraction, not require bit-identical frames.
- `hfov` is an integer field in habitat-lab 0.2.4 structured configs.
- Matrix runners must gate on the preflight verdict (`all_stages_passed`), not
  on the report file's existence, or a refused launch burns a run id.
- Cap-terminated episodes record one video frame more than traced steps.

### Report oracle success beside success (added 2026-09-10, round 4)

On the two castle episodes, every wide-FOV condition reached the episode-2
goal region (oracle success 5/5) but stopped late (success 0/5 to 2/5).
Reporting only success would have read as "the camera geometry fails
episode 2"; reporting oracle success shows a stop-timing failure shared with
the baseline. Summaries of navigation runs in this project must list both,
plus the median stop error and step count, before any camera or model
conclusion is drawn.

## Lead edits and executor returns must not overlap (added 2026-09-11, round 5)

An executor round returns the whole request directory with `rsync -a`, which overwrites every file at the same path, including
lead-owned files edited after dispatch (round 5 lost a threshold change and a package section this way). Rules:
- While a round is in flight, the lead does not edit files under the request directory that the executor will return; queue the
  edits and apply them after the return is verified.
- The return instruction excludes lead-owned files (`review/`, `RESULT.md`, `OPUS_EXECUTION_PACKAGE.md`, `request.json`) from the
  rsync back, or the package states explicitly which files the executor may write.
- Preflight bounds that were guessed before any measurement are labelled provisional in `conditions.json`; when a measurement
  exceeds one, record the measurement beside the new bound rather than editing the number silently.
- A per-frame preprocessing plugin (task sensor) must be proven in the executor preflight by a bit-identical offline recompute and
  by a "differs from the raw sensor" check before any run is accepted; the two checks together show the override is in effect.
