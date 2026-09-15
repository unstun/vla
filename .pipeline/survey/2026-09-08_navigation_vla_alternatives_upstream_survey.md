# Navigation VLA alternatives after the TIC-VLA smoke tests

Date: 2026-09-08. Stage: planning / model selection. Status: `surveyed` only.

## Selection criteria and recommendation

The target is instruction-following mobile/quadruped navigation with Chinese
input, offline simulation videos, and an RTX 5070 Ti with 16 GB VRAM. Metric
distance stopping is a separate acceptance requirement. Manipulation-only VLAs
are outside this comparison.

InternVLA-N1 DualVLN is the preferred next reproduction target if a larger GPU
is available: code, checkpoints, inference examples, simulation evaluation,
and Go2 deployment references are public. Its published full-system deployment
uses about 20 GB GPU memory, so it is not a demonstrated unmodified fit for
the 16 GB card. If the 5070 Ti is a hard constraint, first assess NaVILA's
quantization route using recorded images, before committing to simulator
integration. These are reproduction priorities, not proven superiority over
TIC-VLA on the user's scenes or Chinese instructions.

## Candidate evidence

| Candidate | Interface and evidence | Compute / availability | Decision |
| --- | --- | --- | --- |
| InternVLA-N1 DualVLN | Qwen2.5-VL System 2 produces pixel/latent goals; System 1 generates trajectories. Official stack covers Habitat/Isaac Sim and real Go2 deployment. | 7B VLM backbone; released full checkpoint has 8,383,538,891 BF16 parameters according to the HF API. Paper reports about 20 GB on RTX 4090. | First choice with sufficient VRAM; 16 GB quantization remains untested. |
| NaVILA | Legged navigation with language actions carrying spatial quantities, followed by a visual locomotion policy. Public VLA evaluation, locomotion code and Isaac benchmark. | 8B class. Paper Table XIII reports FP16 18.5 GB and W4A16 8.6 GB on RTX 4090 for 1,737 context tokens and 10 generated tokens. | Plausible 16 GB experiment after quantization verification; published measurement excludes our simulator and is not a 5070 Ti result. |
| NavFoM | Cross-embodiment trajectory predictor; project shows quadruped, wheeled, UAV and vehicle tasks. | Official deployment uses a remote RTX 5090. Checked official page links only a paper, demonstrations and website resources; no runnable model/checkpoint release was established. | Watch list; not an immediately reproducible replacement. |
| Qwen-RobotNav | Qwen3-VL-based navigation; eight `(x, y, theta)` waypoints, task-dependent visual history. Report describes 2B–8B scaling. | Official README explicitly says there is currently no plan to release model weights. | Exclude from immediate local testing. |

The Chinese-navigation acceptance requirement is not established by the checked
candidate papers/cards. A multilingual VLM backbone alone does not establish
Chinese action-following after navigation fine-tuning. NaVILA's spatial action
representation also does not establish accurate stopping after a user-requested
3 m move: its paper describes fixed command velocities and corresponding
execution durations. Closed-loop distance/stop accuracy needs a direct test.

## Source pins, licenses and original entry points

All commit pins below were read from the canonical GitHub API on the survey
date; they are inspected revisions, not newly imported source snapshots.

### InternVLA-N1 / InternNav

- [Repository](https://github.com/InternRobotics/InternNav), branch `main`,
  commit `7a5c62400ac45b313d9b709c740b64191556a242`.
- Code: MIT. The [DualVLN card](https://huggingface.co/InternRobotics/InternVLA-N1-DualVLN)
  displays CC BY-NC-SA 4.0 in a badge, while structured license metadata is
  missing. Treat model terms separately from the code license.
- Checkpoint revision: `a698a9e898b4001621a319e1bc89f02ec715cc86`;
  [HF metadata](https://huggingface.co/api/models/InternRobotics/InternVLA-N1-DualVLN)
  reports 8,383,538,891 BF16 parameters and `gated: false`.
- [Paper](https://arxiv.org/html/2512.08186v1), submitted 2025-12-09;
  repository identifies the work as ICLR 2026. Section 5.2 supplies the 20 GB
  deployment evidence. The RGB model card does not imply the complete real
  robot pipeline is depth/odometry-free: deployment streams RGB-D and uses
  odometry with an MPC tracker.
- [Installation](https://internrobotics.github.io/user_guide/internnav/quick_start/installation.html)
  provides an isolated Python 3.10 model server; original server entry point:
  `python scripts/eval/start_server.py --port 8087`.
- [Evaluation](https://internrobotics.github.io/user_guide/internnav/quick_start/evaluation.html)
  and [inference notebook](https://github.com/InternRobotics/InternNav/blob/7a5c62400ac45b313d9b709c740b64191556a242/scripts/notebooks/inference_only_demo.ipynb)
  are available. The notebook pins Torch 2.6 / cu124 and Transformers 4.51;
  the installation page uses a different older Torch/CUDA recipe. Neither
  recipe was validated here on Blackwell. The notebook's approximate 8 GB
  checkpoint-size sentence should not replace HF parameter metadata or the
  paper's runtime memory measurement.
- Datasets include InternData-N1 and VLN-CE benchmarks; code README assigns
  InternData-N1 CC BY-NC-SA 4.0 and preserves other datasets' original terms.

### NaVILA

- [VLA repository](https://github.com/AnjieCheng/NaVILA), branch `main`,
  commit `76b98f233dd0fff05dfcd69435eec6740febff9d`; Apache-2.0 code.
- [Checkpoint](https://huggingface.co/a8cheng/navila-llama3-8b-8f), revision
  `b2294e96581454468d6b94f38201f4f965ef48b7`, publicly listed and not gated;
  model card/license metadata absent in the checked API response. A released,
  ready-to-load AWQ checkpoint was not verified.
- [Paper v2](https://arxiv.org/html/2412.04453v2), revised 2025-02-17;
  original submission 2024-12-05. Quantization figures are from Table XIII,
  not our measurement. Quantized R2R SR is 48.2 versus FP16 49.7 in that table.
- Original Habitat evaluation: Python 3.10, Habitat-Lab/Sim 0.1.7, VILA,
  Transformers 4.37.2, FlashAttention 2.5.8; example
  `bash scripts/eval/r2r.sh CKPT_PATH 1 0 "0"`. These older dependencies
  require compatibility checks on the 5070 Ti.
- [Dataset annotations](https://huggingface.co/datasets/a8cheng/NaVILA-Dataset)
  cover navigation and human video data. README states raw videos/images are
  not redistributed because of copyright restrictions.
- [Locomotion code](https://github.com/yang-zj1026/legged-loco), `main`,
  commit `87b0d3d18404e784abc0a62227bc41c940f29ecc`, MIT; Go2/H1, Isaac Sim
  4.1.0 and a modified Isaac Lab 1.1.0. Example playback command:
  `python scripts/play.py --task=go2_base_play --history_len=9 --load_run=RUN_NAME --num_envs=10`.
- [Isaac benchmark](https://github.com/yang-zj1026/NaVILA-Bench), `main`,
  commit `e9d2db12ce5788c0f987d734c0094100b6bc0d3a`; GitHub API reports
  `NOASSERTION` for license classification, so inspect its actual license
  before acquisition. It targets Isaac Sim 4.1.0 / Isaac Lab 1.1.0. The public
  code links establish availability, not a reproduced Go2 deployment here.

### Deferred candidates

- NavFoM [paper](https://arxiv.org/abs/2509.12129),
  [official project](https://pku-epic.github.io/NavFoM-Web/),
  [website repository](https://github.com/PKU-EPIC/NavFoM-Web): branch `main`,
  commit `ea53082af068cc49485b6ad78b21eefdb75f660a`, no repository license
  detected. This pin identifies website assets, not model source. Dependencies,
  model/data license, checkpoints and executable demo command remain unknown.
  Follow-up verification of [paper v2](https://arxiv.org/html/2509.12129v2)
  found an internal hardware inconsistency: Section 4.1 specifies RTX 4090,
  while Appendix A.4 and the project page specify RTX 5090. Section 4.1 reports
  at most 0.5 s to generate eight waypoints at a 1,600-token budget and describes
  asynchronous observation upload during action execution. This is not a
  measured Internet round-trip latency. The checked paper/project page do not
  specify the transport protocol, wireless access, server distance or timeout
  handling; NaVILA's separately published TCP protocol must not be attributed
  to NavFoM.
- Qwen-RobotNav [official repository/report overview](https://github.com/QwenLM/Qwen-RobotNav):
  branch `main`, commit `f74cf1f6079300aee6e40e03858da2f98b1b7261`; no
  repository license detected. It contains report resources; no public model
  runtime dependency set or downloadable checkpoint was established.

## Comparison and next-test boundary

Do not compare InternNav R2R/RxR success rates directly with TIC-VLA DynaNav
success rates: scenes, goal tolerances, actions, controllers and evaluation
protocols differ. Candidate selection does not establish improvement. A useful
comparison should share recorded inputs for open-loop Chinese/English probes,
then share simulator starts and termination criteria for closed-loop tests.
Score landmark completion, collisions, path/forward displacement, and actual
low-speed dwell near the requested stopping distance separately.

This survey downloaded no model weights, cloned no source, and ran no new
model or simulator. Existing TIC-VLA experiment artifacts remain the local
evidence source for the preceding tests; candidate runtime claims remain open.
