# Navigation VLA selection without a GPU constraint

Date: 2026-09-08. Stage: planning. Status: `surveyed`.

## Recommendation

For Dr Sun's remote inference, simulation-video, and eventual Lite3 navigation
use case, prioritize **InternVLA-N1 DualVLN**, using its released BF16 weights
before introducing quantization. This is an engineering recommendation based
on inspectable release artifacts and integration references, not an independent
performance ranking or a claim that this is the newest navigation paper.

The model repository publicly lists four weight shards; its API reports
8,383,538,891 BF16 parameters and `gated: false`. The official evaluation guide
documents both Habitat and Isaac Sim closed-loop evaluation, including a
separate agent-server process. InternNav also links Go2 deployment references.
Those references cover different InternNav configurations and do not establish
that the exact DualVLN checkpoint works on Lite3 without adaptation.

Sources: [model](https://huggingface.co/InternRobotics/InternVLA-N1-DualVLN),
[evaluation](https://internrobotics.github.io/user_guide/internnav/quick_start/evaluation.html),
[repository](https://github.com/InternRobotics/InternNav),
[community Go2 guide](https://github.com/cmjang/InternNav-deploy).

## Release and reproduction comparison

| Candidate | Date anchor | Public evidence inspected | Reproduction decision |
| --- | --- | --- | --- |
| InternVLA-N1 DualVLN | Paper submitted 2025-12-09; ICLR 2026; toolbox v0.3.0 announced 2026-01 | Model weights, training/evaluation documentation, model server, Habitat/Isaac evaluation, and robot deployment references | Preferred full-system reproduction candidate for this use case |
| NaVILA | Original paper 2024-12; RSS 2025 | Released VLA source/weights and separate locomotion/Isaac benchmark repositories; existing local quantized task is in review | Retain as a comparison baseline; remove the 16 GB constraint as a selection driver |
| OmniNav | Paper 2025-09; slow-fast OVON checkpoint announced 2026-02 | Training code, Habitat inference, ModelScope checkpoint links, Docker instructions | Useful simulation comparison; the checked README does not provide an equally direct Lite3/Go2 deployment path |
| ABot-N1 | Paper submitted 2026-07-11, revised 2026-07-17 | Official project links ABotN-Bench and an HF paper page. Repository defaults to the benchmark branch; public evaluation code and datasets are available | Newer frontier reference; a complete N1 inference-code-and-weights release was not established by this inspection |
| Qwen-RobotNav | Technical report 2026-06 | Official README explicitly states no current plan to release weights | Not an immediately deployable open-weight candidate |
| NavFoM | Paper 2025-09; ICLR 2026 | Existing same-day survey and fresh website-repository pin; no model-runtime release established | Keep on the watch list; website assets are not model code |

Primary links: [DualVLN paper](https://arxiv.org/abs/2512.08186),
[NaVILA](https://github.com/AnjieCheng/NaVILA),
[OmniNav](https://github.com/amap-cvlab/OmniNav),
[ABot-N1 paper](https://arxiv.org/abs/2607.10383),
[ABot-N1 project](https://amap-cvlab.github.io/ABot-Navigation/ABot-N1/),
[ABotN-Bench](https://github.com/amap-cvlab/ABot-Navigation/tree/ABotN-Bench),
[Qwen-RobotNav](https://github.com/QwenLM/Qwen-RobotNav),
[NavFoM](https://pku-epic.github.io/NavFoM-Web/).

This is a bounded selection survey, not an exhaustive claim about the newest
paper worldwide. Publication date, checkpoint release date, and repository
maintenance date are distinct. Cross-paper success rates are not ranked here
because the control and evaluation protocols differ.

## Inspected revisions and license boundaries

| Repository | Branch | Commit | Code-license evidence |
| --- | --- | --- | --- |
| InternRobotics/InternNav | main | `7a5c62400ac45b313d9b709c740b64191556a242` | MIT |
| AnjieCheng/NaVILA | main | `76b98f233dd0fff05dfcd69435eec6740febff9d` | Apache-2.0 |
| amap-cvlab/OmniNav | main | `1e25dc384f3030e89fd609bf6c9fb6005df0d216` | GitHub API has no detected license; not resolved here |
| amap-cvlab/ABot-Navigation | ABotN-Bench | `2a0aefb56f1e2d315bba924239e9e8ad9dca9d92` | README states Apache-2.0, with separate 3DGS terms for renderer; API has no detected license |
| QwenLM/Qwen-RobotNav | main | `f74cf1f6079300aee6e40e03858da2f98b1b7261` | API has no detected license |
| PKU-EPIC/NavFoM-Web | main | `ea53082af068cc49485b6ad78b21eefdb75f660a` | API has no detected license; website only |

InternVLA-N1 DualVLN checkpoint revision:
`a698a9e898b4001621a319e1bc89f02ec715cc86`.
Code licenses do not substitute for model and dataset terms. The earlier
[same-day survey](2026-09-08_navigation_vla_alternatives_upstream_survey.md)
records the checkpoint-card and dataset-license qualifications at this same
checkpoint revision.

Small primary-source inspection files and fresh API metadata are stored in
`2026-09-08_unconstrained_navigation_vla_sources/`, with URLs and SHA-256 hashes.
They are read-only inspection material, not an imported runnable baseline.

## Original execution entry points and adaptation boundary

The official DualVLN evaluation guide supplies:

```sh
# Model process; set checkpoint path in the config first.
python scripts/eval/start_server.py --config scripts/eval/configs/h1_internvla_n1_async_cfg.py

# Isaac client; configure use_agent_server=True.
python scripts/eval/eval.py --config scripts/eval/configs/h1_internvla_n1_async_cfg.py

# Habitat evaluation.
python scripts/eval/eval.py --config scripts/eval/configs/habitat_dual_system_cfg.py
```

The inspected server source defaults to `localhost`; its configuration can
override the CLI port. A cloud deployment must deliberately configure the
client endpoint/tunnel and version-matched dependencies. Model-only inference
does not establish compatibility with a cloud instance's simulator graphics
stack. Sensor calibration, odometry, trajectory tracking, and the Lite3
locomotion interface remain separate integration work.

Recommended validation sequence: original-precision recorded-observation
inference, bounded original simulator closed loop with a video, paired Chinese
and English instructions, and only then a separately authorized Lite3 test.
Explicitly test metric-distance stopping instead of inferring it from language
understanding. No new model weights, paid instance, training, simulator run,
or robot actuation were started in this selection task.
