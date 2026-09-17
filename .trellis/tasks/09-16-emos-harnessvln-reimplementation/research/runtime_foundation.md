---
origin: ai_only
reviewed: false
checked_on: 2026-09-16
---

# Cortex, Pi and the selected runtime

Dr Sun asked whether the selected harness is built on Pi. The inspected
EmbodiedAgents revision is `c37ab75db4aba88bcc99d17f6eabac146ad46d20`, the
gitlink pinned by the selected EMOS revision.

`agents/components/cortex.py` directly implements planning, tool execution and
feedback-to-planning transitions. Its `ModelComponent` base calls a model
client; `agents/ros.py` imports Sugarcoat's components, monitor, action/service
client handlers and ROS types. `package.xml` declares the ROS/Sugarcoat runtime
dependencies. This is a Python/ROS agent implementation, not a Pi agent-core
integration in the inspected path.

Source anchors:

- [Cortex](https://github.com/automatika-robotics/embodied-agents/blob/c37ab75db4aba88bcc99d17f6eabac146ad46d20/agents/components/cortex.py):
  `_plan_task`, `_process_planning_calls`, `_execute_action_step`,
  `_append_execution_results_to_planning`.
- [ROS/Sugarcoat adapters](https://github.com/automatika-robotics/embodied-agents/blob/c37ab75db4aba88bcc99d17f6eabac146ad46d20/agents/ros.py).
- [Runtime dependencies](https://github.com/automatika-robotics/embodied-agents/blob/c37ab75db4aba88bcc99d17f6eabac146ad46d20/package.xml).

The current [Pi repository](https://github.com/earendil-works/pi), redirected
from `badlogic/pi-mono`, separates `pi-ai` (model/provider API), `pi-agent-core`
(tool-calling runtime/state) and `pi-coding-agent` (coding CLI). Pi is one
reusable implementation choice, not a required foundation for an agent harness.

The broad assertion that other harnesses are all based on Pi is unsupported.
In particular, the current official
[OpenClaw runtime reference](https://docs.openclaw.ai/agent-runtime-architecture)
describes an in-tree `@openclaw/agent-core`, states that no external agent
framework packages remain, and identifies `pi` as a legacy runtime alias.
It still identifies `pi-tui` as an external terminal toolkit. This describes
current packaging and ownership; it does not establish an unrelated historical
code origin. Do not reuse older Pi dependency descriptions as current facts.

The initial Cortex-only proposal was superseded by Dr Sun's Pi-plus-Cortex
selection. Pi owns the sole model/tool loop; a project gateway validates calls
before Cortex/EMOS execution. Pi npm release 0.85.1 has registry gitHead
`d981de1229ef899957bbe968bc8dcda02a21f477`. Cortex's private dispatch methods
are lifecycle-coupled; no drop-in Pi adapter has been verified.
