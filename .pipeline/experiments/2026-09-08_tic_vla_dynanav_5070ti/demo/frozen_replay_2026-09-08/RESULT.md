# Frozen first-call diagnosis

The first anomalous trajectory is reproducible without the simulator. With
identical pixels, scalar state, delay and seed, the Chinese instruction produces
a near-origin trajectory and a strong desired right turn; English produces a
longer forward trajectory and a small desired heading correction. Exchanging
the language-produced semantic cache exchanges the action output exactly.
This identifies an instruction-conditioned model-interface effect and downstream
controller sensitivity. It does not establish a unique neural root cause or
resolve the later closed-loop navigation failure.

## Protocol and provenance

- Approved stage: experiment and analysis; offline diagnosis only.
- Successful execution: `20260908T160120Z`, exit 0, 23.542 seconds, 300-second
  deadline. No simulator, website, training or robot actuation was started.
- Local source of truth: this dated directory and the parent demo source.
  Remote copy: `/home/sun/vla_exec/2026-09-08_tic_vla_dynanav_5070ti/demo/frozen_replay_2026-09-08`.
- Demo source manifest SHA-256:
  `4a940f97a40d7cb513efd044f7df707daf71a13073f303b7395a4f050832c8c0`.
  Existing 65 source files remain unchanged. Pinned upstream commit:
  `9fa6f8b66b9e121d5df5df071297bba8e5353ebb`.
- InternVL3-1B revision `4415a3b810e636d11dfa86b0e9ba40bb00535aa8`;
  TIC checkpoint SHA-256
  `376263f89fad0f42c267d85655019232edc91d36e214e23424804dd4cd42e036`.
  All model assets were checked and the checkpoint loaded strictly.
- The predeclared [plan](plan.json) crosses the two archived frame-120 JPEGs
  with the exact full Chinese and English commands. Each cell has seeds 36,
  37 and 38 plus a reversed-order seed-36 repeat: 16 first-call predictions.
- Each history has one image, matching the original first-call log. The two
  recorded state JSONs are byte-identical; SHA-256:
  `3c83d06d8cafd29869727e809e04e635277b80c1cd9003bd6278793c0b132cef`.
  The actual model state is `[vx, vy, yaw_speed, dx, dy, time_delay]`;
  displacement and delay are zero. Prior-waypoint text is copied from stdout.
- The unmodified `predict_async` path resets its cache and waits for the first
  generation. Read-only hooks retain the real action-head arguments and hash
  delayed pixels, current features, state, token IDs and cache tensors. The
  action expert is in evaluation mode. No deterministic-kernel setting was
  changed; repeatability is measured rather than assumed.
- Eight direct action-head calls exchange Chinese/English caches with current
  image features and state fixed. No cache tensor files are retained; exact
  inputs, code, model identities and hashes allow regeneration.

## Evidence

The original Chinese and English first trajectories are reproduced with **zero
maximum coordinate error**. Both original desired controller commands match
their rounded runtime stdout values within 0.0005. The controller probe compiles
the actual source AST slice, rather than a separately rewritten controller.

| Fixed image | Instruction | Selected lookahead distance | Desired speed | Desired yaw rate |
|---|---|---:|---:|---:|
| Chinese-run first RGB | Chinese | 0.0411 m | 0.0843 m/s | -0.8374 rad/s |
| Same RGB | English | 0.2071 m | 1.5000 m/s | +0.1215 rad/s |
| English-run first RGB | Chinese | 0.0260 m | 0.0267 m/s | -1.0990 rad/s |
| Same RGB | English | 0.2197 m | 1.5000 m/s | -0.0980 rad/s |

Positive yaw is left and negative yaw is right in the controller's FLU
convention. These are **desired commands before slew limiting**. The original
first executed tick has the same limited `v=0.03333, w=-0.05833` in both runs;
do not present the desired values as instantaneous realized robot velocity.

All four identical-input repeat pairs are byte-identical in response, full
cache, image features, scalar state and waypoint tensor. Seeds 37 and 38 also
produce the same results as seed 36 in all four cells. This does not prove
general determinism beyond the tested inputs and narrow sampling settings.

At fixed pixels/state, mean pointwise Chinese-English trajectory separation is
0.0969 m on the Chinese-run image and 0.1111 m on the English-run image.
Changing only the initial image changes some coordinates by up to approximately
0.030 m and changes generated text, but the language-associated trajectory and
command pattern persists on both images.

All eight cache interventions reproduce the donor-language output with **zero
error**. The source action expert reads the last layer's value tensors. This
demonstrates that the observed instruction effect reaches the head through that
interface. It does not distinguish representation quality, generated-text
content, sequence-length effects, or action-head interpretation of that state.

The Chinese generated responses mention a desk/workstation while the English
responses mention the vending machine. These are recorded model outputs and
useful follow-up clues, not a faithful explanation of the model's reasoning or
independent evidence of which object it perceived.

## Controller sensitivity

The source asks for a 1 m arc-length lookahead. These first predicted polylines
are shorter, so its index is clamped to 27. On the Chinese predictions, that
point is only 2.6–4.1 cm from the origin and about 1.2–1.5 cm to the right.
The curvature `2*y/(x*x+y*y)` is therefore large. The controller slows forward
motion and produces a strong right-turn request from this geometry.

Controller-only counterfactuals confirm the calculation: reflecting lateral
coordinates reverses the yaw command with unchanged speed; setting lateral
coordinates to zero yields zero yaw. Doubling all coordinates halves curvature
and roughly doubles speed while yaw stays nearly constant because of curvature
speed limiting. These synthetic controls are not replacement model trajectories
or a proposed navigation fix. Simply scaling the plan is not supported as a
turning fix by this probe.

## Checks and limits

- 97 pre-inference source/package/asset checks passed. All 16 model trajectories
  and eight intervention outputs are finite `(1,30,2)` tensors.
- All 11 successful-run artifacts returned locally and passed SHA-256 checks.
  The first failed harness attempt is retained separately, with six verified
  artifacts; it stopped after its first model call because a NumPy array was
  compared as a scalar Boolean. The fixed pose comparison is covered by all
  16 successful real-model calls. Model/simulator behavior was not changed.
- The successful run uses PyTorch 2.7.0+cu128 and Transformers 4.57.6. Peak
  PyTorch allocation/reservation was 2015.8/2144.0 MiB, not total simulator VRAM.
  After cleanup, GPU use returned to 252 MiB / 0%; process group 79217 exited.
- The two inputs are nearby initial views of one scene, not independent scene
  samples. No occlusion, distance, crowd, language-dataset or training change
  was tested. Initial visual ambiguity may still interact with instruction.
- This reproduces and isolates a **first-call symptom**. Later asynchronous
  cache updates, recovery behavior, collisions and the full 70-second failure
  remain outside this offline causal test. No navigation-fix claim is made.
- Next useful discrimination: keep the same fixture and vary only the target
  phrase (Chinese target name versus English target name in the same sentence),
  then separately assess controller handling of near-origin plans. A corrected
  closed-loop result would require a subsequent simulator validation.

## Artifacts and regeneration

- [Complete runtime report](executions/20260908T160120Z/results/report.json)
- [Analysis and paired checks](analysis/summary.json)
- [Trajectory figure](analysis/frozen_trajectory_comparison.png)
- [Source-derived controller parity](executions/20260908T160120Z/results/controller_parity.json)
- [Local integrity](executions/20260908T160120Z/local_integrity.json)
- [Failed harness attempt](executions/20260908T155955Z/stderr.log)

On the existing execution host, sync the local package first and retain its
manifest. Source `configs/remote_env.sh`, prepend `demo/work/DynaNav` and
`demo/work` to `PYTHONPATH`, then use the pinned IsaacLab Python to run
`run_bounded.py`. It creates a new dated execution directory and refuses output
overwrite. Download the whole execution directory and run locally:

```bash
python3 analysis/analyze.py NEW_EXECUTION_ID
```

The source/asset gate must pass again before every replay. Original simulator
logs remain under the parent `runs/` and remote `work/DynaNav/logs/` directories.
