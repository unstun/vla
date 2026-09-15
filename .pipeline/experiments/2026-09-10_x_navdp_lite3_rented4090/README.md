# X-NavDP with simulated Lite3 on rented RTX 4090

Stage: experiment + analysis. Four physical simulation trials executed and
audited; ready for human review. X-NavDP is integrated with this task's Lite3
simulator, and the declared four-case screen passed. This is not an official
benchmark reproduction or broad reliability validation.
Dr Sun selected X-NavDP and requested deletion of LightNav model/runtime copies
while preserving evidence. This experiment is independent of the retired runtimes.

## Measured behavior

Both blocked-route trials went around the 0.70 m tall box with zero detected
obstacle or boundary contacts. All four trials entered the external 0.25 m
arrival radius and received zero velocity commands afterward.

| Case | Forward displacement | Final goal error | Actual path length | Time to arrival | Contacts |
| --- | ---: | ---: | ---: | ---: | ---: |
| Clear 1 m | 0.766 m | 0.235 m | 0.821 m | 3.65 s | 0 |
| Clear 2 m | 1.831 m | 0.229 m | 1.877 m | 6.84 s | 0 |
| Blocked 4 m, seed 41 | 3.841 m | 0.213 m | 4.572 m | 15.43 s | 0 |
| Blocked 4 m, seed 42 | 3.865 m | 0.208 m | 4.512 m | 14.73 s | 0 |

Times are wall time after the standing warmup and before the two-second stop
observation. Forward displacement is projected onto the initial heading, not
distance traveled along the curved path. The 1 m / 2 m results do not demonstrate
exact-distance stopping: the external radius deliberately stops them early.
Late post-stop XY drift over the final 0.5 s was 0.9–5.2 mm across the trials.

- [All four trials, 49.1 s](media/suite01/all_trials.mp4)
- [Seed 41 obstacle trial](media/suite01/blocked_4m_seed41.mp4)
- [Seed 42 obstacle trial](media/suite01/blocked_4m_seed42.mp4)
- [Measured trajectories](media/suite01/trajectories.png)
- [Machine-readable audit](runs/suite01/evidence_audit.json)
- [Metric table](runs/suite01/measured_summary.csv)

The deployed checkpoint ran in **FP32**, with 173,397,002 inference parameters,
PyTorch 2.7.0+cu128, CUDA 12.8 and an RTX 4090. The model wrapper's per-case
median time was 0.585–0.657 s, including original visualization/recovery code.
The freshness watchdog zeroed commands on 197 control ticks in total. This
watchdog measures time since output completion; it does not impose a bound on
the age of the image used by a newly completed prediction. Dynamic-obstacle
response has not been validated. Total-card sampled peak was 4,525 MiB against
a 2,903 MiB baseline occupied by the separate Isaac Sim process.

This supplies encouraging evidence for RGB-D local obstacle avoidance. It does
not establish Chinese prompt understanding, semantic target recognition,
collision-free operation in general, or superiority over LightNav under matched
inputs. X-NavDP received numeric goals, depth and simulator odometry; the prior
LightNav experiment received RGB and text. X-NavDP's Go2 quadruped embedding was
used unchanged for this Lite3 transfer.

## Fixed scope

- X-NavDP source: `bff5eb8857f50e082243fb455d312409daabc3aa`.
- Checkpoint: `InternRobotics/X-NavDP`, revision
  `7cee38a8d8308874d2b8488783c612f42060ac41`, `x-navdp_posttrain.ckpt`.
  SHA-256 `267089a81bbbe7a913debda6603f3f1b66a79520370ce953b2d888d793b89f24`.
- Original quadruped embedding (index 2), original inference preprocessing,
  diffusion/critic/recovery wrapper, and acados MPC. This is a Go2-to-Lite3
  transfer experiment, not an official Isaac benchmark reproduction.
- Simulated Lite3: same physical MuJoCo model and user-selected `model_149999`
  FP32 ONNX walking export as the prior trials. Real joint torques and contacts.
- Numerical point goals, RGB and metric depth. No language input is sent to
  X-NavDP. Odometry and metric goals are explicit additional information relative
  to the old RGB/text LightNav experiment.
- Clear 1 m and 2 m goals; two seeded 4 m goals with a 0.60 x 0.90 x 0.70 m
  obstacle in the route. Open space exists on both sides. The old trashcan body
  is removed so the geometric goal occupies free space.
- External arrival threshold 0.25 m; maximum active wall time 40 s per case;
  contact/fall abort; 0.5 s output freshness watchdog; 2 s post-stop observation.
  These stops are evaluator protections, not native learned STOP.

## Evidence and reproduction

Local source of truth: `/Users/sun/tongbu/study/phdproject/vla`.
Remote execution copy:
`rented4090:/home/ubuntu/sun/vla_exec/2026-09-10_x_navdp_lite3_rented4090`.
The original sources are pinned under
`references/upstream/2026-09-10_navdp_lite3/`. The local `lib/`, assets and scripts
are independently retained with hashes in `setup/reused_source_manifest.json`.
`prepare_local.py` records the one-time import from the now-retired work copy;
the copied files are the continuing experiment inputs.

1. `python scripts/download_model.py` restores the pinned checkpoint and checks
   its published size/hash.
2. Recreate the independent Python environment and use `scripts/setup_runtime.sh`;
   configure the pinned acados build and tera renderer in dependency provenance.
3. Copy the pinned X-NavDP source into `work/x-navdp`, apply
   `patches/acados_0_5_1_api.patch`, and copy/build pinned acados into `work/acados`.
   The patch only adapts access to acados code-generation settings; controller
   costs and dynamics are unchanged. Preserve the identified `lib/`, `policy/`,
   `assets/`, `cases/` and `tools/t_renderer` inputs.
4. Generate `scripts/source_manifest.py --create` locally, synchronize inputs,
   and run `scripts/source_manifest.py` on the execution copy before launching.
5. `bash scripts/launch.sh scripts/preflight.py --run UNIQUE_ID` validates depth,
   coordinate transforms, physical walking, original checkpoint loading and MPC.
6. Run `scripts/run_suite.py --run UNIQUE_ID` through `scripts/launch.sh` under
   the retained `scripts/run_job.py --seconds 600` supervisor.
7. Return records locally and run `scripts/render_videos.py --run UNIQUE_ID`,
   then `scripts/analyze_results.py --run UNIQUE_ID`.

The executed preflight was `preflight03`: all ten checks passed, including a
physical contact-positive probe and a rendered 2 m wall depth check. Initial
preflight failures are retained: `preflight01` exposed the acados API mismatch;
`preflight02` exposed an overly strict audit of unused checkpoint training heads.
The final loader strictly matches every runtime key and separately records the
357 expected unused training keys; there are zero missing runtime keys.
Dependency installation failures and the final successful environment freeze
are retained under `setup/`.

The suite's 62 exact input arrays and output records all joined by sequence and
SHA-256; every MPC solve returned status 0. The 2,096 trace rows and 441 recorded
panels passed the local audit. All four videos and the combined video passed a
full ffmpeg decode. The execution source gate checked 4,608 inputs before launch;
the later `analyze_results.py` is local post-processing and was not an execution
input. Returned remote file hashes are in `setup/run_return_manifest.json`, with
the local comparison in `setup/run_return_verification.json`.

Video
panels include front RGB, third-person, overhead, and colorized metric depth;
exact raw policy RGB/depth arrays are stored separately in each call's NPZ.
Model-wrapper timings include upstream visualization overhead, not pure GPU
kernel latency. The physical simulator runs independently of model inference.

## LightNav retirement

Model and runnable environment copies were removed from the Mac, rented4090,
and gpu5070ti. Historical reports, raw logs, observations, videos, source
provenance, and read-only upstream reference source remain. The per-host cleanup
records and retained-file hashes are in `setup/cleanup_*.json`.
After deletion, all 8,799 retained local files, 8,624 retained rented4090 files,
and 116 retained gpu5070ti files matched their pre-deletion hashes. At final
inspection no task runtime remained, and protected Isaac Sim PIDs 1213/1251
were still running (`setup/final_remote_status.json`). The new X-NavDP runtime
and checkpoint remain available for reuse; there is no active model service.

No training, real-robot motion, staging, commits, or pushes are part of this task.
