---
origin: opus_execution_on_rented4090
reviewed: false
date: 2026-09-09
package_version: 3
executor: Opus
status: returned_for_lead_review
---

# LightNav-0 continuation v3: execution return

## 1. Result first: three real runs, complete evidence, navigation still fails

Primary films (absolute local paths, real H.264 MP4, all fully decoded and inspected):

- `/Users/sun/tongbu/study/phdproject/vla/.pipeline/experiments/2026-09-09_lightnav0_official_demo_rented4090/continuation_v3/media/rep_04/overview_wall.mp4` — share copy `/Users/sun/tongbu/study/phdproject/vla/.pipeline/experiments/2026-09-09_lightnav0_official_demo_rented4090/continuation_v3/media/rep_04/overview_share.mp4`
- `/Users/sun/tongbu/study/phdproject/vla/.pipeline/experiments/2026-09-09_lightnav0_official_demo_rented4090/continuation_v3/media/rep_05/overview_wall.mp4` — share copy `/Users/sun/tongbu/study/phdproject/vla/.pipeline/experiments/2026-09-09_lightnav0_official_demo_rented4090/continuation_v3/media/rep_05/overview_share.mp4`
- `/Users/sun/tongbu/study/phdproject/vla/.pipeline/experiments/2026-09-09_lightnav0_official_demo_rented4090/continuation_v3/media/rep_06/overview_wall.mp4` — share copy `/Users/sun/tongbu/study/phdproject/vla/.pipeline/experiments/2026-09-09_lightnav0_official_demo_rented4090/continuation_v3/media/rep_06/overview_share.mp4`

Index: `/Users/sun/tongbu/study/phdproject/vla/.pipeline/experiments/2026-09-09_lightnav0_official_demo_rented4090/continuation_v3/media/ALL_RUNS.md`. Analysis: `/Users/sun/tongbu/study/phdproject/vla/.pipeline/experiments/2026-09-09_lightnav0_official_demo_rented4090/continuation_v3/analysis/summary.md`, `summary.json`.

**Outcome: the native STOP mechanism worked in all six runs, the robot really was
still afterwards, and no run stopped at the requested trashcan.** The three new runs
did not reproduce the author demonstration and were not retried to obtain a success.

| run | cohort | termination | decisions | consumed STOP seq | sampled stillness | end (x, y) | d(requested trashcan) | d(2nd trashcan) | d(dog bed) | <=1.0/1.5/2.0 m | visual verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rep_04 | new v3 | model_stop | 64 | 64 | pass | (13.044, 11.902) | **5.192 m** | 3.209 m | 3.549 m | 0/0/0 | other_object |
| rep_05 | new v3 | model_stop | 63 | 63 | pass | (13.069, 11.852) | **5.190 m** | 3.154 m | 3.551 m | 0/0/0 | other_object |
| rep_06 | new v3 | model_stop | 36 | 36 | pass | (9.435, 11.614) | **2.435 m** | 5.666 m | 1.266 m | 0/0/0 | other_object |
| rep_01 | legacy r1 | model_stop | 40 | not recorded | not measurable | (9.662, 11.483) | 2.414 m | 5.404 m | 1.086 m | 0/0/0 | other_object |
| rep_02 | legacy r1 | model_stop | 38 | not recorded | not measurable | (9.395, 11.456) | 2.274 m | 5.632 m | 1.131 m | 0/0/0 | other_object |
| rep_03 | legacy r1 | model_stop | 44 | not recorded | not measurable | (10.548, 10.995) | 2.609 m | 4.393 m | 0.931 m | 0/0/0 | other_object |

Distances are planar, computed from the compiled scene body roots, not from prose:
requested trashcan `ashcan_..._1_0_4` at (8.517244, 9.358022); a **second trashcan**
`ashcan_..._2_0_9` at (14.476999, 9.029993); dog bed `pad_..._1_0_4` at (9.823960, 10.409500).
The 1.0/1.5/2.0 m radii are diagnostic only and were fixed before the runs; they are
not an official benchmark success rate.

Three separate result fields, as required:

1. **Native STOP consumed by the demo?** Yes in all three new runs: seq 64 / 63 / 36,
   traced as `native_stop_consumed` in the demo's own consumption record.
2. **Still afterwards?** Yes. Sampled stillness from the 20 Hz capture stream passed in
   all three: window 3.54 / 3.45 / 3.52 s of monotonic *and* simulation time, first
   sample 21 / 52 / 38 ms after STOP, max adjacent gap 0.066 s, and exactly zero
   commanded rate, observed rate, planar drift and yaw drift. This is sampled evidence,
   not a proof of permanent rest.
3. **Where did it stop?** Nowhere near the requested trashcan. rep_04/rep_05 drove
   through to the far right and stopped ~5.19 m from the requested trashcan and ~3.2 m
   from the *other* trashcan. rep_06 and all three legacy runs stopped in the dog-bed
   region, 0.93-1.27 m from the dog bed and 2.27-2.61 m from the requested trashcan.
   `media/rep_06/keyframe_final.png` shows the model's OPOS marker landing on the dog
   bed while a green trashcan is plainly visible to its right in the same model input.
   A pixel landing on an object is an observed pointing association, not a proof of the
   model's internal reasoning; no offline segmentation pass was run (see section 6).

**A correct STOP at the wrong place is still a navigation failure.** Every attempt is
retained; nothing was re-run to obtain a nicer video.

## 2. Frozen identity, source changes and exact commands

- Source: <https://github.com/lightorigins/LightNav-0>, commit
  `d83fbfb9748ca6b497a2f2a7f4a3e95e2110e40c`, Apache-2.0.
- Checkpoint: revision `826dc5fbfa37afa8293d2e336d329b6ffc0bfb64`, original BF16.
  Rehashed at execution time: 20 files, 9,709,350,260 bytes, weight shard
  `ffc4a925378a881afa761865048eb8d07c55cacf5eaf66548b6641c39f67af18` — matches
  (`setup/checkpoint_rehash_v3.json`). The 9.7 GB payload was verified in place, not copied.
- Instruction, byte-for-byte `move forward, then go to the trashcan on the right`,
  SHA-256 `87ef6df01a076e5d78c06ad6badab2f5f8c1c80a587d687c7a4222fe5a35427e`, asserted
  by the harness before every send.
- Backend `--task vln --backend vllm_local`, greedy, shipped RVQ decoder,
  `--gpu_memory_utilization 0.80 --max_batch_size 8`, `--cam_hfov_deg 112.2 --cam_height 0.198`.
  No FP8, no quantization, no prompt/camera/history/controller change, no extra case.
- Scene `val_2_ceiling.xml`, kinematic TurtleBot, spawn (6.5, 13.8, 0), unmodified.

Work copy: `/Users/sun/tongbu/study/phdproject/vla/.pipeline/experiments/2026-09-09_lightnav0_official_demo_rented4090/continuation_v3/../work/LightNav-0-visual-v3`, built from the pinned snapshot with
`.git` and `docs/assets` deliberately excluded (2451 files; 2450 upstream + 1 new module).
Manifest: `setup/v3_source_manifest.json`. Patch: `patches/v3_telemetry.patch`.

Exactly four files differ from the pinned source, all inside the allowed demo seam,
all observation-only and disabled unless `LIGHTNAV_V3_TRACE_DIR` is set:

| file | change |
| --- | --- |
| `mujoco_demo/vln_mujoco/v3_capture.py` | new: bounded non-blocking writer queue, monotonic frame IDs, exclusive file creation, SHA-256, index/state/trace writers, loss counters |
| `mujoco_demo/vln_mujoco/simulation.py` | inside the existing capture lock: copy `mjSTATE_INTEGRATION`, `data.time`, monotonic ns, pose, velocity and command; submit the original JPEG pair after encoding |
| `mujoco_demo/vln_mujoco/vln_client.py` | sidecar request/response trace (connection id, seq, stamp, JPEG SHA-256, instruction hash, send/receive monotonic ns, raw wire response, enqueued flag) |
| `mujoco_demo/vln_mujoco/server.py` | consumption labels (`applied_to_mpc` / `native_stop_consumed` / `discarded_after_stop` / `missing_capture_pose`), control trace, lifecycle events, recorder flush on shutdown |

No neural code, robot stepping, MPC optimisation, camera setting, wire field, session
semantic or control decision was changed. `src/` is byte-identical to the pinned source.

Service-window commands (`scripts/run_all_v3.sh`, run IDs below):

```bash
PYTHONPATH=$W/src CUDA_VISIBLE_DEVICES=0 $MODEL_PY -m lightnav.serving.ws_server \
  --task vln --backend vllm_local --model_path "$R/checkpoints/LightNav-0" \
  --host 127.0.0.1 --port 8050 --gpu_memory_utilization 0.80 --max_batch_size 8 \
  --record_dir "$C/records" --ready_file "$JOB/model.ready" \
  --cam_hfov_deg 112.2 --cam_height 0.198
```

```bash
MUJOCO_GL=egl PYTHONPATH=$W/mujoco_demo LIGHTNAV_V3_TRACE_DIR=$CAP $DEMO_PY -m vln_mujoco \
  --robot turtlebot --host 127.0.0.1 --port 8088 --vln-server ws://127.0.0.1:8050
```

```bash
timeout 190 $DEMO_PY $C/scripts/run_episode_v3.py --rep rep_04 --run-dir $C/runs/rep_04 \
  --wall-timeout 180 --decision-cap 180 --post-stop 3.0 --reset-settle 2.0
```

Run IDs and exits: model job `runs/model_server_v3_20260910_034730` (ready after 62 s,
listener PID recorded in `listener.txt`); demo job `runs/demo_server_v3_20260910_034730`
(ready after 7 s); capture stream `runs/capture_v3_20260910_034730`; rep_04/05/06 harness
exit code 0 each, none hit the 190 s process bound, the 180 s wall bound or the 180
decision cap. Loaded module `__file__` paths were checked and all four demo modules
resolved to the v3 work copy (`runs/demo_server_v3_*/module_files.json`); no editable
install bypassed the instrumentation. Task-shell overrides (`VLLM_QUANT`,
`VLN_EVAL_TEMPERATURE/TOP_K/TOP_P/TRAJ_TOP1`, `LIGHTNAV_ATTN`,
`LIGHTNAV_SKIP_VERSION_GUARD`, `VLN_KV_CACHE_GIB`, `VLN_VLLM_ENFORCE_EAGER`,
`MAX_BATCH_SIZE`, `ASPECT_MODE`, `RECORD_*`, `CAM_*`, `WAYPOINT_DT_S`, …) were unset for
the window only; the effective environment is saved in `effective_env.txt`.
No global shell config was edited.

Versions in use: torch 2.10.0, vLLM 0.19.1, Transformers 5.8.0 (model env); MuJoCo 3.11.0,
aiohttp 3.14.3, CasADi 3.7.2, numpy 2.4.6, Pillow 12.3.0, pytest 9.1.1 (demo env);
local QA `/opt/homebrew/bin/ffmpeg` and `ffprobe`; remote encoding used the model env's
bundled `imageio_ffmpeg` binary (v7.0.2) because the host has no system ffmpeg.

## 3. Budgets and resources

| budget | limit | actual |
| --- | --- | --- |
| model+demo service lifetime and all new navigation attempts | 900 s | **128.5 s** (03:47:30.7Z → 03:49:39.2Z UTC) |
| per-run active navigation | 180 s / 180 decisions | 11.36 / 10.82 / 5.45 s; 64 / 63 / 36 decisions |
| per-run post-stop observation | 5 s | 3.0 s requested, 3.54 / 3.45 / 3.52 s measured to termination |
| harness process bound | 190 s | max 19.2 s wall per rep |
| separate GPU render budget after services stopped | 900 s | ~110 s for both overhead render passes |
| recorder dry run | <=15 s | 12 s stationary, model disconnected, harness stop recorded |
| **overall wall budget** | **90 min** | **exceeded — see section 6** |

Independent GPU/RAM sampler, 542 samples, target 0.2 s, actual gap mean 0.237 s
(min 0.228, max 0.291) — the sampler ran slower than target and this is reported rather
than hidden. Whole-card memory 2,903 → 16,904 MiB of 24,564 MiB; GPU util peaked 100 %;
temperature peaked 55 °C; system RAM 4,215 → 9,728 MiB of 64,297 MiB. The card is shared
with a protected Isaac Sim streaming process holding ~2.9 GiB, so these are card totals,
not process-exclusive figures (`analysis/resources.json`).

## 4. Recorder, joins and timing evidence

Pre-run checks, all green before any model launch:

- upstream demo suite on the v3 work copy: **27 passed** in 28.06 s.
- v3 focused checks: **24/24 passed** (`setup/v3_test_results.json`), covering 250
  variable-length index rows without a name collision, duplicate rejection, queue
  overflow counted rather than silently dropped, writer failure traced, state-size
  change treated as malformed, exact-hash join accepted while hash mismatch / unknown
  stamp / wrong connection are rejected, a 5 s artificial gap surviving as 5 s of film
  with the stale frame held and no prediction shown before its arrival, exact MuJoCo
  state round trip, **effective GL orthographic projection = 1**, only the ten named
  ceiling geoms hidden, and identical state for capture-disabled vs capture-enabled
  supplied-control replay. That last check is explicitly *not* a claim that asynchronous
  model trajectories repeat.
- stationary dry run `runs/harness_check`: 242 pairs in 12 s, zero losses, ended with a
  recorded harness stop (`setup/harness_check_verification.json`).

Main capture stream (`setup/capture_verification_20260910_034730.json`): **passed**.

```
index rows == front files == third files == saved states == writer-confirmed frames = 981
queue drops = write failures = duplicate names = malformed rows = 0
```

State records are 24,272 bytes each (3,034 float64, `mjSTATE_INTEGRATION`); `states.f64`
is an exact multiple. Observer enqueue p95 = 43.1 µs, max 159.7 µs — inside the 1 ms
target, so the control loop was not made to wait on disk. Measured capture cadence was
18.91 / 18.93 / 18.93 Hz against the 20 Hz renderer target, max adjacent gap 0.070 s.

Joins are exact: `(connection_id, seq)` plus the byte-exact front-JPEG SHA-256 against
the official `actions.json`/`image_%06d.jpg` records. **65 / 64 / 37 requests, 65 / 64 / 37
joined, 0 join problems.** Byte-identical spawn frames are shared across runs, so the
official episode is first resolved per connection from unambiguous matches and the join
is then restricted to it; ambiguity is rejected rather than guessed
(`scripts/rejoin_local.py`, `scripts/v3_join.py`).

Stop bookkeeping is separated, not merged: rep_04 raw `stop:true` predictions were
seq 64 **and 65**; seq 64 was consumed by the demo as the native stop, and seq 65 arrived
in flight after the session had already been torn down and is retained with
`enqueued: false` — it never reached MPC and never moved the robot. rep_05 (63, 64) and
rep_06 (36, 37) behave the same way. `applied_to_mpc` counts are 63 / 62 / 35.

Timing: client round trip mean 177.7 / 170.7 / 150.0 ms; the server's own reported
latency mean 169.2 / 163.0 / 142.3 ms — reported as two separate series, since the
server records after sending. MPC solve mean 8.7 / 8.6 / 9.3 ms, max 21.0 ms.

First observable divergence (`analysis/divergence.json`): the three new runs emit
identical raw model text for the first four decisions. rep_04 vs rep_06 and rep_05 vs
rep_06 first differ at **seq 5**, and only in the pointing token
(`<apos_704>` vs `<apos_703>`) with identical action tokens; rep_04 vs rep_05 first
differ at **seq 6**, there with different action tokens. Decoding is greedy, so this is
consistent with asynchronous capture/control timing producing slightly different input
frames. It does **not** establish that timing is the cause; no logits were saved and
three runs cannot exclude other explanations.

## 5. Media, clocks and QA

Per run: `overview_wall.mp4` (1920x1200, H.264 yuv420p, 20 fps, faststart),
`overview_share.mp4` (1280x800, <1 MB), `native_front_wall.mp4`, `native_third_wall.mp4`
(unannotated original 480x270 frames), `topdown_state_replay_wall.mp4` (1024x768 labelled
overhead), `model_decisions.mp4`, four keyframe PNGs, and `video_metadata.json`.

Source clock: recorded `CLOCK_MONOTONIC` inside the demo process. The presentation clock
is a 20 fps sampling of the instruction-send → termination interval; every panel shares
it. Panel B deliberately shows the older image belonging to the newest *arrived* result
and prints its age; before the first result it shows `WAITING FOR RESULT`. No result is
shown before its recorded arrival time, and no APOS/OPOS pixels are drawn on a newer
camera image. Held stale frames are labelled and counted, never interpolated.

Labels per file are recorded as `live_capture`, `state_replay` or `decision_review`.
`model_decisions.mp4` and the legacy overlays carry an on-screen
`DECISION REVIEW / NOT WALL TIME` banner.

Media QA (`media/media_qa.json`): **24 MP4s, all fully decoded by ffmpeg with no stderr,
zero failures.** Master PTS duration vs recorded monotonic span: 15.000 vs 14.964 s
(+0.036), 14.400 vs 14.354 s (+0.046), 9.050 vs 9.050 s (+0.000) — all within one 20 fps
frame, with no editorial holds. Presentation/unique-source frames: 300/279, 288/266,
181/164 (21/22/17 held repetitions, from the 18.9 Hz capture against the 20 fps timeline).
Recording losses: 0. I inspected start / first-turn / native-stop / final keyframes for
all three runs and additionally sampled t=2/5/8 s frames from each master; labels are
readable at master resolution, aspect ratios are preserved with letterboxing, the robot
and both objects stay inside the fixed overhead frame, and no future path is drawn.

Overhead geometry: one **common fixed orthographic view** for all three new runs,
look-at (9.784, 12.614), 7.534 m vertical x 10.045 m horizontal span, 1024x768, verified
effective `orthographic = 1` on the actual GL camera (not only the requested camera).
Only the ten `ceiling_*_visual_0` geoms are hidden, and only in the separate
render-only model. Replay uses `mj_setState` + `mj_forward` exclusively — zero
`mj_step` calls, no interpolated or invented positions. Robot-local predictions are
converted with the **capture** pose. Ground overlays on the native image use the
compiled camera transform (0.090 m forward offset, 0.198 m height, fovy 79.865°, points
behind the camera rejected); ground-plane Z = 0 is a declared display assumption. The
upstream shifted display ribbon was never used as metric evidence.

Legacy derivatives are new files under `media/legacy_rep_0*/` only; the originals are
untouched. Independently recomputed round-1 losses: **31 / 28 / 32** frames overwritten
per stream (87→56, 79→51, 90→58), matching the lead's figures. Those runs saved no
MuJoCo state, so they get a clearly labelled XY trajectory diagram instead of an
overhead state replay, and their gaps stay visible.

## 6. Integrity, cleanup, deviations and open questions

- **Sync gate** (`setup/sync_gate_verification.json`): local and remote v3 work copies
  are **2451 / 2451 files with zero hash mismatches** (python runtime caches excluded).
  The only files differing from the pinned source are the four allowlisted telemetry
  files; nothing outside the allowlist changed.
- **Return integrity**: `setup/return_manifest.json` lists 2749 files / 125.9 MB with
  SHA-256 for everything under `continuation_v3` except the lead's read-only
  `research/` inputs. The transferred archive `setup/v3_return.tgz` hashes to
  `5b7493e04aea1bebb44fc0d5dc7eb9c078b62555f636e71c6109f57f9a20225d` on both hosts.
- **Legacy preservation** (`setup/legacy_integrity_recheck.json`): all **559** files in
  `research/legacy_frozen_manifest.json` rechecked, **0 missing, 0 mismatched**.
- **Cleanup** (`setup/final_host_state.txt`): no `ws_server`/`vln_mujoco` process
  remains, nothing listens on 8050/8088, GPU back to 2,903 MiB used / 21,179 MiB free,
  46 GiB disk free. The protected Isaac Sim processes **1213 and 1251 are alive and
  untouched**, with unchanged uptime. No unrelated workload was stopped or reconfigured.
- **Not staged, not committed, not pushed.** No agent or task was dispatched.

Deviations and limitations, stated plainly:

1. **The 90-minute overall wall budget was exceeded.** The bounded parts stayed inside
   their own limits (service window 128.5 s of 900 s; render ~110 s of 900 s), but
   implementation, two composition retries after real layout bugs, transfer and QA
   pushed total session time well past 90 minutes. I continued rather than returning a
   half-built deliverable; the overrun is a deviation, not an approved extension.
2. **One capture stream for three runs.** The demo process ran once and recorded one
   continuous, provably complete stream; per-run sets are sliced by the harness's
   recorded monotonic boundaries. Completeness is proved globally, not per run.
3. **Overhead frames were encoded remotely at CRF 14 / yuv444p and re-composited
   locally.** The state replay is therefore a lightly recompressed render, not a lossless
   one. The original JPEGs and MuJoCo states are returned intact and every film is
   regenerable from them; native camera evidence was never re-encoded before inference.
4. **No offline segmentation pass** was run to confirm that OPOS pixels sit on actual
   trashcan or dog-bed geometry. The dog-bed association in rep_06 is a visual reading of
   the returned frames, not a segmentation-verified fact.
5. **Two composition defects were found and fixed** during QA (panel A showed a wall-vs-
   monotonic clock subtraction as a nonsense frame age; the overhead panel was clipped by
   a bad paste). Both were fixed and every film was regenerated; the earlier frames are
   not part of the delivered set.
6. **The sampler ran at ~0.237 s instead of 0.2 s**, so short GPU transients between
   samples could be missed.
7. Open questions for the lead, deliberately not acted on here: the scene contains a
   **second trashcan** at (14.477, 9.030) and rep_04/rep_05 stopped in its direction —
   whether "the trashcan on the right" is ambiguous for this spawn is a question this
   fixed-case package cannot settle. Why round 2 produced 63-64 decisions where round 1
   produced 38-44, and why one of three runs (rep_06) still landed in the dog-bed cluster,
   are unexplained. Any prompt, backend, controller or camera intervention belongs in a
   separate reviewed experiment, not here.

## 7. Reproduction pointers

`scripts/run_all_v3.sh` (service window and three runs), `scripts/run_episode_v3.py`
(harness), `scripts/test_v3.py` (pre-run checks), `scripts/verify_capture.py`,
`scripts/render_replay.py` (offline state replay), `scripts/rejoin_local.py`,
`scripts/compose_video.py`, `scripts/legacy_derivatives.py`, `scripts/analyze.py`,
`scripts/media_qa.py`, and helpers `v3_join.py`, `v3_timeline.py`, `v3_render.py`.
Raw evidence: `runs/capture_v3_20260910_034730/` (frames, index, `states.f64`, traces),
`runs/rep_0*/` (episode, events, snapshots), `records/run_20260910_114735/` (official
model records), `analysis/` (slices, joins, replay meta, resources, divergence).

## 8. One decision left to the lead: the raw-evidence ignore

`continuation_v3/runs/` holds 65 MB of raw evidence (1,962 original JPEGs, the 23 MB
`states.f64`, traces and logs) and `continuation_v3/media/` holds 40 MB of films; none of
it is covered by the existing `work/` ignore, so it currently shows as untracked and
would be committed. `setup/v3_return.tgz` (20 MB) is additionally a compressed duplicate
of the extracted `runs/records/analysis/setup` content and is only kept so the transfer
can be re-verified byte for byte.

I did **not** edit `.gitignore`. That file already carries concurrent uncommitted edits
from other work in this repository, and adding an ignore entry is a repository-policy
decision that belongs to the lead. The package's own rule points at a narrow
path-specific ignore plus tracked provenance, hash and regeneration instructions; all
three of those already exist (`setup/return_manifest.json`, `setup/v3_return.tgz` +
its SHA-256, and section 7). My recommendation is to keep `media/` tracked, and to add a
single narrow entry for `.../continuation_v3/runs/capture_v3_*/frames/` and
`.../continuation_v3/runs/capture_v3_*/states.f64` if the raw bytes should stay
local-only — but that is the lead's call, not mine, and I made no such change.
