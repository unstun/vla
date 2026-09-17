---
origin: ai_only
reviewed: false
status: surveyed
checked_on: 2026-09-16
---

# Open-source navigation work related to HarnessVLN

The project remains in experiment + analysis. This is a source survey requested by
Dr Sun, not a decision to replace InternVLA-N1 or alter the current experiment
protocol. No candidate was installed, executed, imported as a baseline, or tested
on Lite3 during this survey.

## Follow-up: AgiBot and a dedicated navigation harness

Dr Sun asked whether AgiBot has a purpose-built embodied agent harness. The
closest identified match is **HarnessVLN**, by authors affiliated with Nanjing
University, AGIBOT and Tsinghua University. The paper was posted on 2026-09-14;
its physical deployment uses an AgiBot A3U humanoid. This identity is verified
from the [official project page](https://agibot-harnessvln.netlify.app/) and
[paper v1](https://arxiv.org/html/2609.15195v1), not inferred solely from the
robot manufacturer.

Compared with the MIP minimal interface, the paper describes additional
navigation-specific runtime responsibilities: bounded working memory, explicit
subgoal states, failure-event memory, a persistent spatiotemporal graph,
evidence and reachability checks before execution, and validated stopping.
Its eight tools are `observe`, `observe_panorama`, `retrieve_memory`,
`ground_target`, `query_depth`, `navigate_to`, `backtrack` and `request_stop`.
The model proposes operations; the harness checks and dispatches them. A stop
request requires semantic, geometric and task-progress evidence. These are
paper-described mechanisms, not locally verified implementation behavior.

The code-release check is now more precise than the initial inaccessible-link
result below. The official [repository](https://github.com/AgibotGeneral/harnessvln)
is public, but `main` at `b71bed50953c5f300ce2c5aeefbb18383514c11b`
(2026-09-12) contains only `readme.md`. It says code will be released after
paper submission. No root license, implementation, installation procedure or
execution entry exists in the inspected snapshot. This is a paper and project
page reference, not an available reproduction baseline. The versioned PDF is
saved at `docs/research/papers/pdf/2026-09-16_harnessvln/` with provenance.

**Link-U OS / 灵渠 OS** is a second AgiBot project with a different scope. Its
[public repository](https://github.com/Link-U-OS/Link-U-OS) was checked at
`64ac7b08dd609dfb463310945856419be470315a` (2026-01-12), with a root
Mulan PSL v2 license. The Alpha documentation emphasizes AimRT communication,
hardware and process services, Bazel/Docker integration, AimStudio deployment,
and A2 bipedal locomotion training/deployment with MuJoCo and Isaac Gym. These
are robot infrastructure capabilities; this inspection does not establish a
released HarnessVLN-equivalent agent loop in Link-U OS. Original usage starts
with `document/en/setup_environment.md`, `build_package.md`,
`deploy_package.md` and `robot_operation.md`, linked by the pinned documentation
index. Submodules have separate revisions and terms and were not imported or
executed.

For this question, HarnessVLN is the direct navigation-harness design reference;
Link-U OS is the robot infrastructure reference. Neither changes the selected
MIP preparation or authorizes a new experiment. Source captures, repository
identities, license text and SHA-256 records are in
`2026-09-16_harness_vln_open_source_sources/agibot_followup/manifest.json`.

### Reproduction and quadruped adaptation assessment

Dr Sun subsequently asked about reproduction difficulty, implementation ancestry,
and dog-platform compatibility. The public repository was rechecked: its complete
tree at `b71bed50953c5f300ce2c5aeefbb18383514c11b` is one README blob. The
paper does not identify an inherited agent-runtime codebase; a derivation from
MIP, OpenClaw or a particular agent library is not established. Figure 2 and
Sections 3/4 describe a custom navigation harness coordinating existing models
and planners. The appendices specify that a single MLLM serves initialization,
planning, grounding, verification and recovery with function-specific prompts.
That description does not establish how any underlying agent library was used.

| Component | Paper-specified implementation | Reproduction boundary |
|---|---|---|
| Simulation | Habitat, MP3D R2R/RxR, HM3D-v2 and HM3D-OVON | Dataset/simulator setup is needed; no executable HarnessVLN environment lock is released. |
| MLLM | GPT-5.5 for main instruction following; GPT-5.6-luna for main ObjectNav; Qwen-3.8-27B on A3U | Using DeepSeek would be a separately labeled model substitution. |
| Perception | GroundingDINO and SAM; synchronized RGB-D and pose | Pretrained perception components and calibration remain required. |
| Navigation executor | FMM for planar motion; NavDP for stair traversal | Exact integration code, dependency revisions and checkpoint bindings are unavailable. |
| A3U depth | Head stereo images with Fast FoundationStereo | This sensor path must be adapted to the selected Lite3 sensors. |
| Harness | Event memory, ST Graph, proposal validation and stop checks | Algorithm and partial parameters are published; full prompts and implementation are not. |

Appendix 1 is more concrete than a conceptual diagram: it specifies a 5 cm map,
0.75/1.00 m place/entity merge radii, three retrieval seeds and at most five
returned places, IDF-weighted cosine relevance, and a 50-image request budget.
It also gives geometric stopping measurements and thresholds. Appendix 2
explicitly labels its prompts as condensed excerpts. Thus an independent
research prototype is feasible, but matching the original implementation and
reported scores is not yet a straightforward installation task. No wall-clock
estimate or GPU-fit guarantee is supported by the released material.

Quadruped adaptation is an architectural assessment, not a reported HarnessVLN
result. Its high-level task/memory protocol can in principle stay above a
replacement executor, but a Lite3 implementation would need synchronized RGB-D
and pose, calibrated frame transforms, body-aware traversability/clearance,
trajectory or velocity execution through a pinned locomotion interface, and
measured arrival/failure feedback. The simulation defaults (0.88 m sensor
height and 0.10 m agent radius) are not a Lite3 body model. The independent
[NavDP paper](https://arxiv.org/html/2505.08712v3), Sections V-A/V-B and Tables
III/IV, reports Unitree Go2 evaluation. This supports the feasibility of one
executor component, not the entire HarnessVLN stack or a Lite3 port.

For a future project decision, keep MIP as the existing minimal reference and
consider adding one reviewed mechanism at a time (task state, geometric stop
verification, then persistent spatial evidence). Such work would be a local
extension inspired by HarnessVLN until the original release is available and
matched. This assessment authorizes no new implementation or experiment.

## Scope refinement: harness research with physical quadruped navigation

Dr Sun clarified that the target is work on the agent harness itself for robot-dog
navigation. The broader six-candidate list below is therefore background, not a
list of confirmed quadruped-harness deployments. Three directly relevant papers
were verified against their primary text:

| Paper | Physical platform and harness contribution | Evidence boundary and code |
|---|---|---|
| [NavMCP: Scaffolding Foundation Models into Physical-World Agents Pushes the Frontier of Long-Horizon Navigation](https://arxiv.org/abs/2608.30396), 2026-08-31 | Unitree Go2. A reasoning agent calls a navigation foundation model; intent, trajectory observations and persistent evidence memory coordinate multi-room exploration. | [Sections 3, 4.5 and Appendix C](https://arxiv.org/html/2608.30396v1). Real tasks involve exploration to answer questions; the Go2 obstacle-avoidance layer remains enabled. No canonical complete implementation was established in this search. |
| [Embodied Agents Take Control / MIP](https://arxiv.org/abs/2607.26148), 2026-07-28 | Unitree Go2. General coding-agent harnesses own the observe/act/recover/stop loop over monocular RGB and discrete motion primitives. | [Section 4.7 and Appendix C](https://arxiv.org/html/2607.26148v1) describe qualitative physical trials, including body-clearance and spatial-memory failures, rather than a controlled real-world success-rate benchmark. Apache-2.0 paper branch verified above; `coding-agent/bridges/go2_bridge.py` and `go2_host.py` also fetched for interface inspection, not executed. |
| [Harness Robotic OS: A Unified Embodied-Agent Runtime for Closed-Loop Quadruped Inspection](https://arxiv.org/abs/2609.11225), 2026-09-10 | Vbot quadruped, Argos inspection system. Shared context, reusable navigation/perception skills, OpenClaw/Qwen3-VL orchestration and operational feedback form the runtime. | [Sections 3–6](https://arxiv.org/html/2609.11225v1). Deployed navigation uses a prior map and configured inspection waypoints. Cognitive memory/evolution protocols should not be conflated with the reported navigation/inspection results. No canonical complete implementation was established in this search. |

For a Lite3 research direction that wraps existing navigation and locomotion,
**NavMCP is the closest architectural reference** (assessment). For an immediately
inspectable, licensed tool-interface implementation with physical quadruped
evidence, **MIP is the clearest candidate in this narrowed set**. These remain
reading/reproduction recommendations, not a baseline decision.

Robot-type exclusions verified from original papers:

- [AgenticNav, Section 4.2](https://arxiv.org/html/2606.10577v2) uses an
  omnidirectional four-wheel robot, not a quadruped.
- [HarnessVLN, Section 5.1](https://arxiv.org/html/2609.15195v1) uses an AgiBot A3U
  humanoid. It remains an architectural reference, not quadruped evidence.
- [ReasonNav, Appendix D.1](https://reasonnav.github.io/assets/paper.pdf) uses an
  AgileX Ranger Mini 2.0 wheeled base.

The narrowed survey did not establish that these three are an exhaustive list.

## Scope and result

Criteria: language/semantic navigation with explicit planning, spatial memory,
tools, execution feedback, recovery, or completion checks; an official paper and
substantive public implementation; a checked root code license. Six candidates
meet the code-and-license criterion. Their weights, external services, datasets,
and third-party components have separate requirements.

| Candidate and paper | Relation to HarnessVLN | Verified release and main boundary |
|---|---|---|
| [HSGM, CVPR 2026](https://arxiv.org/abs/2606.00095) | Subtasks, semantic/geometric maps, VLM waypoint selection, classical A* execution | [Apache-2.0 code](https://github.com/Teacher-Tom/HSGM_public); agent, mapper, planner and evaluation entry exist. Habitat and external VLM service required. |
| [GC-VLN, CoRL 2025](https://arxiv.org/abs/2509.10454) | Instructions become spatial graph constraints; navigation tree supports backtracking | [MIT code](https://github.com/bagh2178/GC-VLN); constraint solver, graph and planner exist. Released evaluation consumes a supplied instruction DAG; arbitrary live-language parsing remains to be checked. |
| [MSGNav, CVPR 2026](https://arxiv.org/abs/2511.10376) | Multimodal spatial memory, closed-loop reasoning, feasible final viewpoints near a target | [MIT code](https://github.com/ylwhxht/MSGNav); HM3D and GOAT-Bench evaluation exists. Unitree G1 deployment code is still marked forthcoming. Primarily goal/object navigation, not the same route-following task as R2R. |
| [Embodied Agents Take Control / MIP, 2026 preprint](https://arxiv.org/abs/2607.26148) | A general agent owns the navigation loop through observation and motion tools | [Apache-2.0 paper branch](https://github.com/jianzhou0420/AgentCanvas/tree/archive/mip-embodied-agents-take-control); MCP bridge, model adapters and evaluation driver exist. Minimal interface intentionally omits explicit spatial memory/maps. |
| [SG-Nav, NeurIPS 2024](https://arxiv.org/abs/2410.08189) | Online hierarchical 3D scene graph and re-perception to correct target detection | [MIT code](https://github.com/bagh2178/SG-Nav); agent and scene graph implementation exist. Object-category search, legacy Habitat/Torch stack. |
| [VLFM, ICRA 2024](https://arxiv.org/abs/2312.03275) | Language-conditioned frontier selection, explicit maps, PointNav execution | [MIT code](https://github.com/rai-opensource/vlfm); Habitat evaluation and Spot-related implementation exist. Object-category search; README explicitly disclaims active maintenance. |

The similarities above are an architectural assessment, not a claim that these
methods implement HarnessVLN's complete tool contract or stop-validation rule.
Performance numbers across different tasks, splits and sensors are not ranked.

## Repository identities checked live

Commit dates describe the inspected revision, not a prediction of maintenance.
All six repositories were accessible. The five main-branch shortlist repositories
were reported unarchived by the API. MIP uses an explicitly frozen paper branch;
that branch designation is separate from a repository's archive status.

| Repository | Branch inspected | Commit | Commit date | Root code license |
|---|---|---|---|---|
| Teacher-Tom/HSGM_public | main | `e2df6e70df869af57d77a32ba658fba04e6814eb` | 2026-06-11 | Apache-2.0 |
| bagh2178/GC-VLN | main | `1beddca8d90d79855c110c5a433f7b8856ca263a` | 2026-06-21 | MIT |
| ylwhxht/MSGNav | main | `03681a178d6993265e838e1fbbaf2338c54e1c62` | 2026-03-23 | MIT |
| jianzhou0420/AgentCanvas | archive/mip-embodied-agents-take-control | `b2b363af80a010ea9f73a0be9d49bc75555efdef` | 2026-08-28 | Apache-2.0, checked on this branch |
| bagh2178/SG-Nav | main | `d56863c96dea311aaa67fb0d39a1a8ccc3f0487f` | 2025-09-16 | MIT |
| rai-opensource/vlfm | main | `584ed56008754fde7997d904983607def8328322` | 2025-01-07 | MIT |

## Execution assumptions and source checks

The commands below are upstream README entry points, recorded but **not run**.
They do not include all installation, data, service-start or weight preparation.

| Candidate | Environment and assets | Original entry | Interface and adaptation boundary |
|---|---|---|---|
| HSGM | Python 3.9+, CUDA, Habitat-Sim/Lab, YOLOE segmentation weights, MP3D/R2R/RxR or HM3D; OpenAI-compatible VLM endpoint, with local vLLM described as an option | From `src/`: `python run_experiments.py --task r2r --config ../config/vlnce_test.yaml` | VLM chooses waypoints, A* plans motion for the simulator. Shipped config assumes camera height 1.2 m, HFOV 135 degrees, pitch -30 degrees, agent radius 0.1 m. These do not match Lite3. |
| GC-VLN | Python 3.9 agent and Python 3.10 model server, Habitat-Sim 0.2.4, GLIP, Grounded-SAM-2, MP3D and R2R/RxR episodes | Start GSAM2 server per README, then `bash run_eval.sh r2r` | Graph-derived spatial goals feed FMM and simulator actions. `get_instruction_graphs` reads `observations[i]['instruction']['DAG']`; online instruction-to-DAG generation is not established by the inspected code. |
| MSGNav | Python 3.9, Torch 2.0.1/CUDA 11.8, Habitat-Sim 0.2.5, perception models, HM3D/GOAT-Bench, configured Qwen/GPT endpoint | `python run_hm3d_evaluation.py -cf cfg/eval_hm3d.yaml` | Spatial target/viewpoint and exploration planning inside Habitat. No released Lite3 control adapter was established; G1 release remains forthcoming. |
| MIP | AgentCanvas backend/runner Python 3.10; VLN-CE environment Python 3.8 and Habitat-Sim 0.1.7; MP3D scenes; chosen agent/model credentials or supported local model service | After starting the environment host: `python coding-agent/stdrun.py run std_codex_gpt-5.6_bare_default` | `observe()` returns RGB and `step(actions)` executes STOP/forward/left/right. A Lite3 adapter would need measured motion and camera feedback. The paper's main board uses a frozen 100-episode subset; do not compare its headline score directly with full-split scores. |
| SG-Nav | Python 3.9, Habitat-Sim 0.2.4, older Torch stack, GLIP/GroundingDINO/SAM, LLM configuration, scene datasets | `python SG_Nav.py --visualize` | Scene graph informs exploration/target goals; local FMM control emits simulator actions. Check CLI flags and required paths against the pinned README before execution. |
| VLFM | Python 3.9, Torch 1.12.1/CUDA 11.3, Habitat or Spot extras; MobileSAM, GroundingDINO, YOLOv7, PointNav weights; scene datasets | `./scripts/launch_vlm_servers.sh`, then `python -m vlfm.run` | Frontier/target waypoint to PointNav; Spot deployment is relevant precedent, not a Lite3 port. Third-party license terms remain separate from the MIT root. |

Selected implementation anchors, fetched at the pinned commits:

- HSGM: `src/agent/agent.py`, `src/mapping_utils/path_planning.py` and
  `config/vlnce_test.yaml`; the planner imports `AStarFinder`.
- GC-VLN: `src/solver/constraint.py`, `src/solver/navigation_tree.py`,
  `src/solver/instruction_graph.py` and `src/agent/navigation_planner.py`.
- MSGNav: `src/multimodal_3d_scene_graph.py`, `src/query_vlm.py` and
  `src/explore_utils.py`; scene observation/graph and target-query routines exist.
- MIP: `coding-agent/bridges/mcp_bridge.py` and
  `coding-agent/harnesses/mini/nav_agent.py`; the bridge exposes image observation
  and discrete action execution.
- SG-Nav: `SG_Nav.py` and `scenegraph.py`.
- VLFM: `vlfm/policy/base_objectnav_policy.py` and `vlfm/policy/itm_policy.py`.

## Related work not counted as a licensed implementation in this shortlist

- [InstructNav](https://arxiv.org/abs/2406.04882): official
  [repository](https://github.com/LYX0501/InstructNav), `main` at
  `e58a5aac51cdb1c1ea4794ded0138e78f24de70f` (2025-03-29), has substantive code
  and an ObjectNav benchmark entry. No root license was found in the complete
  tree. README uses Azure GPT-4/GPT-4V services. This refresh agrees with the
  earlier local survey on those two limitations.
- [CA-Nav](https://arxiv.org/abs/2412.10137): official
  [repository](https://github.com/Chenkehan21/CA-Nav-code), `main` at
  `8430359ff930880ccc74131d4c31d74a598a9b6e` (2026-03-10), contains an evaluator,
  baselines and configuration. No root license was found in the complete tree.
  README documents Habitat 0.1.7 and cached LLM replies. The linked ROS1 real-robot
  repository was not code-audited here.
- [AgenticNav, arXiv:2606.10577](https://arxiv.org/abs/2606.10577): especially
  relevant tool-calling design, but this search did not establish its canonical
  public implementation. GitHub/Hugging Face contain unrelated projects sharing
  the name; do not equate those with this paper.
- [HarnessVLN](https://arxiv.org/abs/2609.15195): the project page's Code button
  did not establish an accessible repository in the initial check. The follow-up
  above resolves the official public repository to a README-only placeholder;
  a runnable code release is still not available in that inspected snapshot.

## Recommendation for this project

First inspect **HSGM** as the candidate for a bounded upstream reproduction: its
semantic planner, explicit geometry, A* executor, license and evaluation entry
are identifiable in a small release. Before any run, resolve the segmentation
weight source, scene access, simulator versions and VLM endpoint. A one-episode
Habitat run would establish only upstream execution, not Lite3 integration.

Use **GC-VLN** to study instruction constraints and recovery, with the supplied
instruction-DAG dependency made explicit. Use **MSGNav** to study target approach
and final viewpoint selection. Use **MIP** as a distinct, minimal tool-interface
comparison; it does not supply HarnessVLN's explicit verification layer.

These are survey recommendations, not Dr Sun's baseline selection. Any new stop
arbitration, detector-based target decision or navigation executor would define
a new method relative to the current unchanged-upstream InternVLA-N1 protocol.
Existing Lite3 locomotion can be evaluated as a separate execution layer after
the required frame, scale, sensor, timing and collision contracts are specified.

## Evidence and refresh

Live primary-source metadata and inspected symbols are recorded in
[`2026-09-16_harness_vln_open_source_sources/`](2026-09-16_harness_vln_open_source_sources/):

- `repository_audit.json`: seven repository identities, complete file listings,
  root license texts and pinned READMEs.
- `mip_repository_audit.json`: the paper-specific AgentCanvas branch identity,
  file listing, branch license and README.
- `code_inspection.json`, `interface_inspection.json`: selected source URLs,
  SHA-256 hashes, symbols and line-numbered excerpts. No remote source was run.

To refresh identities, use the public GitHub repository endpoint to resolve the
default branch, the commits endpoint to resolve that branch, and the git/trees
endpoint at the resulting SHA with `recursive=1`. Inspect raw README/LICENSE
and source paths at that same SHA. MIP must resolve its paper branch explicitly.
All recorded trees returned `truncated: false`. This inspection does not verify
external download availability, environment installation or reported metrics.
