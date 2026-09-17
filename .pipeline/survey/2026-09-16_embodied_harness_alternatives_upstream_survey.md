---
origin: ai_only
reviewed: false
status: surveyed
checked_on: 2026-09-16
---

# Open implementations adjacent to HarnessVLN

Stage: experiment + analysis, source survey only. Dr Sun asked for released
alternatives after discussing spatial target grounding and SLAM in HarnessVLN.
The screening criteria were an actual agent/runtime or semantic-navigation
implementation, a traceable license, an original execution entry, and a clear
boundary between navigation reasoning and robot execution. No installation,
model run, remote experiment, robot connection or actuation was performed.

## Selection assessment

| Candidate | Relevant capability | Best use and boundary |
|---|---|---|
| [EMOS](https://github.com/automatika-robotics/emos), Automatika Robotics | Cortex plans and executes tools; Memory wraps eMEM; Kompass supplies planning/control; Sugarcoat manages components/events. A public Lite3 plugin exists. | Closest newly identified software-runtime reference for a Lite3 agent. Public components and adapters are not evidence that our robot or firmware is supported without verification. |
| [RAI](https://github.com/RobotecAI/rai), RobotecAI | ROS 2 agent framework with image/transform/object-position tools and Nav2 goal, feedback and cancellation tools. | Good reference when building on an existing ROS 2/Nav2 robot. The ROSbot XL example supplies named room coordinates; it is not evidence of unknown-building semantic exploration. |
| [HSGM](https://github.com/Teacher-Tom/HSGM_public), CVPR 2026 | Hierarchical semantic/geometric maps, language-conditioned target selection and A* execution in Habitat. | Best of this small set for a paper-defined navigation comparison. It is not a generic agent harness or a supplied Lite3 deployment. |

This EMOS is Automatika Robotics' Embodied Operating System, not the differently
authored ICLR 2025 paper with the same acronym. MIP remains the selected existing
minimal baseline. The recommendations above do not select a replacement or
authorize implementation. Paper-architecture comparison remains in
`2026-09-16_harness_vln_open_source_upstream_survey.md`.

## Pinned identities and licensing

| Repository | Branch / inspected commit | License evidence |
|---|---|---|
| automatika-robotics/emos | main / `31b82958e7a1646b9af606184518333c97290f58` | Root MIT license checked. |
| automatika-robotics/embodied-agents | main / `29898459a7fc80ed1a5f6cbbfdc0f9459b68321f` | Root MIT license checked. EMOS itself pins `c37ab75db4aba88bcc99d17f6eabac146ad46d20`; Cortex/Memory source and MIT license were inspected at that gitlink revision. |
| automatika-robotics/emos-plugin-lite3 | main / `8aa389a6df9952bb9537e4b61891d8d68a4cdf22` | `package.xml` declares MIT. No root license text exists in the inspected 15-file tree; distinguish this declaration from the main EMOS license. |
| RobotecAI/rai | main / `6802d4073e8caa2ab72c5509fa1eeeb659663f64` | Root Apache-2.0 license checked. |
| Teacher-Tom/HSGM_public | main / `e2df6e70df869af57d77a32ba658fba04e6814eb` | Root Apache-2.0 license checked; unchanged from the earlier survey. |

EMOS also pins `stack/kompass` to `0a4b9b221731d3dad2aae12c7d7671c0eb8e0cef`
and `stack/sugarcoat` to `a389fb263fdd3a80181556eb2a7b3031a5fd59a2`.
These are recorded submodule identities, not imports or runtime checks.

## Code and execution entry mapping

### EMOS / Cortex

At the EMOS-pinned EmbodiedAgents revision, `agents/components/cortex.py`
contains `Cortex`, `_plan_task`, `_process_planning_calls`,
`_execute_action_step`, `_append_execution_results_to_planning`, and action
feedback/cancellation management. `agents/components/memory.py` instantiates
`emem.SpatioTemporalMemory` and requires a position/odometry topic to tag
observations. These implementation anchors support the presence of a runtime;
they do not validate task success or failure recovery on our hardware.

The official [full-stack tutorial](https://emos.automatikarobotics.com/recipes/planning-and-manipulation/cortex-navigation.html)
wires perception, position-tagged memory, Cortex and Kompass's Planner,
Controller, LocalMapper and DriveManager. Its example uses an existing
`/odometry/filtered` input and configured `map`/`odom` frames. The
[mapping documentation](https://emos.automatikarobotics.com/navigation/mapping.html)
describes integrating Robot Localization, SLAM Toolbox or Glim. Public robot
drivers and a local mapper should not be described as a complete calibrated
global localization system.

Original entry points, recorded but not executed: `emos install --mode
container` or `emos install --mode native`, then `python recipe.py` for a
prepared recipe, or `emos run <recipe_name>` for a registered recipe. Dependencies
include ROS 2/container runtime, the pinned submodules, model serving, robot
drivers and a suitable localization/TF setup. The repository documents Ollama,
RoboML, vLLM and OpenAI-compatible providers; no DeepSeek compatibility or GPU
fit was executed in this survey.

### Lite3 plugin

`lite3_plugin/plugin.py::Lite3Plugin` and `codecs.py` implement Motion Host UDP
telemetry/command conversion. Observed source contracts include `Twist` velocity
commands, leg odometry, IMU, joint/operator feedback and status events.
`republishers.py` exports standard ROS 2 feedback and an odometry transform.
`package.xml` names Sugarcoat, ROS message/TF packages, Livox and RealSense
drivers; camera/lidar paths and mounting transforms must be checked against the
actual sensor rig before use. This source does not establish any leg-odometry
accuracy or SLAM performance.

The plugin supplies a box footprint and a differential-drive planning
abstraction while sending Lite3 velocity packets. It is an adapter around the
robot's Motion Host interface, not a replacement quadruped locomotion policy.
The current VLA project's pinned custom locomotion interface would need a
separate compatibility decision before reuse. Do not start the plugin merely
to inspect it: activation includes a control heartbeat and motion-capable
actions. No plugin import/activation or robot connection was performed here.

### RAI

`examples/rosbot-xl-demo.py` constructs a `ReActAgent` with image, TF,
object-position, current-pose and blocking navigation tools.
`src/rai_core/rai/tools/ros2/navigation/nav2.py` contains `Nav2Toolkit`,
`NavigateToPoseTool`, feedback/result queries and cancellation. The official
[ROSbot demo](https://robotecai.github.io/rai/demos/rosbot_xl/) uses Grounded SAM 2,
GroundingDINO and Nav2; Kitchen/Living Room coordinates are provided in its
embodiment configuration. It requires existing localization and navigation
services and does not supply a Lite3 adapter in the inspected example.

Original demo entry: source `setup_shell.sh`, launch
`examples/rosbot-xl.launch.py` with the downloaded O3DE game launcher, then
`streamlit run examples/rosbot-xl-demo.py`. The documented setup includes ROS 2,
Nav2, perception dependencies, model-provider configuration and the simulator
assets. None of these commands was executed.

### HSGM

`src/agent/agent.py` contains the navigation agent; the inspected
`src/mapping_utils/path_planning.py::path_planning` uses `AStarFinder` on a
costmap. Original entry from `src/`:
`python run_experiments.py --task r2r --config ../config/vlnce_test.yaml`.
Dependencies and sensor mismatch are recorded in the earlier survey: Habitat,
scene assets, segmentation weights and a VLM endpoint are required. This
inspection does not establish a real-robot localization or control adapter.

## Evidence

`2026-09-16_embodied_harness_alternatives_sources/manifest.json` records five
repository identities, trees, gitlinks, root READMEs/licenses and SHA-256 values.
`code_inspection.json` records fifteen versioned source/document captures and
their hashes. All evidence labels are `surveyed`; nothing was imported as a
baseline, reproduced, integrated or validated by this follow-up.
