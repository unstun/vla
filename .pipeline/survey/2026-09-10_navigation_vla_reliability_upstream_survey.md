---
origin: ai+primary_sources+local_experiment_records
reviewed: false
date: 2026-09-10
stage: planning
status: surveyed
---

# Navigation VLA alternatives after the LightNav–Lite3 failures

The best next full navigation-VLA comparison is **InternVLA-N1 with NavDP**,
specifically the released RGB-D configuration. The most relevant new local
navigation candidate is **X-NavDP**, which has released code and a checkpoint
and explicitly studies detours, recovery, and embodiment changes. X-NavDP is
not language-conditioned: it needs a separate source of geometric goals.

Neither is established as more reliable than LightNav on Lite3. These are
reproduction priorities based on inspected mechanisms and artifacts, not a
validated ranking. Published VLN success rates do not cover our combination of
exact distance commands, target identity, physical contacts, and native stopping.
LightNav itself reports higher R2R/RxR success than several candidates in this
survey, so replacing it solely on a paper leaderboard would not follow the evidence.

## Scope and method

Checked 19 GitHub repository endpoints, including companion controllers and
benchmarks: 18 resolved to an exact revision; ReflectVLN returned HTTP 404 from
the live GitHub API despite a searchable cached page. Also checked official
papers/project pages, eight Hugging Face model metadata records, five current
GitHub issue lists, and selected issue comments and implementation files.
The initial NaVILA issue query covers the latest 30 items, not its entire history.

Selection criteria are: downloadable and identifiable checkpoints; actual
navigation inference/evaluation code; obstacle handling during execution;
termination semantics; sensor and locomotion compatibility; RTX 4090 feasibility;
and evidence for recovery, Chinese instructions, and metric movement. Stars and
README superlatives are not reliability evidence. Manipulation-only OpenVLA,
SmolVLA, and GR00T checkpoints are not interchangeable Lite3 navigation policies.

Small primary-source inspection copies, API responses, URLs, and SHA-256 records
are in [the source folder](2026-09-10_navigation_vla_reliability_sources/).
No repository was cloned, model weight downloaded, upstream code executed, GPU
job launched, or robot command sent in this survey. Inspection copies are not
an imported runnable baseline. Existing experiment files were only read.

## Recommended candidates

| Priority and role | Candidate | Why it is relevant | What prevents a reliability claim |
|---|---|---|---|
| First full VLA comparison | [InternVLA-N1 with NavDP](https://huggingface.co/InternRobotics/InternVLA-N1-w-NavDP) | Language/pixel-goal reasoning plus a separate RGB-D trajectory policy; released weights, real-world client, simulator configurations, and a velocity-control seam | Different checkpoint from our DualVLN trial; learned avoidance, not an independent collision guarantee; Lite3 adaptation and Chinese/metric tests remain necessary |
| First new local-policy experiment | [X-NavDP](https://github.com/InternRobotics/NavDP/tree/bff5eb8857f50e082243fb455d312409daabc3aa/baselines/x-navdp) | RGB-D point-goal policy; RL for recovery and heterogeneous robots; public post-trained weights and quadruped evaluation | No language input; Go2/G1/Dingo rather than Lite3; contact penalties do not impose a runtime collision veto; released wrapper contains recovery heuristics |
| Legged whole-system reference | [NaVILA](https://github.com/AnjieCheng/NaVILA) + [legged-loco](https://github.com/yang-zj1026/legged-loco) | Mid-level spatial actions with a separate perception-aware locomotion controller and physical Isaac benchmark | Its avoidance benefit depends on that lower controller; our existing Lite3 walking export does not inherit it. English-only training; older dependencies and unresolved deployment reports |
| Explicit local risk response reference | [ViPlanner](https://github.com/leggedrobotics/viplanner) | Depth/semantic local paths and a learned risk signal that changes the published path | Not a VLA; learned risk can be wrong; ROS1 and robot/controller integration remain work |
| Existing controls, not newly validated winners | [TIC-VLA](https://github.com/ucla-mobility/TIC-VLA), [OmniVLA](https://github.com/NHirose/OmniVLA) | Already have local inference or simulator evidence; useful to separate integration changes from model changes | Our existing results do not establish exact distance stopping or Lite3 obstacle safety; TIC-VLA has an unresolved training reproduction report |

### InternVLA-N1: choose the exact variant

The freshly retrieved configurations distinguish two releases:

- `InternVLA-N1-w-NavDP`: revision `6d48df24da45e8b31fdcef9572bbcbf68c0baf64`,
  `system1=navdp_async`, `torch_dtype=bfloat16`; HF reports 8,388,561,894 BF16 parameters.
- `InternVLA-N1-DualVLN`: revision `a698a9e898b4001621a319e1bc89f02ec715cc86`,
  `system1=nextdit_async`, `torch_dtype=bfloat16`; HF reports 8,383,538,891 BF16 parameters.

They are not alternate names for the same deployed checkpoint. The inspected
real-world client sends synchronized RGB and depth and uses odometry; the agent
feeds two RGB/depth observations into System 1. Its output is a trajectory,
tracked through a velocity interface. Do not infer the real-world sensor contract
from an RGB-only benchmark label.

The DualVLN paper reports approximately 20 GB on RTX 4090 for the complete model.
That is useful feasibility evidence for this family, not a measured footprint
for our proposed w-NavDP configuration plus simulator. More concerning, its
Social-VLN table reports **35.4% human collision rate**, compared with 36.4% for
StreamVLN. It is a useful comparison candidate, not evidence that the safety
problem is solved. [Paper, Table 3 and §5.2](https://arxiv.org/html/2512.08186v1).

Code is MIT. The three InternVLA model cards display a CC BY-NC-SA 4.0 badge,
while HF structured license metadata is missing. Dataset terms are separate.

Sources: [w-NavDP config](https://huggingface.co/InternRobotics/InternVLA-N1-w-NavDP/blob/6d48df24da45e8b31fdcef9572bbcbf68c0baf64/config.json),
[DualVLN config](https://huggingface.co/InternRobotics/InternVLA-N1-DualVLN/blob/a698a9e898b4001621a319e1bc89f02ec715cc86/config.json),
[real-world agent](https://github.com/InternRobotics/InternNav/blob/7a5c62400ac45b313d9b709c740b64191556a242/internnav/agent/internvla_n1_agent_realworld.py#L127-L160),
[client](https://github.com/InternRobotics/InternNav/blob/7a5c62400ac45b313d9b709c740b64191556a242/scripts/realworld/http_internvla_client.py).

### X-NavDP: strongest new lead for the failure we observed

The authors report a matched Go2 simulation improvement from **55.78% to 79.85%**
SR over NavDP; overall simulation SR rises from 61.20% to 84.28%. These are their
point-goal evaluations, not language navigation or comparisons against LightNav.
The paper explicitly says collisions affect reward but do not directly end
training episodes. [Official results](https://yty-sky.github.io/x-navdp-project-page/#results),
[paper, Appendix B](https://arxiv.org/html/2607.28560v1).

Release audit:

- Original X-NavDP subdirectory code has an **MIT** license. The parent NavDP
  README states CC BY-NC-SA 4.0; dependency terms must be assessed by component.
- HF revision `7cee38a8d8308874d2b8488783c612f42060ac41` is not gated and lists
  `x-navdp_posttrain.ckpt` (873,100,357 bytes), `navdp_pretrain.ckpt`, controller
  checkpoints and robot assets. This verifies listing and identity metadata,
  not downloaded payload hashes or loadability. HF does not declare a structured
  model license; its card's MIT wording refers to original code.
- The release README says the supplied checkpoint was trained for 24,000 steps
  on **72 scenes**; paper v1's main training description uses **56 scenes**.
  Exact release-to-paper parity needs clarification before claiming reproduction
  of the paper numbers.
- Interface: RGB-D, local geometric goal, embodiment ID, and optional pose
  guidance; output is candidate trajectories and learned Q values. The policy
  ranks candidates with the mean of two critics. This is learned trajectory
  scoring, not geometric clearance certification.
- The evaluated wrapper samples a random candidate when stuck and schedules a
  **1.5-second sleep** on a direction inconsistency. These behaviors matter for
  latency and safety testing; source availability does not establish runtime quality.
- Documented stack: Python 3.11, Isaac Sim 5.0.0, Isaac Lab package 0.46.2,
  `isaaclab-rl==0.4.0`, and acados. Exact 4090 runtime memory is unmeasured here.

Original bounded-evaluation entry points are
`bash eval/scripts/start_policy_server.sh --checkpoint checkpoints/x-navdp_posttrain.ckpt --embodiment quadruped`
and `bash eval/scripts/run_evaluation.sh --config_file eval/config/eval_pointgoal/quadruped_clutter_easy.yaml`.
The README provides episode/step limits; a future run also needs a wall supervisor.

Sources: [release README](https://github.com/InternRobotics/NavDP/blob/bff5eb8857f50e082243fb455d312409daabc3aa/baselines/x-navdp/README.md),
[HF payload listing](https://huggingface.co/InternRobotics/X-NavDP/tree/7cee38a8d8308874d2b8488783c612f42060ac41),
[inference wrapper](https://github.com/InternRobotics/NavDP/blob/bff5eb8857f50e082243fb455d312409daabc3aa/baselines/x-navdp/eval/src/policy_agent.py#L468-L548),
[critic selection](https://github.com/InternRobotics/NavDP/blob/bff5eb8857f50e082243fb455d312409daabc3aa/baselines/x-navdp/eval/src/policy_network_embodiment.py#L449-L458).

### NaVILA: preserve the source of its avoidance capability

Its physical Go2 ablation reports SR of **50.2% with perception-aware locomotion
versus 36.2% with blind locomotion**. The mid-level VLA alone does not produce
that benefit. The low-level system uses LiDAR/height information, unlike the
proprioceptive input of our selected Lite3 `model_149999` controller.
[Paper, Table IV](https://arxiv.org/html/2412.04453v2).

The owner explicitly confirms English-only training in [issue #30](https://github.com/AnjieCheng/NaVILA/issues/30).
Open issues [#44](https://github.com/AnjieCheng/NaVILA/issues/44) and
[#57](https://github.com/AnjieCheng/NaVILA/issues/57) report spinning/non-stopping
and poor Go2 instruction following. These are unresolved user reports, not
controlled proof that the official configuration fails.

Code is Apache-2.0; legged-loco is MIT. The official 8B HF checkpoint is public,
but its card/explicit license was absent at the inspected revision. The existing
local NF4 export passed inference/reload, not navigation. The paper's AWQ result
and our NF4 runtime must remain distinct. Native FP16 or the existing NF4 route
can be compared on 4090, with a separate simulator memory check.

### ViPlanner: inspectable risk response, not a hard safety guarantee

The ROS planner reads depth/semantic observations and predicts both waypoints
and `fear`. At `fear > 0.7`, it can mark planning as failed and publish only the
first pose as the main path, retaining the full path on a risk-visualization
topic. That is a concrete response missing from the LightNav demo tracker.
Whether the downstream controller physically stops still requires an integration
test. Code is BSD-3-Clause; ROS1 and external segmentation/checkpoint dependencies
add porting cost. It supplies local planning, not language understanding.
[Risk logic](https://github.com/leggedrobotics/viplanner/blob/6fcf3c60f6fa3b28b3a11af054d6033825923789/ros/planner/src/viplanner_node.py#L284-L297),
[path publication](https://github.com/leggedrobotics/viplanner/blob/6fcf3c60f6fa3b28b3a11af054d6033825923789/ros/planner/src/viplanner_node.py#L571-L579).

## Wider screening and exclusions

| Candidate | Fresh release evidence | Decision |
|---|---|---|
| [LoGoPlanner](https://github.com/InternRobotics/NavDP/tree/bff5eb8857f50e082243fb455d312409daabc3aa/baselines/logoplanner) | Public metric-geometry policy and LeKiwi deployment instructions; HF weights are gated (`gated=auto`, anonymous card fetch returned 401); model metadata declares CC BY-NC-SA 4.0 | Strong coordinate-navigation research lead. Not a language model; access, metric drift, and Lite3 tracking remain unresolved. Authors acknowledge imperfect real-world reconstruction |
| [OmniNav, Amap](https://github.com/amap-cvlab/OmniNav) | Actual training/evaluation code; visual and slow-fast OVON ModelScope checkpoint links; Habitat versions differ by task | Secondary simulation comparator; no equally direct Lite3 control path or root license found. Do not confuse with the different September 2026 paper also named OmniNav |
| [TIC-VLA](https://github.com/ucla-mobility/TIC-VLA) | Model and DynaNav code/checkpoint released; UCLA Academic Software License | Keep as existing latency-aware baseline. [Issue #11](https://github.com/ucla-mobility/TIC-VLA/issues/11) reports a Stage-2 reproduction gap with no reply at inspection; not independently reproduced by this survey |
| [OmniVLA](https://github.com/NHirose/OmniVLA) | Original and edge checkpoints; MIT code and edge-card metadata; existing local inference evidence | Keep as control. No new evidence establishes an independent obstacle safety layer or accurate meter stopping |
| [ABot-N0/N1](https://github.com/amap-cvlab/ABot-Navigation) | Branches are ABot-N0, ABotN-Bench and webpage. Default is benchmark code; N0 README is a report overview. N1 project/paper exist | Frontier reference; complete public N1 inference-plus-weight chain not established. Benchmark code is not the N1 policy |
| [Qwen-RobotNav](https://github.com/QwenLM/Qwen-RobotNav) | README explicitly says there is currently no plan to release weights | Exclude from immediately deployable open-weight options |
| [NavFoM](https://github.com/PKU-EPIC/NavFoM-Web) | Resolved website revision and inspected index.html; no runnable checkpoint release established | Watch list, not deployable candidate |
| [VLingNav](https://github.com/wsakobe/VLingNav-web) | Website repository; [artifact-release request #1](https://github.com/wsakobe/VLingNav-web/issues/1) remains open | No verified runnable checkpoint chain |
| [MobileVLA-R1](https://github.com/AIGeeksGroup/MobileVLA-R1) | Code changed September 8; old placeholder-data finding is stale. Actual HF archive parts exist | Defer: [issue #9](https://github.com/AIGeeksGroup/MobileVLA-R1/issues/9) alleges released weights match NaVILA and omit additional modalities; no reply. This survey did not download/re-hash the archive and does not establish that allegation as fact |
| [Uni-NaVid](https://github.com/jzhzhang/Uni-NaVid) | Released inference/benchmark implementation and checkpoint links | Secondary RGB navigation baseline; no specific evidence of stronger Lite3 obstacle reliability |
| [VLFM](https://github.com/rai-opensource/vlfm) | Released modular semantic navigation; MIT main code; README says not actively maintained | Useful semantic-navigation baseline, not a new end-to-end VLA; legacy stack |
| [X-Mobility](https://github.com/NVlabs/X-MOBILITY) / [COMPASS](https://github.com/NVlabs/COMPASS) | Official Apache-2.0 implementations, Docker/export/ROS2 paths; X-Mobility pretrained checkpoint links; COMPASS offers residual RL adaptation | Relevant mobility/control alternatives, not language-conditioned VLA replacements. COMPASS adaptation would introduce a separate training project |
| [ReflectVLN](https://github.com/AIprogrammer/ReflectVLN) | Search cache advertises a model, but fresh canonical API returns 404 | Availability unverified; exclude until a live canonical release resolves |
| [Robostral Navigate](https://mistral.ai/news/robostral-navigate/) | Official model announcement/report; no public download/runtime path established in inspected official sources | Frontier reference, not an immediately reproducible GitHub option |
| [NavMCP](https://arxiv.org/html/2608.30396v1) | Agent/executor research; appendix says Qwen-RobotNav and Qwen3.6-Plus use hosted APIs | Interesting orchestration, not a downloadable replacement checkpoint; do not confuse with unrelated navmcp packages |

The new X-NavDP and LoGoPlanner leads are additions to the September 8 survey.
MobileVLA-R1 was refreshed rather than rejected using its old placeholder link.
No code/model combination inspected establishes both Chinese navigation and
precise user-specified displacement on Lite3.

## Local evidence that must remain separate

- [LightNav capability probes](../experiments/2026-09-09_lightnav0_official_demo_rented4090/lite3_capabilities_v1/README.md): eight single-shot Lite3 cases, all four numeric-distance cases failed the declared tolerance, and neither blocked case demonstrated contact-free detouring.
- [DualVLN Chinese chair trial](../experiments/2026-09-08_dualvln_rented4090/public_scenes/requests/2026-09-09_zh_between_two_chairs/review/LEAD_REVIEW.md): approached a pair and emitted STOP; geometric between-the-chairs success was unscored. This was not the w-NavDP checkpoint.
- [DualVLN official reproduction review](../experiments/2026-09-08_dualvln_rented4090/review/OFFICIAL_REPRODUCTION_LEAD_REVIEW.md): no official episode ran in that attempt because of data/environment blockers. Do not replace this with the custom-trial result.
- [TIC-VLA compatibility result](../experiments/2026-09-08_tic_vla_dynanav_5070ti/RESULT.md): one hospital episode met the benchmark's 1.5 m condition with zero reported collision indicators; evaluator termination did not prove native learned STOP.
- [NaVILA NF4 probe](../experiments/2026-09-08_navila_8b_quantized_5070ti/README.md): CUDA inference and export/reload only.

These older local records were read for scope and interpretation; no remote
runtime state was refreshed or new comparative run performed.

## Proposed acceptance experiment

Use two comparisons so that adding sensors or a better controller does not get
misreported as a better VLA checkpoint:

1. **Local execution:** keep Lite3 and `model_149999` fixed. Compare the existing
   navigation baseline, the present LightNav path tracker, and X-NavDP under
   matched starts/goals. Supply and label RGB-D where required. Include a tall
   non-traversable box, a narrow passage, a dead end, and a moving obstacle.
2. **Language and goal completion:** compare LightNav, the exact InternVLA-N1
   w-NavDP release, and the existing DualVLN variant on matched tasks. Include
   ambiguous bins, paired Chinese/English text, and 1/2/3 m requests. Translation
   is an explicit extra condition, never silently inserted.

Score native STOP, target identity, final distance and stationary dwell,
contacts, minimum clearance, falls, timeout, and every external intervention
separately. Retain failed attempts. Start with a small bounded screen, then
repeat surviving conditions at least ten times across varied starts; ten trials
is still a screening sample, not a safety validation campaign. A protective
controller stopping a bad proposal does not convert the model's task into success.

For an operational stack, geometric collision checks and odometry-based metric
execution should have authority to stop the robot independently of language
generation. Those engineering protections and native model competence require
separate acceptance results. This survey recommends the next candidates; it
does not authorize new training or real-robot motion.

## Inspected repository revisions

The table below is generated from saved live API records. API license labels
are only discovery metadata: the component-specific findings above take
precedence. Commit dates identify the inspected head, not the date of the last
substantive algorithm change. No repository here was found archived at lookup.

| Repository | Branch | Inspected commit | Head date (UTC) | API license |
|---|---|---|---|---|
| [InternRobotics/InternNav](https://github.com/InternRobotics/InternNav) | main | `7a5c62400ac45b313d9b709c740b64191556a242` | 2026-03-10 | MIT |
| [InternRobotics/NavDP](https://github.com/InternRobotics/NavDP) | master | `bff5eb8857f50e082243fb455d312409daabc3aa` | 2026-09-07 | not detected |
| [AnjieCheng/NaVILA](https://github.com/AnjieCheng/NaVILA) | main | `76b98f233dd0fff05dfcd69435eec6740febff9d` | 2025-08-20 | Apache-2.0 |
| [yang-zj1026/legged-loco](https://github.com/yang-zj1026/legged-loco) | main | `87b0d3d18404e784abc0a62227bc41c940f29ecc` | 2024-12-15 | MIT |
| [yang-zj1026/NaVILA-Bench](https://github.com/yang-zj1026/NaVILA-Bench) | main | `e9d2db12ce5788c0f987d734c0094100b6bc0d3a` | 2025-08-28 | NOASSERTION |
| [NHirose/OmniVLA](https://github.com/NHirose/OmniVLA) | main | `5182600cb4a9ee07684e17cdd2a6cbafc56b8a68` | 2026-03-25 | NOASSERTION |
| [ucla-mobility/TIC-VLA](https://github.com/ucla-mobility/TIC-VLA) | main | `9fa6f8b66b9e121d5df5df071297bba8e5353ebb` | 2026-07-09 | NOASSERTION |
| [amap-cvlab/OmniNav](https://github.com/amap-cvlab/OmniNav) | main | `1e25dc384f3030e89fd609bf6c9fb6005df0d216` | 2026-08-15 | not detected |
| [amap-cvlab/ABot-Navigation](https://github.com/amap-cvlab/ABot-Navigation) | ABotN-Bench | `2a0aefb56f1e2d315bba924239e9e8ad9dca9d92` | 2026-08-05 | not detected |
| [QwenLM/Qwen-RobotNav](https://github.com/QwenLM/Qwen-RobotNav) | main | `f74cf1f6079300aee6e40e03858da2f98b1b7261` | 2026-06-30 | not detected |
| [PKU-EPIC/NavFoM-Web](https://github.com/PKU-EPIC/NavFoM-Web) | main | `ea53082af068cc49485b6ad78b21eefdb75f660a` | 2025-10-22 | not detected |
| [leggedrobotics/viplanner](https://github.com/leggedrobotics/viplanner) | main | `6fcf3c60f6fa3b28b3a11af054d6033825923789` | 2025-02-12 | NOASSERTION |
| [rai-opensource/vlfm](https://github.com/rai-opensource/vlfm) | main | `584ed56008754fde7997d904983607def8328322` | 2025-01-07 | MIT |
| [jzhzhang/Uni-NaVid](https://github.com/jzhzhang/Uni-NaVid) | main | `79ef5ea3fea14c205342d1ab070563d84c7a966a` | 2025-12-15 | MIT |
| [AIprogrammer/ReflectVLN](https://github.com/AIprogrammer/ReflectVLN) | unresolved | `HTTP 404` | unknown | not detected |
| [AIGeeksGroup/MobileVLA-R1](https://github.com/AIGeeksGroup/MobileVLA-R1) | main | `689cc0d0dc4af3bb40bdc6da9e1fbc390cd9e30e` | 2026-09-08 | Apache-2.0 |
| [wsakobe/VLingNav-web](https://github.com/wsakobe/VLingNav-web) | main | `778ba7331e99651542f2e8fffe84155242cf34e5` | 2026-01-14 | not detected |
| [NVlabs/X-MOBILITY](https://github.com/NVlabs/X-MOBILITY) | main | `5837aead8902a2f4afdeb372548c45a6b0f8d69b` | 2026-02-10 | Apache-2.0 |
| [NVlabs/COMPASS](https://github.com/NVlabs/COMPASS) | main | `8060f7ccb126b364707d52db3bab016f01547890` | 2026-06-26 | Apache-2.0 |

ABot-N0 branch additionally inspected at `77ceab459a801f48d186b360604eca7a7dd95811`.
