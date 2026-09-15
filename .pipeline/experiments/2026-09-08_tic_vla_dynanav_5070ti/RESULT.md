# TIC-VLA hospital closed-loop compatibility trial on RTX 5070 Ti

Date: 2026-09-08. Successful run: `20260908T131741Z`.

## Outcome

The pinned pretrained TIC-VLA executed a closed-loop Nova Carter hospital
episode on the RTX 5070 Ti. Actual simulated RGB frames fed the model; its
finite waypoints produced nonzero wheel-controller commands and observed motion.
The upstream benchmark returned exit 0 and marked the episode successful.

This is one upstream-based compatibility trial on Isaac Sim 5.1. It is not an
exact paper reproduction, a complete DynaNav evaluation, or a Lite3 result.
No training or real-robot command was performed.

## Measured result

| Item | Observed value |
|---|---:|
| Benchmark success | 1 of 1 episode |
| Distance threshold | 1.5 m |
| Final navigation error | 1.484381 m |
| Path length | 12.171777 m |
| Benchmark-reported duration | 18.5 s / 555 frames |
| Total wall time, including setup and shutdown | 114.801728 s |
| Control audit wall-time span | 67.405697 s |
| Finite, correctly shaped model outputs | 184 / 184, each `(1,30,2)` |
| Nonzero model command records | 184 |
| Backup/recovery command records | 0 |
| First in-scene model call | 1.653716 s |
| Later model call p50 / p95 | 38.780 / 64.296 ms |
| Sampled combined GPU memory peak | 15486 / 16303 MiB, approximately 15.12 GiB |
| Benchmark-reported collision indicators | human 0; physical 0 |

These are single-trial measurements. GPU sampling was every approximately two
seconds, so the sampled maximum is not a continuous allocation trace. Initial
total GPU use was 251 MiB, and no unrelated GPU compute process was present.
Model call duration is not the whole control-cycle rate.

The evaluator stops the episode when the robot reaches its configured goal
neighborhood. The last recorded command was still nonzero; this does not prove
that the model independently learned to issue a stop command.

## Visual evidence and playback

- [Third-person video](runs/20260908T131741Z/third_person.mp4)
- [Front-camera video](runs/20260908T131741Z/front_camera.mp4)
- [Structured analysis](runs/20260908T131741Z/analysis.json)
- [Original benchmark output](runs/20260908T131741Z/benchmark_results/hospital_single_results_latest.json)
- [Artifact inventory](runs/20260908T131741Z/artifact_sha256.json)

Each video encodes all 184 retained frames, from frame 3 through frame 552,
at the upstream sensor cadence of 10 FPS. The approximately 18.4-second videos
use the benchmark's frame-counter time basis, not wall-clock playback. No
episode resets or separate runs were spliced together. Representative start,
middle and end images were inspected. The 133368734-byte original camera
archive is stored alongside the videos and is path-specifically ignored;
its SHA-256 is `0490d6e7dc049fa107120a0c57c5d7dd6c49cea2836f8d7774a39f3ff7bb21c5`.

## Source and execution identity

- Local parent commit at task start: `4aa2890`, with unrelated existing edits
  preserved.
- TIC-VLA source: `main`, clean pinned commit
  `9fa6f8b66b9e121d5df5df071297bba8e5353ebb`.
- Source license: UCLA Academic Software License; existing upstream manifest
  retains the license hash and provenance.
- InternVL3-1B revision: `4415a3b810e636d11dfa86b0e9ba40bb00535aa8`.
- Official TIC-VLA checkpoint SHA-256:
  `376263f89fad0f42c267d85655019232edc91d36e214e23424804dd4cd42e036`.
- Runtime: Ubuntu x86_64, RTX 5070 Ti, driver 580.126.09, Isaac Sim 5.1.0.0,
  Python 3.11.15, PyTorch 2.7.0+cu128, Transformers 4.57.6.
- Task-only added dependencies: accelerate 1.10.1, timm 1.0.22,
  opencv-python-headless 4.11.0.86. Existing system packages and drivers were
  not replaced. FlashAttention2 was not installed.
- Remote execution directory:
  `/home/sun/vla_exec/2026-09-08_tic_vla_dynanav_5070ti/`.
- Exact successful source subset: `manifests/successful_run_work.sha256`.
  The unused outdoor vehicle assets were omitted from the transfer.

## Compatibility changes and retained failures

The source algorithm, checkpoint, hospital instruction, seed 36, crowd count
20, 70-second configured timeout and 1.5 m threshold were retained. The example
was reduced to its one hospital episode.

`0001-execution-audit.patch` adds trajectory/controller timing and preserves
front-camera images that upstream cleanup would otherwise remove.
`0002-asynchronous-asset-loads.patch` disables blocking asset loads at simulator
startup and preserves that setting when SDK components rewrite it. The successful
trial combines the task-local capture-settings wrapper and setting-change
subscriptions. Synchronous image rendering remains intact. No global SDK source
was modified; the workaround is specific to this runtime and trial.

The initial scene-only probe blocked at the first render update with synchronous
asset loading. Its asynchronous counterpart rendered successfully. Full attempts
`20260908T125334Z` and `20260908T130935Z` then remained at frame zero and were
explicitly stopped. Their logs, resource samples and stop reasons are retained.
The third attempt, with setting subscriptions, progressed and completed.

The successful variant retains a periodic 90-second `faulthandler` diagnostic.
Its `Timeout` heading is a stack-dump timer, not a simulator deadline failure;
the run metadata has `timed_out=false` and `exit_code=0`.

## Limitations

The SDK reported missing NavMesh random points for some people, unreachable
pedestrian routes and several character PNG texture errors. Camera inspection
confirmed recognizable hospital geometry, the robot and vending-machine area,
but these unresolved errors prevent an exact crowd/visual benchmark claim.
Collision indicators are the upstream detector's outputs, not an independent
safety certification. The paper's 1 m criterion also differs from this example's
1.5 m criterion. The benchmark's frame-derived duration was retained; the physics
clock was not independently instrumented.

## Local integrity and cleanup

See `manifests/local_integrity.json` for the final asset/media hash audit and
`logs/post_run_runtime.txt` for cleanup. The post-run host returned to 251 MiB
GPU use, 0% utilization, no GPU compute processes and no task runtime processes.
Exact model assets are retained locally under `models/` and `checkpoints/`, with
their manifests and regeneration script tracked. No Spot or Lite3 trial was run.

## Subsequent metric-language test

The isolated [Chinese three-meter stop test](distance_stop_2026-09-08/RESULT.md)
completed on the same checkpoint with goal-triggered stopping and automatic
backup disabled. It did not follow the command: maximum forward progress was
0.106 m, final forward displacement was -8.440 m and cumulative path was 9.771 m;
there was no qualifying two-second stop near the 3 m reference. The 49.24-second
overhead video and 363 verified artifacts are local. A child-crashed first
attempt is preserved separately. This is a failed metric-language trial, not
evidence of accurate metric stopping or a general checkpoint language limit.

The subsequent [matched metric-language pair](distance_language_pair_2026-09-08/RESULT.md)
used one shared source manifest and fresh Chinese/English processes. Both failed
the three-meter stop criterion. Chinese passed the reference at 1.382 m/s and
continued (20.208 m sampled path); English turned away (9.610 m sampled path).
All 726 run artifacts are verified locally, with original videos and a 15.05 s
simulator-time-aligned comparison. Same-language variation across Chinese runs
and non-identical RGBs limit causal language conclusions.
