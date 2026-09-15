---
origin: ai_only
reviewed: false
stage: planning
status: surveyed
---

# Quadruped world-action candidates

Checked on 2026-09-10. This bounded survey interprets the request as learned
world models supporting language-conditioned robot action, while explicitly
separating locomotion methods without language. No ready-to-deploy Lite3
checkpoint was established. All candidates remain `surveyed` locally.

## Candidate comparison

| Candidate | Primary evidence and interface | Release boundary |
|---|---|---|
| Metis | [Paper, v1](https://arxiv.org/html/2606.15869v1) reports Go2 navigation. Image, instruction, and ego state condition navigation waypoints; a PD controller converts them to velocity commands. World prediction supervises training; inference bypasses future-video generation. | [Repository](https://github.com/LogosRoboticsGroup/Metis) contains documentation/assets, not executable implementation or weights at the inspected pin. Its planned August release date is not release evidence. |
| DECOWAM | [Paper, v1](https://arxiv.org/html/2608.20114v1) reports a quadruped with a six-axis arm. Current RGB, language, and 14-D state condition a 48-step action chunk and future video. Channels include arm/gripper, base velocity, and padding. | No author-linked implementation/checkpoint was identified. Robot product name is unspecified; DEEP Robotics affiliation does not establish Lite3 support. |
| AstraNav-World | [Paper, v1](https://arxiv.org/html/2512.21714v1) combines visual history/instructions, a video predictor, and a waypoint policy. Physical-robot demonstrations are reported, but the inspected text does not identify a quadruped model. | [Repository](https://github.com/amap-cvlab/AstraNav-World) provides Action Former benchmark inference and a [ModelScope link](https://modelscope.ai/models/chongchongjj/AstraNav_World_ActionFormer). Diffusion-policy release is still listed as pending. Checkpoint bytes were not verified. |
| WMP | [Project](https://wmp-loco.github.io/) reports A1 terrain traversal with world-model-based perception. It is visual/proprioceptive locomotion, without a language interface. | [Code](https://github.com/bytedance/WMP) is available. README instructs users to train before playback; no checkpoint file/link was found in the inspected tree/README. It is not a complete WLA. |

## Repository pins and reproduction entry points

| Repository | Default branch and commit | Repository license | Original entry point and assumptions |
|---|---|---|---|
| `LogosRoboticsGroup/Metis` | `main`, `7677b62d786cff8bb2044b489bd41f3d59514b43` | Apache-2.0 | No runnable command published at this pin. Model zoo still pending. |
| `amap-cvlab/AstraNav-World` | `main`, `856b9aa992ea11d68ae6b35260b4e5f432be8cb9` | Apache-2.0 | `cd infer_r2r_rxr` then `bash eval_r2r.sh`; PyTorch >=2.6, Habitat 0.1.7 for R2R/RxR, different 0.2.3 dependencies for OVON. Needs model and benchmark assets. |
| `bytedance/WMP` | `master`, `c232c115ada4517453ebded5019078ba055456de` | Apache-2.0 | Python 3.8 recommended, Isaac Gym Preview 3, CUDA PyTorch. `python legged_gym/scripts/train.py --task=a1_amp --headless --sim_device=cuda:0`; subsequent `play.py` requires a trained policy. Formal training is not authorized by this survey. |
| DECOWAM | No canonical implementation identified | Code/model license unknown | No verified reproduction command. |

Repository licenses do not establish checkpoint or dataset licenses.
Maintenance snapshots: AstraNav repository last pushed 2026-01-21, Metis
2026-06-16, WMP 2024-12-18. These are GitHub metadata, not maintenance promises.

## Additional verification

- GitHub REST metadata and recursive trees were inspected without cloning.
- AstraNav's pinned `world/wan/models/action_former/action_former_policy.py`
  returns waypoint, arrival, sine, and cosine predictions at line 56.
  `infer_r2r_rxr/eval_r2r.sh` expects a user-supplied checkpoint path.
- The README announces Action Former inference weights. Web extraction of
  the ModelScope page failed, and a direct file-list API probe returned 404.
  This does not prove that the model is absent, but prevents a verified
  downloadable-checkpoint claim in this survey.
- DECOWAM's paper identifies 14-D actions as six arm targets, one gripper
  channel, three base-velocity channels, and four padding channels. Its
  mobile-manipulation setting does not establish standalone Lite3 navigation.
- GenRL and general VLA results appeared as search leads but are not promoted
  to confirmed quadruped WLA deployment candidates here.

## Recommendation and claim boundary

For language-guided navigation research, inspect AstraNav's released Action
Former variant first, conditional on checkpoint access and asset licenses.
The smallest original target is a bounded official Habitat evaluation, not a
Lite3 control loop. Metis has clearer Go2 evidence but lacks a runnable release
at the inspected commit. DECOWAM is relevant if mobile manipulation is within
scope. WMP belongs to the separate locomotion research track.

These priorities are engineering assessments of interface and release
readiness, not measured performance rankings. Adapting a waypoint model to
Lite3 still requires camera/scale/frame calibration, command tracking, and
closed-loop evaluation; joint-action policies require robot-specific dynamics
adaptation. No sources, weights, datasets, or runtimes were imported or run.
Existing research-state indexes and experiment files were not changed.
