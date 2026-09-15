---
origin: ai_only
reviewed: false
stage: planning
status: surveyed
---

# UnifoLM-WLA-1.0: Lite3 suitability

Checked on 2026-09-10. The published material does not establish Lite3
support. It is a potential research reference for perception and action
learning, but cannot currently serve as a directly runnable Lite3 navigation
baseline.

## Primary evidence

- [Official project page](https://unigen-x.github.io/unifolm-wla.github.io/).
- [Pinned website source](https://github.com/UniGen-X/unifolm-wla.github.io/blob/f9c41c9ab097897da6ac32eab45454ef72a0e2bb/index.html),
  branch `main`, commit `f9c41c9ab097897da6ac32eab45454ef72a0e2bb`.
- Pinned `index.html`: 119,795 bytes; SHA-256
  `515096f8e499e1660ea61d6083f6e2cdd5df28ca54caca56ddd42381603ffa81`.
  This pins the presentation website, not an implementation repository.

The page describes a 6B-parameter humanoid foundation model trained on
approximately 2,500 hours of robot data. Its reported real-robot platform is
Unitree G1, with 10 whole-body manipulation tasks and 54 tabletop tasks.
These are author-reported demonstrations, not locally reproduced results.

The disclosed action representation separates end-effector poses,
end-effector joints, and lower-body joints, with separate residual vector
quantization models. An MMDiT action expert is conditioned on an embodiment
embedding. The published demonstrations of multiple end effectors do not
establish transfer to a quadruped's locomotion dynamics.

The ER component uses Qwen3-VL-4B and includes spatial reasoning, image-point
prediction, and 2D trajectory prediction. These capabilities are relevant to
navigation research, but the page does not establish a metric navigation
trajectory, traversability model, or Lite3 controller interface.

## Release and reproduction boundary

The Code, Models, and Datasets buttons all display `Coming soon` and link
back to `#resources`. No implementation commit, checkpoint, code/model
license, simulator setup, ROS interface, installation environment, or
original smoke command can be established from those links. The page links
existing training-data sources; those are not a release of this model's
complete training dataset. No paper link is provided on the inspected page.

The public Unitree repository inventory inspected through the GitHub API
listed `unifolm-vla` and `unifolm-world-model-action`; those are distinct
projects and must not be treated as this WLA-1.0 release.

## Adaptation assessment

| Intended use | Assessment |
|---|---|
| Load the released policy and drive Lite3 | No supported path is published; action semantics and embodiment differ. |
| Reuse ER for scene understanding or visual goals | Plausible research direction after release; requires Lite3 camera and navigation evaluation. |
| Train a Lite3 navigation action expert | Substantial new work: define waypoints or body velocity commands, obtain paired navigation data, train or fine-tune the action mapping, and evaluate the closed loop. |
| Transfer the whole-body action policy to Lite3 joints | Requires robot-specific state/action definitions, dynamics and control adaptation, training, and validation; a joint-name remap is insufficient. |

The adaptation assessments above are engineering inferences from the
published scope, not claims made or validated by the authors.

For Lite3 navigation, the preferred research seam would be visual/language
understanding followed by a navigation goal or trajectory and a separately
validated Lite3 locomotion controller. The project's downstream interface
remains a reviewable decision; this survey does not freeze it.

There is no runnable original reproduction target identified for WLA-1.0
today. Once the release exists, the first target should be the official
offline inference example with its original checkpoint and embodiment,
before any Lite3 interface experiment.

Scope of this check: primary webpage/source inspection and release-link
verification only. No implementation was imported, executed, integrated,
or validated. Existing project experiments and state indexes were not changed.
