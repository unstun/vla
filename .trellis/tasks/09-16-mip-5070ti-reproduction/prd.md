# Prepare MIP reproduction on RTX 5070 Ti

Stage: experiment + analysis. Requested by Dr Sun on 2026-09-16: prepare MIP
reproduction on the 5070 Ti and have the server download its required resources.
This request authorizes acquisition, isolated environment preparation and bounded
installation/interface smoke checks. It selects MIP for reproduction preparation;
it does not replace the existing InternVLA-N1 experiment or authorize robot motion.

## Acceptance criteria

- Verify the actual SSH destination and record live GPU, RAM, disk and processes.
- Pin AgentCanvas's paper branch and Apache-2.0 source at
  `b2b363af80a010ea9f73a0be9d49bc75555efdef` on local and execution copies.
- Download source and runtime resources directly on the server; preserve unrelated
  installations and processes.
- Prepare the upstream `agentcanvas` runner and `ac-vlnce` Habitat environments,
  recording exact compatibility changes and checks on the RTX 5070 Ti.
- Materialize the upstream frozen `rand100` split. Download scene assets only
  under the user's existing or newly confirmed dataset authorization.
- Verify imports and the server/tool interface; use actual rendered observations
  if scene access is available. Record authentication or dataset blockers precisely.
- Return setup logs, environment inventories, source hashes and result summary
  locally. Distinguish prepared/imported from an executed navigation reproduction.

## Boundaries

No formal multi-episode benchmark, model training, real-robot actuation, host-wide
cleanup or modification of sibling repositories. No silent fallback from the
paper's split/model/interface to another protocol. Dr Sun confirmed MP3D access,
selected DeepSeek Harness and will configure the server API key later. Prepare a
separately labeled DeepSeek extension and verify its interface without a real API
call; original Claude/Codex benchmark results remain outside this preparation.

Follow-up on 2026-09-16: after configuring the server key, Dr Sun said
"好了，你试试". This authorized the credential check and one prepared episode-0
trial. That trial completed; see `implement.md` and `REAL_EPISODE_RESULT.md`.
