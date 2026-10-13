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

Historical failure: an executor round returned the whole request directory with `rsync -a`, which overwrote every file at the same path, including
lead-owned files edited after dispatch (round 5 lost a threshold change and a package section this way). Rules:
- While a round is in flight, the lead does not edit files under the request directory that the executor will return; queue the
  edits and apply them after the return is verified.
- The return instruction excludes lead-owned files (`review/`, `RESULT.md`, `OPUS_EXECUTION_PACKAGE.md`, `request.json`) from the
  rsync back, or the package states explicitly which files the executor may write.
- Preflight bounds that were guessed before any measurement are labelled provisional in `conditions.json`; when a measurement
  exceeds one, record the measurement beside the new bound rather than editing the number silently.
- A per-frame preprocessing plugin (task sensor) must be proven in the executor preflight by a bit-identical offline recompute and
  by a "differs from the raw sensor" check before any run is accepted; the two checks together show the override is in effect.

## Repeated fix series and stop evidence (added 2026-09-17, SCAN fix qualification)

Learned from `.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/scan_fix_qualification/` (`RESULT.md`,
`isaac_series/e03_failure_analysis.md`).

- **Show that the series reached the failure condition.** A passing repeated series says nothing about a
  position-dependent fix unless its episodes hit the failing region. Replay every recorded stop pose offline with the
  original and the fixed build (`make_fixtures.py from-journals` → `suite_worker.py --fixtures ...` →
  `analyze_suite.py`). Each replay carries its own validity control (AC0: the original build must reproduce the
  recorded rejection). Report "original rejects at k of N stops" beside the pass count.
- **Judge dwell from full-rate records, not a polled snapshot.** The backend's `StopEvidenceWindow` reads a single
  overwritten `current_command.json` in a 0.02 s loop and can miss samples. `review_two_goal.py` walks every 0.02 s
  `metrics.jsonl` row and is the acceptance authority. A single out-of-limit sample (0.1595 against 0.15 rad/s)
  failed the check that the backend had passed.
- **Stillness failures after a stop belong to the locomotion layer first.** Before 2026-09-18 the V12 runner kept the
  RL policy running on a zero command, with no PD stance hold. Its zero-command yaw noise is already close to the
  0.15 rad/s limit (see the `machine-dog` flat stand-still diagnosis). Check that before blaming the planner, and never
  relax the threshold to hide it. The stance hold added since does not move this margin in the two-goal pilot; see the
  next section.
- **Remote-only bulk needs a returned record and a narrow rule.** Bulk files left on the execution host
  (`clouds.jsonl`, `third_person_master.mp4`) come back as `remote_only_artifacts.json`: path, bytes, remote SHA-256,
  manifest SHA-256 and `all_match`. The review accepts exactly those paths as absent, and only when all three hashes
  agree. Any other missing, changed or unexpected file still fails `returned_hashes_match`
  (`p2b_execution/test_review_two_goal_remote_only.py`).
  As of 2026-10-01, `AGENTS.md` makes gpu5070ti the default home for heavy data.
  New execution plans return only explicitly listed compact evidence and review
  videos, with remote paths/hashes and retrieval instructions for retained bulk.
  Run full-data checks on that host and return their results. This does not change
  any frozen reviewer's missing-file behavior or imply its local return gate
  passed. See [Newton artifact retention](./newton-artifact-retention.md).
- **Keep the executed copy of an untracked driver before editing it.** If a series driver changes after it ran, save
  the executed bytes with their hash (`isaac_series/run_isaac_series.executed_6fca2efd.py`) and name them in the
  result.
- **A series driver writes a ledger line for every outcome.** Pass, review failure, launcher error or timeout,
  review error and host-not-idle all get a line, and a non-passing line records the host state after the failure. The
  idle probe fails closed (`set -e`; no GPU row means not idle). The driver pauses on any non-pass; applying the stop
  rule is the lead's job.

| Condition | Required outcome |
|---|---|
| Series passes, but no stop pose was replayed natively | No claim that the series exercised the fix |
| Backend reports arrival, full-rate dwell < required | Count the episode as failed; report the sampling gap |
| Remote-only record hash ≠ manifest hash, or an extra path is missing | `returned_hashes_match` false |
| Host probe command fails or reports no GPU | Host not idle; do not launch |

## Stance hold, post-result amendments and interrupted series (added 2026-09-18)

Learned from `.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/stance_hold_qualification/RESULT.md` (task
`09-17-isaac-runner-stance-hold`).

- **A hold that enters after the review window does not change the stop check.** The two-goal review judges the
  1.0 s before each terminal, which falls 0.10–1.40 s after the zero command. At that time V12 still drives
  (STAND_SETTLING) and the PD hold waits for its gates. All 24 still-window peaks were in STAND_SETTLING (median
  0.120 rad/s with the hold, 0.121 without). Before crediting a controller change for a stop-dwell pass, locate each
  window peak in the controller's mode timeline (`series_report.py` → `still_windows`, `zero_command_intervals`).
- **Give every post-switch window an end condition before results.** AC7's fixed 1.0 s window after a hold entry
  also scored a planner restart 0.18 s later (episode 6: entry calm at 0.063 rad/s, restart peak 0.174). Define what
  ends a window (for example a mode change or a new command) when the criterion is frozen, not after a failure.
- **Post-result amendments are recorded, never silent.** An acceptance rule may change after results only on Dr
  Sun's explicit instruction, and then:
  - the frozen thresholds file carries the rule as data (`ac7_entry.end_at_restart: true`, `restart` definition)
    plus an `amendment` record: `date`, `by`, verbatim `quote`, `post_result: true`, `trigger` (run, step, value),
    and `previous_sha256`;
  - the previous file is archived byte for byte in `stance_hold_thresholds_history/`; the analyzer pins the new SHA
    (`FROZEN_THRESHOLDS_SHA256`) and lists the old one in `SUPERSEDED_THRESHOLDS`, and loading an older file
    reproduces the old rule;
  - the analyzer returns the amended `verdict` and `as_frozen_before_results` side by side, and other criteria that
    reuse the window (AC8 b, the D5 selection) keep the frozen window unless the instruction names them;
  - every report shows both verdicts, labels the amended one post-result, and does not promote the evidence label
    to `validated`.
- **Recover a finished episode; never re-run it.** If the local series driver dies after the remote worker has
  written its final `result.json`, the episode happened. Re-running it would drop a finished outcome.
  `recover_interrupted_episode.py` handles this case:
  - it checks the prepared package hashes;
  - it requires `last_result_write_phase == "final"`, refuses a run that is already collected, and treats a remote
    `passed` other than true as `execute_failed`;
  - it runs the launcher's own `collect_remote_only`, writes `return_verdict.json` with a `recovered_collect` record,
    and appends a ledger line marked `recovered_after_driver_interrupt`.
  Keep the executed script bytes if it is edited afterwards.
- **Run long series drivers detached.** A background task started from a Claude session dies with the session.
  Start drivers with `nohup … &` and follow the ledger or log with a monitor.
- **Changing a launcher default keeps old evidence reproducible.**
  - Leave the runner's own default (and its hashed bytes) unchanged.
  - Read a prepared package that lacks the field with its legacy meaning (`stance_hold` → `off`,
    `stance_entry_kd` → `ramp`).
  - Pin every caller that reproduces older conditions (`run_isaac_series.py`, `pointcloud_display/run_probe.py`
    pass `--stance-hold off`).
  - Add a reproduction note to the older result (`P2B_RESULT.md`).
  - Derive dependent defaults from the new default instead of fixing them (`--stance-entry-kd` resolves to
    `xfade1s` with the hold on and `ramp` with it off).

| Condition | Required outcome |
|---|---|
| Rule changed after results without an `amendment` record or archived previous file | Refuse; the analyzer only accepts the pinned SHA |
| Amended criterion reported without its as-frozen verdict | Report incomplete |
| Local driver died, remote result final | Collect and review with the launcher's steps; mark the ledger line; no physics rerun |
| Local driver died, remote result not final | Do not recover; report the episode as interrupted |
| Remote result final but `passed` not true | Ledger `execute_failed`, even if the review passes |
| Launcher default changed | Old packages keep their recorded meaning; reproducing callers pinned explicitly |

## Host outage evidence and partial cohorts (2026-10-12)

### Scope / trigger

Use when SSH loss or a manual reboot interrupts a remote Newton series. The
manual recovery action cannot establish the earlier fault's cause. The concrete
examples are the full-route repeat and gpu5070ti-freeze audits dated 2026-10-12.

### Signatures

- `collect_incident.py --output /data/sun/vla_mppi_20261009/results/freeze_20261012_retry02`
- `summarize.py --observed-only [--batch-root <declared cohort root>]`

These are audit commands, not simulator entry points or permanent services.

### Contracts

Bind historical journal queries to the exact incident boot ID, and convert
monotonic records with realtime/monotonic pairs from that boot. Record timestamp
duplicates and backward steps; repeated polls of the same backend snapshot need
not advance its timestamp. RAM available is distinct from free RAM, and sparse
sampling cannot disprove an unobserved peak. Later resource monitoring belongs
to its own interval. Return raw source hashes and a bounded compact manifest.

Observed-only aggregation preserves original progress, request and runner bytes.
It requires a dead original batch (boot reconciliation or absent runner) and a
nonempty closed prefix of the declared tags. Validate each closed raw inventory,
archive, start/goal, native identity, copyback and stop proof. Keep partial and
unstarted trials outside the closed count and report requested count separately.

### Validation and error matrix

| Condition | Required handling |
|---|---|
| Different boot or unstable journal clock offset | Refuse clock alignment |
| Empty journal grep, exit1 and no stderr | Record no match with original exit code; require other same-boot records as a positive control |
| Query timeout/error or unavailable journal | Report missing evidence, not no fault |
| Raw FINISHED result without copyback/retention | Preserve partial arrival; do not qualify or fabricate closeout |
| Other GPU tasks detected by admission | Pause before next run; preserve prior failures |
| Observed-only count less than requested count | Keep batch incomplete and acceptance false |

### Good / base / bad cases

Good: distinguish continuously recorded backend computation from an inaccessible
SSH entry. Base: report sparse memory samples and unresolved cause. Bad: infer
OOM from a user reboot, attribute old GPU errors to a new incident, or call a
resource-paused two-trial prefix a completed six-trial cohort.

### Required checks

The actual recorded incident must produce matching clock endpoints/gaps and
preserve duplicated snapshots. Current source/native hashes must match the
cohort's original identities. Every returned file must match its remote manifest;
all navigation failures and interruption state must survive aggregation.

### Wrong versus correct

Wrong: "Reboot restored access, therefore RAM exhaustion caused a host freeze."
Correct: report the observed access loss, prior computation and resource window,
the manual recovery operation, and which causal evidence remains unavailable.

## Native stop causes and physical holding (2026-10-12 v177 audit)

### Scope and signatures

Use for stop/recovery diagnosis after complete episodes. The reference is
`audits/2026-10-12_v177_stop_causes/` under the Newton experiment:
`inspect_stops.py --output PATH`, `inspect_windows.py --first PATH --output PATH`,
`audit_drift.py`, and `make_report.py`. These read closed captures, not physics.

### Contracts

- Match native revocation, first cancellation and replacement by generation and
  reason. Count control revocations separately from measured low-speed intervals
  and terminal holds. A repeated FSM emergency transition is not a distinct stop.
- A rejection label may conflate geometry and age. Use actual proof/source
  stamps and the native predicate. New data at a separate observer does not
  prove the controller's map consumed or published it.
- Do not use the last timer safety message as the controller's latest map: its
  independent validation may continue while the timer stops publishing.
- Audit `effective_command`, `stance_mode`, `stance_reason` and actual body pose.
  Zero desired velocity and a passed short stillness window do not establish
  sustained spatial holding. Retain observed drift, even in an arrival pass.
- Reconstruct spline control points as production3xN, notNx3. Reject malformed
  diagnostics before evaluating a point. Preserve failed probe evidence without
  relabelling it a production crash.

### Validation and error matrix

| Evidence | Permitted conclusion |
|---|---|
| Source age exceeds250ms; newer cloud seen by observer | Sufficient age-gate violation; internal delay attribution remains open |
| Native ordered replay matches rejection phase/sample count | Reproduced predicate on recorded inputs, not exact asynchronous episode |
| Zero effective command but STAND_SETTLING and body displacement | Holding failure remains open regardless of terminal arrival |
| Timer proof older than live independent checks | Do not reconstruct the controller map from that timer proof |
| Probe malformed/aborted | Diagnostic failure; preserve and repair the probe |

### Good/base/bad and required checks

Good:35matched revocations,30intermediate retries,5terminal stops,33low-speed
intervals and the0.957mzero-command drift reported separately. Base:explicitly
label a controlled fresh-prefix geometry replay. Bad:infer30Hz, smooth recovery
or a stable stop from5/5arrival. Assert source hashes, one-to-one event matching,
native replay status/sample counts, and the actual effective-command timeline.

Wrong:all `scan_safety_evidence_stale` events are data timeouts.
Correct:the current controller also emits that label for `!proof->clear`; inspect
the native geometry result and source age independently.

## Policy-only move / stop / restart evidence (v179)

### Scope / trigger

Separate locomotion stopping from navigation failures using the current pinned
policy, without treating a zero command as a stationary body.

### Signatures

`versions/v179/run_probe.py --terrain {flat,stairs} --attempt 1..6`, under
`supervise.py --run-id ID --deadline 600 -- ...`, uses
`V179_TEMP_ROOT=/private/tmp/vla_policy_stop_20261012` and `NEWTON_RUN_DIR`.
`analyze.py --runs PATH --output PATH` reads closed captures.

### Contracts

Keep the existing factory startup and smooth REJOIN. Detach automatic stance
only after RL owns the joints during the first nonzero command; keep its contact
observer read-only. Each stopped sample must have actual effective command zero,
`stance_mode=POLICY_ONLY`, unchanged20/0.5gains, and target equal to policy target.
Record command-application start pose/time separately from the post-step pose.
No pose/history reset within a trial. Preserve partial startup/fall captures.

The5cm late-excursion flag is a declared diagnostic criterion, not robot safety
qualification. Separate first2s braking from subsequent drift and distinguish
maximum excursion from final displacement. Label a stair approach stop as such;
scene name alone does not establish support on different treads. A complete
script establishes restart execution, not standing or navigation acceptance.

### Validation and error matrix

| Condition | Required result |
|---|---|
| Any stop sample has hold ownership or nonzero effective command | Reject policy-only analysis |
| Fewer than500samples in a requested10s stop | Partial, never a completed stop |
| Golden input, source, geometry or gain mismatch | Refuse execution/claim |
| Remote resource gate held | Retain hold; use only an already-authorized local exception |
| Stop drift also occurs without navigation | Locomotion/deployment/physics limitation; training-only cause unproved |
| Mac framebuffer larger than declared output | Resize before drawing captions; verify actual output dimensions |

### Good / base / bad cases

Good:v179records12conditions/24stops, all policy-only, with braking separated.
Base:the first slow stair-scene stop is still on the flat approach. Bad:call all
24windows independent trials or claim that forcibly freezing the joints fixes
an RL limitation. v180's Retina caption layout is retained as failed visual QA;
v181normalizes the frame before annotation.

### Required tests

Schedule tests require two500-step zero windows and a continuous counter.
Analysis tests reject hold contamination and partial-window completion, and
distinguish a2s braking fixture from later drift. Render tests reject time
reversal/nonzero start and forbid future-state selection. Validate original raw
archive members remotely, then full MP4 decoding and source-frame identities.

### Wrong versus correct

Wrong:zero-command drift proves the neural network's training is the sole cause.
Correct:record the current model/runtime/physics contract and qualify the
observed behavior; original training and other simulators remain separate tests.

Before selecting diagnostic speeds, read both the checkpoint-bound training
command generator/configuration and `newton-minimum-cruise.md`. Label commands
below the project operating cruise as low-speed controls; include the intended
operating range before making a general stopping claim. Report planned,
commanded, effective and measured speed separately. A training sampler's dynamic
per-axis gap is not a fixed scalar stability threshold, and the planned cruise
floor does not apply to braking or zero-command holds. Changing speed on stairs
also changes stopping support geometry; disclose this confound.

For a historical v177 speed audit, verify the actual term-major ONNX command
history (input[60:90], newest[87:90]) against observation[6:9] and effective
command before interpreting thresholds. Separate horizontal norm from yaw;
true-zero holds are not low-speed walking violations. Measure continuous time,
exclude telemetry gaps, and distinguish finite boundary ramps from prolonged
endpoint correction using curve identity and the actual error-feedback law.
Do not shade an entire mixed deceleration/endpoint interval as abnormal: mark
the endpoint subinterval. Deduplicate shared zero episodes across repeated
cancel events. A repeated stance-reason string is not a repeated transition.
An earlier low command and later zero drift are association, not proof that a
speed-floor change would fix the same physical stop state.
