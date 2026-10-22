---
origin: ai_only
reviewed: false
---

# Literature And Upstream Index

## 2026-10-22: 50 recent open-source repositories plus six supplementary references

Dr Sun requested at least 50 additional recent open-source repositories.
[The acquisition survey](../survey/2026-10-22_recent_navigation_50_upstream_survey.md)
records 50 newly acquired canonical repositories with default-branch commits
since 2026-04-22, plus six separately labelled older references. All 56 are
deduplicated against 361 prior reference/survey identities; source checkouts,
commit pins, license evidence, entry points and file-integrity records are local.
[The Chinese catalogue](../../references/upstream/2026-10-22_recent_navigation_50/comparison.md)
groups navigation/control, terrain/locomotion, mapping, VLN and evaluation.
Two source-empty repositories, one binary-only core release and one conflicting
license declaration are excluded from the count. Status: imported only; no
upstream program, simulation or physical experiment was run. Baseline unchanged.

## 2026-10-09: Navigation qualification across 18 repositories

[Qualification survey](../survey/2026-10-09_navigation_qualification_upstream_survey.md)
inspects 15 implementations/frameworks and 3 benchmarks with pinned source
references and primary evaluation protocols. It finds no shared 30 Hz / 60 ms /
zero-failed-round acceptance rule. Our native v114 solver has measured
millisecond-scale ordinary rounds; comparative mission reliability remains
ungraded, with a recorded failed episode and unresolved freshness/recovery
coupling. The project's sustained-30-Hz requirement is unchanged. Status:
`surveyed` only; no new upstream execution or performance ranking.

> ⚠ [未门控] Codex CLI 0.153.3 在当前沙箱初始化 app-server 时返回 Operation not permitted，未产生独立核查结论。主会话已核对摘要、实测字段、视频 SHA 和未实施方案边界；reviewed: false 保留。

## 2026-10-01: SCAN-Planner frequency source check

[SCAN-Planner, arXiv 2606.19555v1](https://arxiv.org/html/2606.19555v1)
was inspected for Dr Sun's local-rate question. The paper describes real-time
Jetson Orin NX operation but does not report fixed local replanning Hz or a
measured 30 Hz trajectory-update result. At author-code pin
`348e8a590a50a5a6bbab8d8c6dcfd171f009be26` (Apache-2.0), FSM/safety/controller
timers are 100/20/100 Hz; nominal trajectory generation is displacement/state/
safety triggered. Timer settings are not achieved trajectory rates. Status of
this source check: `surveyed`, not a new upstream reproduction. See the
[frequency survey](../survey/2026-10-01_scan_planner_frequency.md) for primary
paper/code links and the inspected previous-trajectory initialization branch.
The [Newton timing archive](../experiments/2026-10-01_newton_nav2_timing_archive.md)
separately records our failed full-stack 30 Hz/1:1 targets and delivered video.

## 2026-09-26: Newton LiDAR self-occlusion and bridge handling

Dr Sun required GitHub source inspection before problem-specific workarounds.
See `../survey/2026-09-26_newton_lidar_bridge_upstream_survey.md` for pinned
Robotec RGL, MuJoCo, Livox, Newton, Warp, newton_ros and MAVROS source mappings.
The local sensor adapter follows sensor-owner exclusion while preserving other
robot/external occlusion and refitting the actual animated human mesh. The
analytic/native-MuJoCo and skin controls passed in
`../experiments/2026-09-26_newton_stair_reproduction/runs/lidar_upstream_contract_v2/`.
This qualifies one geometric sensor condition, not RTX parity or stair
navigation. A narrow BSD MAVROS filter port now passes extracted-C++ parity and
live Mac/Linux tests. rclpy/Docker issue comparisons support the standard
single-threaded executor and pinned PyZMQ complete-message state transfer;
the original graph is integrated in a bounded local run, which fails navigation
on timeout. `newton_ros` remains surveyed only. The survey records all pins,
licenses, direct controls and the next trajectory-timing diagnosis.

## 2026-09-21: Isaac cloud vs physical MID-360

Dr Sun asked not to invent a MID-360 matcher and to check open-source
repositories first. Survey:
`../survey/2026-09-21_isaac_mid360_livox_upstream_survey.md`
(`surveyed` only; CSV not downloaded; mode not run). Ranked sources:
Livox-SDK `livox_laser_simulation` `1cce107` MIT `mid360.csv`, already
ported here as `--lidar-pattern-mode livox_mid360` via Isaac Lab
`PatternBaseCfg`; stock Isaac Lab `LidarPatternCfg` (what stand_probe
used); Isaac Sim RTX custom emitters as a different stack. Current
unmapped-box cloud remains uniform 16×2° / 12 m, not the Livox table.

## 2026-09-20: unmapped box in simulated LiDAR

Dr Sun asked to copy open-source LiDAR-target patterns instead of inventing a
Building-runner box spawn. Survey:
`../survey/2026-09-20_unmapped_obstacle_lidar_hits_upstream_survey.md`
(`surveyed` only; not imported, not reproduced). Ranked sources: Isaac Lab
v2.3.2 tag `37ddf626` MultiMeshRayCaster (sibling extra prim + string
`mesh_prim_paths`; BSD-3-Clause) and the already-pinned Lite3 fallback
`run_isaac_v12_fallback.py` `single_box` at `848b4aec` (Cuboid spawn, extra
string target, AABB pad 0.01 m). The fallback prim under `/World/ground` is
unsafe on the Building runner because `/World/ground` is already a merged
raycast target. No upstream spawn-but-omit zero-hit test was found. Task:
`.trellis/tasks/09-20-isaac-lidar-unmapped-box-hits/` (planning).

## 2026-09-17: RL policy to PD stance-hold switching

Dr Sun asked for published and open-source practice before another home-made stance-hold entry.
Survey: `../survey/2026-09-17_rl_pd_stance_hold_switch_survey.md` (surveyed only). No surveyed source
switches automatically from an RL policy to a joint-PD hold while changing gains. Code keeps the policy
gains and moves the target over 1-2 s (rl_sar Lite3, LimX), switches at a suitable moment (Disney biped
2501.05204, Safe-Stop 2609.02358), or keeps standing inside RL (GR00T WBC balance policy). Isaac Lab applies
gain changes before the delayed targets, unlike the Lite3 command packet.

## 2026-09-16: released embodied runtime alternatives

Dr Sun selected a HarnessVLN method reimplementation with Pi plus Cortex.
The active task `.trellis/tasks/09-16-emos-harnessvln-reimplementation/` is
in progress: Pi owns the sole model/tool loop, with Cortex/EMOS interfaces
behind an explicit navigation-validation layer. Pinned Pi, EMOS and
EmbodiedAgents snapshots have been acquired under
`references/upstream/2026-09-16_pi_cortex_harnessvln/`.

The first offline protocol slice passed 11 Python and 5 real-Pi-runtime tests
on the Mac and the 5070 Ti Linux host. Source equality and all 11 returned
artifacts were hash-verified. The deterministic case used 10 scripted provider
turns, two fixture movements and three intended rejections. It made zero actual
LLM calls and did not run Cortex/ROS or Habitat. See
`../experiments/2026-09-16_pi_cortex_harnessvln/RESULT.md` for the claim boundary.
This is not a HarnessVLN navigation reproduction or a real-robot result.

Dr Sun then selected Isaac Lab and the existing machine-dog-nav Lite3 stack,
with maximum supportable method fidelity and eventual physical deployment.
The Habitat-first proposal is superseded. The 79-file bridge at committed
848b4aec was exported into VLA; selected CPU checks passed 93 tests with one
ROS-dependent skip and 15 subtests. The native PCT/SCAN port's 65 file hashes
match its manifest. The canonical planner files, eight explicit Foxy adaptations
and 145 global PCT/license files are now frozen from committed upstream objects.
All eight bridge transport tests passed in the existing Foxy/rclpy container,
including the earlier skipped ROS case. A GPT-5.5/medium executor implemented
the separate P2A lifecycle core; after three lead correction requests, 37
executor tests and 21 lead tests passed locally and in actual Python 3.8.10
with source hash equality. This is bounded lifecycle acceptance, not actual
PCT/SCAN/Isaac integration. Perception/graph memory and sensor-derived
localization remain implementation work. A separate real
FAST-LIVO2 candidate was located in machine-dog; current local evidence does
not establish that it is integrated into this harness or deployment-ready.
See the task's research/isaac_backend_mapping.md and
research/fidelity_and_deployment.md for source mapping and acceptance gates.

Following the HarnessVLN/SLAM discussion, EMOS (Automatika Robotics), its
EMOS-pinned Cortex/Memory components and public Lite3 plugin, RAI, and HSGM
were inspected as practical source references. EMOS/EmbodiedAgents carry MIT
root licenses; the Lite3 plugin declares MIT in `package.xml` but has no root
license text in the inspected tree. RAI and HSGM carry Apache-2.0 root licenses.
The Lite3 plugin is a Motion Host/ROS interface, not a validated adapter for
our custom locomotion stack; localization and sensor calibration remain
integration work. RAI's ROSbot demo uses predefined room coordinates.
Exact revisions, original entry points and inspected symbols are in the
[runtime comparison](../survey/2026-09-16_embodied_harness_alternatives_upstream_survey.md).
The original comparison established `surveyed` status only. The Pi/Cortex
acquisition and offline interface results above are separate subsequent work;
the other alternatives have no new execution evidence.

## 2026-09-16: open-source work related to HarnessVLN

Follow-up on AgiBot: **HarnessVLN** is the dedicated navigation-harness paper
with AGIBOT/Nanjing/Tsinghua affiliations and A3U humanoid deployment. Its public
repository `AgibotGeneral/harnessvln` at
`b71bed50953c5f300ce2c5aeefbb18383514c11b` contains only a release-placeholder
README; implementation remains unavailable in the checked snapshot. A versioned
PDF and source checks are saved. AgiBot **Link-U OS** was separately surveyed at
`64ac7b08dd609dfb463310945856419be470315a` (Mulan PSL v2): its Alpha release is
robot communication/deployment/locomotion infrastructure, not verified evidence
of the same navigation agent harness. See the AgiBot follow-up in the
[comparison](../survey/2026-09-16_harness_vln_open_source_upstream_survey.md).

Follow-up execution: Dr Sun selected MIP, authorized MP3D download and requested
DeepSeek Harness. The pinned source is now `imported`; RTX 5070 Ti setup and a
credential-free scripted MCP/image smoke passed. After user credential setup,
one real DeepSeek episode completed: native STOP, success 0/1, oracle 0/1,
distance to goal 4.7544 m. Paper metrics remain unreproduced. See
[MIP preparation and first run](../experiments/2026-09-16_mip_5070ti/README.md).

Dr Sun subsequently narrowed the query to **agent harness research for robot-dog
navigation**. Primary-text checks identify NavMCP (Go2), Embodied Agents Take
Control / MIP (Go2), and Harness Robotic OS / Argos (Vbot) as direct references.
MIP has a checked implementation; canonical full code for NavMCP and HROS was not
established. See the scope-refinement section of the comparison linked below.
AgenticNav uses a wheeled robot and HarnessVLN uses a humanoid.

Six official implementations with checked root licenses were surveyed: HSGM,
GC-VLN, MSGNav, Embodied Agents Take Control / MIP, SG-Nav, and VLFM. See the
[dated comparison](../survey/2026-09-16_harness_vln_open_source_upstream_survey.md)
for primary paper/repository links, exact commit pins, source checks, dependencies,
original execution entries and Lite3 adaptation limits. All six have status
`surveyed` at the initial survey boundary; MIP's subsequent preparation is recorded above.
InstructNav and CA-Nav have public code but no root license found at the checked
revisions. AgenticNav's corresponding official implementation was not established.
Older recommendations below remain historical, not the current project route.

## 2026-09-09: LightNav-0 official-demo preparation

Dr Sun selected [LightNav-0](https://github.com/lightorigins/LightNav-0).
Source `d83fbfb9748ca6b497a2f2a7f4a3e95e2110e40c` is imported; the official
MuJoCo default TurtleBot case is prepared, not executed. The model revision
is `826dc5fbfa37afa8293d2e336d329b6ffc0bfb64`. See the
[dated source survey](../survey/2026-09-09_lightnav0_official_demo_upstream_survey.md)
and [session handoff](../handoffs/2026-09-09_vla_lightnav0_handoff.md).
The older survey overview below is historical and does not override this update.

> [待核查] Automated archive gate lacked the host/import context and did not
> complete successfully. Local source hashes and the saved SSH snapshot verify
> these facts; manual checks passed, but an automated PASS is not claimed.

This index records the 24 papers and 21 upstream repositories inspected in the
2026-08-16 Lite3 VLA survey. OmniVLA is the sole exception to the original
survey-only state: Dr Sun selected it, and its pinned source/checkpoints now
have imported and reproduced evidence. All other entries remain `surveyed`.

The AI-authored survey recommends OmniVLA as the first low-cost reproduction
candidate. That recommendation is not a human baseline selection. See the
[survey report](../survey/2026-08-16_lite3_vla_open_source_reproduction_survey.md)
and [local import audit](../survey/2026-08-16_lite3_vla_open_source_reproduction_survey/import_audit.md).

## Papers

| Citation key | Type | Canonical source | Pinned version | Status | Notes |
|---|---|---|---|---|---|
| Chen2025VLMPC | paper | [arXiv 2407.02666](https://arxiv.org/abs/2407.02666) | PDF SHA-256 `e838e4bf3284` | surveyed | Quadruped high-level skill planning; code license and external-VLM chain do not close the reproduction gate. [Local PDF](../../docs/research/papers/Chen2025VLMPC.pdf) |
| Cheng2025NaVILA | paper | [RSS 2025](https://www.roboticsproceedings.org/rss21/p018.html) | PDF SHA-256 `e02fcccae8aa` | surveyed | Direct legged VLA with mid-level motion commands; main model and dataset licenses remain missing. [Local PDF](../../docs/research/papers/Cheng2025NaVILA.pdf) |
| Ding2024QUARVLA | paper | [arXiv 2312.14457](https://arxiv.org/abs/2312.14457) | PDF SHA-256 `14321464aa61` | surveyed | Direct quadruped VLA; no canonical runnable release was found. [Local PDF](../../docs/research/papers/Ding2024QUARVLA.pdf) |
| Frey2023WVN | paper | [RSS 2023](https://roboticsproceedings.org/rss19/p054.html) | PDF SHA-256 `968c82dd6c58` | surveyed | Wild visual traversability support, not a VLA. [Local PDF](../../docs/research/papers/Frey2023WVN.pdf) |
| Goetting2024VLMnav | paper | [arXiv 2411.05755](https://arxiv.org/abs/2411.05755) | PDF SHA-256 `76f5cbb6b7a6` | surveyed | Zero-shot discrete VLM navigation; repository license and cloud-model dependency fail the gate. [Local PDF](../../docs/research/papers/Goetting2024VLMnav.pdf) |
| Hirose2025LeLaN | paper | [PMLR 270](https://proceedings.mlr.press/v270/hirose25b.html) | PDF SHA-256 `f05f0d5924a1` | surveyed | Clear waypoint/velocity interface; weight and aggregate-data licenses remain incomplete. [Local PDF](../../docs/research/papers/Hirose2025LeLaN.pdf) |
| Hirose2026OmniVLA | paper | [arXiv 2509.19480](https://arxiv.org/abs/2509.19480) | PDF SHA-256 `f6744c6c6b5e` | surveyed | Dr Sun selected the corresponding repository; pinned edge and original runtime evidence now exists. The paper itself remains a surveyed source. [Local PDF](../../docs/research/papers/Hirose2026OmniVLA.pdf) |
| Huang2023VLMaps | paper | [arXiv 2210.05714](https://arxiv.org/abs/2210.05714) | PDF SHA-256 `c7bb57c0defb` | surveyed | Open-vocabulary semantic-map predecessor; support module rather than VLA. [Local PDF](../../docs/research/papers/Huang2023VLMaps.pdf) |
| Huang2025MobileVLAR1 | paper | [arXiv 2511.17889](https://arxiv.org/abs/2511.17889) | PDF SHA-256 `f6a719d00e66` | surveyed | Direct mobile/quadruped control relevance; core data link and official pretrained smoke path remain incomplete. [Local PDF](../../docs/research/papers/Huang2025MobileVLAR1.pdf) |
| Liu2025CityWalker | paper | [CVPR 2025](https://openaccess.thecvf.com/content/CVPR2025/html/Liu_CityWalker_Learning_Embodied_Urban_Navigation_from_Web-Scale_Videos_CVPR_2025_paper.html) | PDF SHA-256 `2d15ff7b166a` | surveyed | Visual future-trajectory foundation model without language conditioning. [Local PDF](../../docs/research/papers/Liu2025CityWalker.pdf) |
| Long2024InstructNav | paper | [arXiv 2406.04882](https://arxiv.org/abs/2406.04882) | PDF SHA-256 `491e7fef88ae` | surveyed | Layered semantic navigation; repository license and external-API chain are unresolved. [Local PDF](../../docs/research/papers/Long2024InstructNav.pdf) |
| NavDP2025 | paper | [arXiv 2505.08712](https://arxiv.org/abs/2505.08712) | PDF SHA-256 `ffc54542c81f` | surveyed | Continuous diffusion trajectory System 1; useful inside InternNav, not a standalone language baseline. [Local PDF](../../docs/research/papers/NavDP2025.pdf) |
| Roth2024ViPlanner | paper | [arXiv 2310.00982](https://arxiv.org/abs/2310.00982) | PDF SHA-256 `e137c0544599` | surveyed | Legged semantic local planning, not a VLA. [Local PDF](../../docs/research/papers/Roth2024ViPlanner.pdf) |
| Shah2023LMNav | paper | [PMLR 205](https://proceedings.mlr.press/v205/shah23a.html) | PDF SHA-256 `464d4cf79d30` | surveyed | Foundational layered language-navigation reference; included as a date-range exception. [Local PDF](../../docs/research/papers/Shah2023LMNav.pdf) |
| Song2024GeRM | paper | [arXiv 2403.13358](https://arxiv.org/abs/2403.13358) | PDF SHA-256 `aa87d7d7eed5` | surveyed | Highly relevant quadruped generalist model, but the public implementation and license are insufficient. [Local PDF](../../docs/research/papers/Song2024GeRM.pdf) |
| StreamVLN2025 | paper | [arXiv 2507.05240](https://arxiv.org/abs/2507.05240) | PDF SHA-256 `e771475ef290` | surveyed | Streaming VLN component; best considered through InternNav rather than standalone. [Local PDF](../../docs/research/papers/StreamVLN2025.pdf) |
| Tang2023SayTap | paper | [PMLR 229](https://proceedings.mlr.press/v229/tang23a.html) | PDF SHA-256 `5e1fcd1b750a` | surveyed | Language-to-quadruped locomotion predecessor, not a navigation VLA. [Local PDF](../../docs/research/papers/Tang2023SayTap.pdf) |
| Tong2025QUARTOnline | paper | [arXiv 2412.15576](https://arxiv.org/abs/2412.15576) | PDF SHA-256 `ec670370bd77` | surveyed | Direct streaming quadruped VLA; open-source release remains insufficient. [Local PDF](../../docs/research/papers/Tong2025QUARTOnline.pdf) |
| Wei2026InternVLA | paper | [arXiv 2512.08186](https://arxiv.org/abs/2512.08186) | PDF SHA-256 `c535e225421e` | surveyed | Strong dual-system alternative; model card has an NC badge but lacks structured license metadata and a license file. [Local PDF](../../docs/research/papers/Wei2026InternVLA.pdf) |
| Yin2025UniGoal | paper | [arXiv 2503.10630](https://arxiv.org/abs/2503.10630) | PDF SHA-256 `86654c940baec` | surveyed | Universal goal representation reference, not a direct quadruped baseline. [Local PDF](../../docs/research/papers/Yin2025UniGoal.pdf) |
| Yokoyama2024VLFM | paper | [arXiv 2312.03275](https://arxiv.org/abs/2312.03275) | PDF SHA-256 `07f1f60fae11` | surveyed | Explainable language-value frontier baseline; modular semantic navigation rather than end-to-end VLA. [Local PDF](../../docs/research/papers/Yokoyama2024VLFM.pdf) |
| Zhang2025UniNaVid | paper | [RSS 2025](https://www.roboticsproceedings.org/rss21/p013.html) | PDF SHA-256 `ec1399b1bdb3` | surveyed | General video VLN/VLA; checkpoint license remains incomplete. [Local PDF](../../docs/research/papers/Zhang2025UniNaVid.pdf) |
| Zhang2026QwenRobotNav | paper | [arXiv 2606.18112](https://arxiv.org/abs/2606.18112) | PDF SHA-256 `dc70ff7f3b44` | surveyed | Go2-relevant technical report; runnable code, weights, and license were not released at the pinned repository state. [Local PDF](../../docs/research/papers/Zhang2026QwenRobotNav.pdf) |
| Zheng2024NaviLLM | paper | [arXiv 2312.02010](https://arxiv.org/abs/2312.02010) | PDF SHA-256 `c3504a31db06` | surveyed | General embodied-navigation benchmark model; root code license was not found. [Local PDF](../../docs/research/papers/Zheng2024NaviLLM.pdf) |

Full PDF provenance and hashes are tracked in the survey
[`artifact_manifest.tsv`](../survey/2026-08-16_lite3_vla_open_source_reproduction_survey/artifact_manifest.tsv).

## Upstream Repositories

| Citation key | Type | Canonical source | Pinned version | Status | Notes |
|---|---|---|---|---|---|
| OmniVLA | repository | [NHirose/OmniVLA](https://github.com/NHirose/OmniVLA) | `5182600cb4a9ee07684e17cdd2a6cbafc56b8a68` | imported; reproduced | MIT code; edge reproduced on macOS CPU and original reproduced in the official CUDA stack. A separate Lite3 single-frame receive-only contract is integrated and validated; no navigation or locomotion claim. |
| InternVLA-N1 / InternNav | repository | [InternRobotics/InternNav](https://github.com/InternRobotics/InternNav) | `7a5c62400ac45b313d9b709c740b64191556a242` | surveyed | MIT code; model-card NC badge plus missing structured metadata/license file; gated NC data; known dependency issue. |
| VLFM | repository | [rai-opensource/vlfm](https://github.com/rai-opensource/vlfm) | `584ed56008754fde7997d904983607def8328322` | surveyed | MIT main code, mixed upstream licenses, legacy stack, and no active maintenance; not an end-to-end VLA. |
| NaVILA | repository | [AnjieCheng/NaVILA](https://github.com/AnjieCheng/NaVILA) | `76b98f233dd0fff05dfcd69435eec6740febff9d` | surveyed | Apache-2.0 code; main checkpoint/data licensing and complete Go2 deployment chain remain open. |
| NaVILA-Bench | repository | [yang-zj1026/NaVILA-Bench](https://github.com/yang-zj1026/NaVILA-Bench) | `e9d2db12ce5788c0f987d734c0094100b6bc0d3a` | surveyed | Useful companion benchmark; cannot cure NaVILA's main asset-license gaps. |
| LeLaN | repository | [NHirose/learning-language-navigation](https://github.com/NHirose/learning-language-navigation) | `a41d478cb966eabce78af2b79e6cbfef3aebd589` | surveyed | MIT code and clear ROS waypoint/velocity interface; asset licenses and legacy dependencies remain open. |
| MobileVLA-R1 | repository | [AIGeeksGroup/MobileVLA-R1](https://github.com/AIGeeksGroup/MobileVLA-R1) | `ff9062c143d6b50c05d913e6be15d36634a7a460` | surveyed | Apache-2.0 code, but the core data URL and official pretrained smoke path are incomplete. |
| Uni-NaVid | repository | [jzhzhang/Uni-NaVid](https://github.com/jzhzhang/Uni-NaVid) | `79ef5ea3fea14c205342d1ab070563d84c7a966a` | surveyed | MIT code; official checkpoint-license evidence remains incomplete. |
| NaviLLM | repository | [zd11024/NaviLLM](https://github.com/zd11024/NaviLLM) | `a221f42ad52893e861779921df336d63c0b4f3a6` | surveyed | Root repository license was not found; benchmark-oriented and inactive. |
| InstructNav | repository | [LYX0501/InstructNav](https://github.com/LYX0501/InstructNav) | `e58a5aac51cdb1c1ea4794ded0138e78f24de70f` | surveyed | No root license found and some external model/API dependencies remain. |
| VLMnav | repository | [Jirl-upenn/VLMnav](https://github.com/Jirl-upenn/VLMnav) | `82d59684c15a6694ea73b969e76a57157c8740b8` | surveyed | No root license found; external VLM dependency makes it unsuitable as the first baseline. |
| VLM-PC | repository | [stanford-iris-lab/vlm-pc](https://github.com/stanford-iris-lab/vlm-pc) | `4a616a93ebd8036bc2c43fbe45071ef939daca48` | surveyed | Quadruped skill-planning implementation; code license and external-service chain fail the gate. |
| StreamVLN | repository | [InternRobotics/StreamVLN](https://github.com/InternRobotics/StreamVLN) | `e48f6ff7e9201d93aae003e8f64b04c00cec13bc` | surveyed | Useful InternNav component; standalone root license evidence is incomplete. |
| NavDP | repository | [InternRobotics/NavDP](https://github.com/InternRobotics/NavDP) | `878740a2011856d0e3782dd6ccd880fd2eccd70f` | surveyed | Active trajectory component; checkpoint terms and standalone root license need separate review. |
| Qwen-RobotNav | repository | [QwenLM/Qwen-RobotNav](https://github.com/QwenLM/Qwen-RobotNav) | `f74cf1f6079300aee6e40e03858da2f98b1b7261` | surveyed | Report and media only at the pinned state; runnable implementation, weights, and license absent. |
| GeRM | repository | [Songwxuan/GeRM](https://github.com/Songwxuan/GeRM) | `fadc5b2de494c1084e88865279341799a74417fc` | surveyed | Public repository lacks enough runnable implementation and license evidence. |
| VLMaps | repository | [vlmaps/vlmaps](https://github.com/vlmaps/vlmaps) | `58060f97239074338ab419a2090d43fa752d724d` | surveyed | MIT open-vocabulary mapping component; useful support, not a VLA baseline. |
| ViPlanner | repository | [leggedrobotics/viplanner](https://github.com/leggedrobotics/viplanner) | `6fcf3c60f6fa3b28b3a11af054d6033825923789` | surveyed | Legged local-planning component under custom terms; not a language/VLA baseline. |
| CityWalker | repository | [ai4ce/CityWalker](https://github.com/ai4ce/CityWalker) | `ab0ef60b17dc4d1d16c7d95dd143e6dac91abed1` | surveyed | Apache-2.0 visual trajectory model; no language conditioning, so only an adjacent comparator. |
| QUAR-VLA official release | repository | [Project page](https://quart-robot.github.io/) | — | surveyed | Project page still reports code as forthcoming; no canonical runnable repository was accepted. |
| VoroNav | repository | [Project page](https://voro-nav.github.io/) | — | surveyed | Project page reports code as forthcoming; no implementation was accepted. |

Use `surveyed`, `imported`, `reproduced`, `integrated`, and `validated` only as
defined in `AGENTS.md`.

## 2026-10-12 stop and holding source audit

Status: surveyed only. [Thirteen-repository stop/recovery comparison](../survey/2026-10-12_v177_stop_recovery_upstream_survey.md)
links pinned Nav2Foxy/newerMPPI, move_base, TEB, SCAN/EGO, Fast-Planner, FASTER,
CMUGo2, ART and field_local_planner sources, plus officialLite3sdk_deploy,
UnitreeRLgym and legged_gym control/standing references.27existing source files
were freshly byte-verified; new selected sources have per-file manifests under
`references/upstream/2026-10-12_stop_hold/`. No implementation import, upstream
execution or comparative physical success claim.

## 2026-10-12 RL zero-command stopping follow-up

Status: surveyed only. [Seven locomotion repositories and current V12 source](../survey/2026-10-12_rl_zero_command_upstream_survey.md)
separate velocity tracking, stationary training, foot support and deployment
mode changes. The pinned V12 command branch clears XY but does not guarantee
zero yaw; its available stand-still reward is not configured and its posture
standing multipliers are 1.0. These are source findings, not an original-run
command distribution or causal policy diagnosis. The per-leg handoff proposal
remains unvalidated; isolate policy stopping before selecting a repair.

## 2026-10-08 mapping backlog and safe navigation

Status: surveyed only. [Eight-repository mapping/admission survey](../survey/2026-10-08_mapping_backlog_upstream_survey.md)
reads pinned Nav2, ROG-Map, SUPER, Elevation Mapping CuPy, Isaac ROS nvblox,
EGO-Planner, SCAN-Planner and PCT-SCAN-ROS2 sources against local v78/v82
evidence. The inspected upstreams combine bounded or latest-observation input,
separate mapping/control rates, local/incremental map work and continued
execution of a committed trajectory; they do not establish that a background
mapper can keep every observation of an arbitrarily growing stream. Our v82 keeps every
distinct scan under a 250 ms map-age gate, so it is not equivalent to a
latest-slot or bounded-drop queue. Recommendations are hypotheses; no upstream
was cloned or run.

## 2026-10-09 local-planning failure handling

Status: surveyed only. [Four-implementation failure-path survey](../survey/2026-10-09_local_planning_failure_upstream_survey.md)
checks pinned SCAN-Planner, EGO-Planner, TEB and Nav2 Foxy source: each
anticipates failed local planning (retries, counters, zero command, emergency
stop or a FollowPath abort). Three public issue reports are recorded as user
evidence, not reproduced. Upstream failures do not qualify our latency,
recovery or reliability.

## 2026-10-13 local trajectory completion (terminal crawl)

Status: surveyed only. [Six-repository completion survey](../survey/2026-10-13_terminal_capture_upstream_survey.md)
compares Nav2 Foxy SimpleGoalChecker, ROS navigation LatchedStopRotateController,
CMU Go2 pathFollower, TEB, SCAN closed_loop_controller and EGO traj_server;
pins and file SHA-256 are under `references/upstream/2026-10-13_terminal_capture/`.
It motivated the v184/v185 completion latch and the v187 bounded-correction
timeout (Nav2 controller failure -> recovery). v185 3/5, v186 2/5 and v187 3/5
full-route arrivals were not accepted (v185/v186 rejected); the unchanged v177
control arrived 5/5.
No upstream source was copied or executed.
