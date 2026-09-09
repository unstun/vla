---
origin: ai+local+official_sources
reviewed: false
date: 2026-09-09
thread_id: 01a080e1-1419-7611-a5cc-6d2d641bae42
stage: experiment_preparation_and_analysis
---

# VLA handoff: LightNav-0 is prepared, not executed

Dr Sun requested local archival before the current session's usage runs out.
The latest experiment request is: **LightNav-0 的复现，在服务器上复现官方案例版**.
The established workflow is manual Opus execution: the lead prepares an English
package, Dr Sun passes it to Opus, Opus returns an English report, and the lead
checks actual local artifacts and reports to Dr Sun in Chinese. Every reply
starts `Dr Sun,`. Do not mention Chinese reporting preferences in Opus prompts.
Do not substitute another model or launch a remote experiment merely to resume
this archived conversation.

## Resume here

- Package: `.pipeline/experiments/2026-09-09_lightnav0_official_demo_rented4090/OPUS_EXECUTION_PACKAGE.md`.
- Experiment (`LNEXP` below): `.pipeline/experiments/2026-09-09_lightnav0_official_demo_rented4090/`.
- Dedicated task: `.trellis/tasks/09-09-lightnav0-official-demo-rented4090/`.
  PRD, design, implementation plan and task metadata exist. Status is `planning`,
  execution metadata `prepared_not_dispatched`. It was created with `--no-start`;
  the prior DualVLN task remains the session's active pointer.
- No Opus dispatch ID, installed LightNav runtime, downloaded model weights,
  model inference, navigation episode or LightNav video exists yet.
- Preparation validation: `LNEXP/setup/preparation_validation.json`.
  It checks 18 prepared files, a 2,459-file source manifest and 2,236 scene
  assets. Source checkout is clean. Archive files are separate from this frozen
  preparation manifest; do not rewrite hashes to conceal subsequent changes.

When Dr Sun pastes an Opus return, read `LNEXP/OPUS_RETURN.md`, actual commands,
source diff, model/scene manifests, raw outputs and decoded videos. Package
preparation does not establish reproduction. If asked to dispatch differently,
follow the new explicit instruction while preserving the package's experiment
and source-of-truth boundaries.

## LightNav-0 fixed case and provenance

- Canonical repository: https://github.com/lightorigins/LightNav-0
- Source commit: `d83fbfb9748ca6b497a2f2a7f4a3e95e2110e40c`.
- Local pristine source:
  `references/upstream/2026-09-09_lightnav0_official_demo/source/LightNav-0`.
- Provenance and code map: adjacent `repository_manifest.yaml`, `comparison.md`;
  survey `.pipeline/survey/2026-09-09_lightnav0_official_demo_upstream_survey.md`.
- HF model: `LightOriginsHQ/LightNav-0`, revision
  `826dc5fbfa37afa8293d2e336d329b6ffc0bfb64`, original BF16.
  HF metadata reports 4,847,825,408 stored parameters. Weight shard:
  9,695,744,034 bytes, SHA-256
  `ffc4a925378a881afa761865048eb8d07c55cacf5eaf66548b6641c39f67af18`.
  Model API/configs were fetched; weights were not. API `gated=false` was verified.
- Official bundled MuJoCo case: ProcTHOR `val_2_ceiling.xml`, default TurtleBot,
  default spawn `(6.5,13.8,0)`, original front RGB and MPC.
- Exact default instruction from upstream `web/index.html:48`:
  `move forward, then go to the trashcan on the right`.
- Bundled scene: 2,236 files / 65,457,963 bytes, all size/SHA-256 verified;
  Ai2 MolmoSpaces revision `c89e1f5481af56fd25ef4efb76bdced9b726ec6a`, CC BY 4.0.
  The source/model licenses are Apache-2.0; retain separate scene attribution.
- No gated MP3D/HM3D assets are needed for this case.
- Default TurtleBot movement is **kinematic**. This case cannot validate
  quadruped locomotion, contact safety, or full paper benchmark scores.

## Server and execution boundaries

Read-only observation on **2026-09-09 14:47:38 UTC**, not a permanent state:

- SSH `rented4090` → `ubuntu@117.50.179.202:22`, existing key authentication.
  Never copy the old pasted password into prompts, reports, scripts or memory.
- Hostname `10-60-164-100`; RTX 4090 24,564 MiB; sampled use 2,903 MiB;
  driver 575.57.08; root disk about 78 GiB free.
- Protected unrelated process: PID 1247 `/isaac-sim/kit/kit`, about 2,859 MiB.
  Recheck process identity before acting; do not terminate it.
- `uv` and `python3.11` were not found on login-shell PATH. Runtime installation
  is still pending. Do not reuse/alter the DualVLN or Isaac Sim environments.
- Remote LightNav root:
  `/home/ubuntu/sun/vla_exec/2026-09-09_lightnav0_official_demo_rented4090`.
- Official inference pins: Python 3.11, vLLM 0.19.1, Transformers 5.8.0,
  nvidia-cutlass-dsl 4.5.2. MuJoCo demo has its own uv environment.
- Package uses original BF16 and `--task vln`, localhost services; original
  vLLM backend first, official HF backend only as an explicit recorded fallback.
  Preserve original visual/history/decoder/controller settings. No quantization.
- Three fixed repetitions; each capped at 180 wall seconds or 180 decisions;
  setup/download cap 60 minutes, combined model startup/GPU runs cap 1,800 seconds.
- Save raw model text, decoded waypoints, stop provenance, MPC commands, poses,
  clocks and resource samples. Distinguish model stop, invalid output, timeout,
  watchdog and owner-WebSocket disconnect. Closing the UI-owner socket stops control.
- On native stop, observe another two seconds to check actual stillness. A stop
  in the wrong place does not satisfy the navigation task.
- Return first-person, native third-person and paired MP4s for every attempt,
  including failures. Keep raw camera evidence. Official renderer can clamp long
  frame gaps, so preserve a full elapsed-time recording and label playback clocks.
- Exact source/model/config/evidence hashes must match locally after return.
  All final code changes belong in local `LNEXP/work/LightNav-0` with a patch
  against pristine source. Stop only task-owned services after syncing.
- No training, robot actuation, public service exposure, driver changes, or
  unrelated process cleanup is authorized by this package.

## TIC-VLA observations discussed immediately before LightNav selection

This is the earlier InternVL3-1B-based model, not DualVLN. Current primary paper:
https://arxiv.org/html/2602.02459v2.

- Training: frozen visual encoder + language-model supervised fine-tuning;
  action-expert imitation with synthetic 0–10 s semantic delays; action-only PPO.
  Data includes SCAND, GND and DynaNav; 310 episodes/5.1 h refers only to the
  authors' DynaNav collection, not all training data. The released checkpoint's
  final-PPO status is not explicitly established by the release README.
- Go2 hardware Figure 6 (`Fig_5.png`) labels front RGB, an additional head-top
  depth camera and LiDAR. Paper says model receives front RGB. Exact mount height,
  tilt and camera model were not established. Do not infer model depth/LiDAR input
  or a particular SLAM implementation from the hardware picture. High videos
  showing the entire robot are external views, not the policy camera.
- The current Nova Carter path predicts 30 two-dimensional waypoints and uses a
  waypoint controller. A controller zero branch exists for a near-zero lookahead
  point; this path does not independently parse language `STOP` like DualVLN.
- Official `DynaNav/benchmark.py:547` ends the simulator at the goal-distance
  condition. That termination alone does not establish learned stopping.
- Raw metric-trial telemetry was checked this session: Chinese instruction
  `向前直走 3 米，然后停下` crossed 3.011 m with actual speed 1.3817 m/s,
  desired/applied speed 1.5 m/s. The Chinese/English matched pair both failed
  near-target sustained-stop criteria; termination was timeout, with evaluator
  goal-stop disabled and waypoint controller unchanged.
- Source/results:
  `.pipeline/experiments/2026-09-08_tic_vla_dynanav_5070ti/distance_language_pair_2026-09-08/RESULT.md`;
  run `20260908T163626Z_metric_zh/telemetry.jsonl`, frame 273;
  pinned TIC source commit `9fa6f8b66b9e121d5df5df071297bba8e5353ebb`.
- Do not infer general language rankings or that all 1B models cannot stop from
  these limited trials. Separate model behavior from controller behavior.

## Previous DualVLN state to preserve

`DVEXP` = `.pipeline/experiments/2026-09-08_dualvln_rented4090`.

- Official evaluator ran five times on two frozen **custom public castle**
  episodes: success 3/5 and 2/5; all ten runs had native System-2 STOP.
  Episode 2 had 8–10 recorded collisions. These are not R2R benchmark results.
- Standard frozen R2R episodes 10/11/12 remain unexecuted because MP3D scene
  access/terms were not cleared. Never equate public castle tasks with R2R.
- Use `DVEXP/review/PUBLIC_SCENES_LEAD_REVIEW.md`, not just the Opus summary.
  Its findings include two derived-file manifest mismatches and overstrong
  claims about unique RNG causes. Raw run/video evidence was preserved locally.
- User instruction `往前走，走到两个椅子中间` is archived under
  `DVEXP/public_scenes/requests/2026-09-09_zh_between_two_chairs`.
  Review: `review/LEAD_REVIEW.md`. The actual run `zh_chairs_v1` had 51 actions,
  initial 120-degree left turn, 6.75 m path and native STOP. Chairs remain in
  front; strict geometric arrival between two chairs was not validated.
- Videos:
  `DVEXP/public_scenes/runs/zh_chairs_v1/vis_0/skokloster-castle/0001_success0.mp4`
  and `vis_debug/epoch_0/skokloster-castle_0001.mp4`.
  The filename's success flag uses a bookkeeping goal, not the user's chair task.
- Preserve failed-run evidence; previous Opus deletion/reuse of two initial
  failed chair attempts was a review finding, not a pattern to repeat.

## Archive and Git boundaries

Large prior experiments and unrelated dirty files already existed. This archive
does not stage their entire directories, credentials, models, videos or source
copies. The local Git backup includes the new LightNav preparation documents,
their small manifests, this handoff and the archive-owned memory files only.
Old raw evidence remains at its existing local paths. There is no configured
Git remote, so this is a local backup, not an off-machine backup.

See `.pipeline/handoffs/2026-09-09_vla_archive_report.md` for archive validation,
quality-gate status and backup details. No research result is promoted by archival.
